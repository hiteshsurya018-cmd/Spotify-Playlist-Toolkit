import uuid

import spotipy

from app.models.db import UserSession
from app.models.schemas import DuplicateSummary, TransferRequest, TransferResult
from app.services.spotify_client import (
    get_all_playlist_track_uris,
    playlist_add_items_v2,
    playlist_remove_items_v2,
    retry_spotify,
)


def chunks(items: list[str], size: int = 100):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def detect_duplicates(sp: spotipy.Spotify, destination_playlist_id: str, track_uris: list[str]) -> DuplicateSummary:
    existing = get_all_playlist_track_uris(sp, destination_playlist_id)
    duplicate_uris = sorted(set(track_uris).intersection(existing))
    return DuplicateSummary(
        duplicates=len(duplicate_uris),
        new_tracks=len([uri for uri in track_uris if uri not in existing]),
        duplicate_uris=duplicate_uris,
    )


def add_tracks(sp: spotipy.Spotify, playlist_id: str, track_uris: list[str]) -> int:
    count = 0
    for batch in chunks(track_uris):
        retry_spotify(lambda batch=batch: playlist_add_items_v2(sp, playlist_id, batch))
        count += len(batch)
    return count


def remove_tracks(sp: spotipy.Spotify, playlist_id: str, track_uris: list[str]) -> int:
    count = 0
    for batch in chunks(track_uris):
        retry_spotify(lambda batch=batch: playlist_remove_items_v2(sp, playlist_id, batch))
        count += len(batch)
    return count


def transfer_tracks(sp: spotipy.Spotify, session: UserSession, action: str, payload: TransferRequest) -> TransferResult:
    duplicate_summary = detect_duplicates(sp, payload.destination_playlist_id, payload.track_uris)
    duplicate_set = set(duplicate_summary.duplicate_uris)
    tracks_to_add = [uri for uri in payload.track_uris if not (payload.skip_duplicates and uri in duplicate_set)]

    transferred = add_tracks(sp, payload.destination_playlist_id, tracks_to_add) if tracks_to_add else 0
    if action == "move" and transferred:
        remove_tracks(sp, payload.source_playlist_id, tracks_to_add)

    operation_id = str(uuid.uuid4())
    session.last_action = {
        "operation_id": operation_id,
        "action": action,
        "source_playlist_id": payload.source_playlist_id,
        "destination_playlist_id": payload.destination_playlist_id,
        "track_uris": tracks_to_add,
    }

    return TransferResult(
        operation_id=operation_id,
        action=action,
        requested=len(payload.track_uris),
        transferred=transferred,
        skipped_duplicates=len(payload.track_uris) - len(tracks_to_add),
        duplicate_summary=duplicate_summary,
    )


def undo_transfer(sp: spotipy.Spotify, session: UserSession) -> tuple[int, str]:
    action_data = session.last_action or {}
    action = action_data.get("action")
    track_uris = action_data.get("track_uris") or []
    source = action_data.get("source_playlist_id")
    destination = action_data.get("destination_playlist_id")

    if not action or not track_uris or not source or not destination:
        return 0, "No transfer action is available to undo."

    if action == "copy":
        count = remove_tracks(sp, destination, track_uris)
    else:
        add_tracks(sp, source, track_uris)
        count = remove_tracks(sp, destination, track_uris)

    session.last_action = None
    return count, f"Undid last {action} operation."
