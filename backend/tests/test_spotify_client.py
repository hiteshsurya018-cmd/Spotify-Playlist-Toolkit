from app.services.spotify_client import clear_playlist_cache, get_all_playlists, get_playlist_tracks_page, spotify_from_token


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


class FakePlaylistSpotify:
    def __init__(self):
        self.calls = 0

    def current_user_playlists(self, limit=50, offset=0):
        self.calls += 1
        return {
            "items": [
                {
                    "id": "playlist-1",
                    "name": "Cached Playlist",
                    "images": [],
                    "owner": {"id": "user-1", "display_name": "Test User"},
                    "tracks": {"total": 3},
                    "public": False,
                    "collaborative": False,
                }
            ],
            "next": None,
        }


def test_spotify_from_token_disables_spotipy_status_retries():
    sp = spotify_from_token({"access_token": "token"})

    assert sp.retries == 0
    assert sp.status_retries == 0


def test_get_all_playlists_caches_per_user_and_returns_clones():
    clear_playlist_cache()
    sp = FakePlaylistSpotify()

    first = get_all_playlists(sp, "user-1")
    first[0].tracks_readable = False
    second = get_all_playlists(sp, "user-1")

    assert sp.calls == 1
    assert second[0].tracks_readable is True
    clear_playlist_cache()


def test_get_playlist_tracks_page_uses_current_playlist_items_endpoint():
    sp = FakeCurrentSpotify()

    tracks, total, has_more = get_playlist_tracks_page(sp, "playlist-1", limit=100, offset=0)

    assert sp.paths == ["playlists/playlist-1/items"]
    assert tracks[0].name == "Song One"
    assert total == 1
    assert has_more is False
