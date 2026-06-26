from app.services.spotify_client import get_playlist_tracks_page


class FakeCurrentSpotify:
    def __init__(self):
        self.paths = []

    def _get_id(self, kind, value):
        assert kind == "playlist"
        return value

    def _get(self, path, **kwargs):
        self.paths.append(path)
        return {
            "items": [
                {
                    "added_at": "2026-01-01T00:00:00Z",
                    "track": {
                        "id": "track-1",
                        "uri": "spotify:track:1",
                        "type": "track",
                        "name": "Song One",
                        "artists": [{"name": "Artist A"}],
                        "album": {"name": "Album A", "images": []},
                        "duration_ms": 180000,
                    },
                }
            ],
            "total": 1,
            "next": None,
        }


def test_get_playlist_tracks_page_uses_current_playlist_items_endpoint():
    sp = FakeCurrentSpotify()

    tracks, total, has_more = get_playlist_tracks_page(sp, "playlist-1", limit=100, offset=0)

    assert sp.paths == ["playlists/playlist-1/items"]
    assert tracks[0].name == "Song One"
    assert total == 1
    assert has_more is False
