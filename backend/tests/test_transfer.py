from app.models.db import UserSession
from app.models.schemas import TransferRequest
from app.services.transfer import detect_duplicates, transfer_tracks, undo_transfer


class FakeSpotify:
    def __init__(self):
        self.destination_items = ["spotify:track:1", "spotify:track:2"]
        self.added = []
        self.removed = []

    def _get_id(self, kind, value):
        assert kind == "playlist"
        return value

    def _get(self, path, **kwargs):
        limit = kwargs.get("limit", 100)
        offset = kwargs.get("offset", 0)
        items = [{"item": {"uri": uri}} for uri in self.destination_items[offset : offset + limit]]
        return {"items": items, "next": None, "total": len(self.destination_items)}

    def _post(self, path, payload=None, **kwargs):
        playlist_id = path.split("/")[1]
        self.added.append((playlist_id, payload["uris"]))
        return {"snapshot_id": "added"}

    def _delete(self, path, payload=None, **kwargs):
        playlist_id = path.split("/")[1]
        self.removed.append((playlist_id, [item["uri"] for item in payload["items"]]))
        return {"snapshot_id": "removed"}


def make_session():
    return UserSession(
        id="session",
        spotify_user_id="user",
        display_name="User",
        csrf_token="csrf",
        token_info={"access_token": "token", "refresh_token": "refresh", "expires_at": 9999999999},
    )


def test_duplicate_detection_counts_existing_tracks():
    summary = detect_duplicates(FakeSpotify(), "dest", ["spotify:track:1", "spotify:track:3"])

    assert summary.duplicates == 1
    assert summary.new_tracks == 1
    assert summary.duplicate_uris == ["spotify:track:1"]


def test_copy_skips_duplicates_by_default_and_stores_undo():
    sp = FakeSpotify()
    session = make_session()
    payload = TransferRequest(
        source_playlist_id="source",
        destination_playlist_id="dest",
        track_uris=["spotify:track:1", "spotify:track:3"],
    )

    result = transfer_tracks(sp, session, "copy", payload)

    assert result.transferred == 1
    assert result.skipped_duplicates == 1
    assert sp.added == [("dest", ["spotify:track:3"])]
    assert session.last_action["action"] == "copy"
    assert session.last_action["track_uris"] == ["spotify:track:3"]


def test_move_adds_then_removes_from_source():
    sp = FakeSpotify()
    session = make_session()
    payload = TransferRequest(
        source_playlist_id="source",
        destination_playlist_id="dest",
        track_uris=["spotify:track:3"],
    )

    result = transfer_tracks(sp, session, "move", payload)

    assert result.transferred == 1
    assert sp.added == [("dest", ["spotify:track:3"])]
    assert sp.removed == [("source", ["spotify:track:3"])]


def test_undo_copy_removes_added_tracks_from_destination():
    sp = FakeSpotify()
    session = make_session()
    session.last_action = {
        "action": "copy",
        "source_playlist_id": "source",
        "destination_playlist_id": "dest",
        "track_uris": ["spotify:track:3"],
    }

    restored, message = undo_transfer(sp, session)

    assert restored == 1
    assert "copy" in message
    assert sp.removed == [("dest", ["spotify:track:3"])]
    assert session.last_action is None
