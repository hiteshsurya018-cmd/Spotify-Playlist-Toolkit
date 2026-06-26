from fastapi.testclient import TestClient
import pytest
from spotipy.exceptions import SpotifyException

from app.api.playlists import FORBIDDEN_TRACK_PLAYLISTS
from app.api.deps import get_current_session, get_spotify
from app.main import app
from app.models.db import UserSession


class FakeSpotify:
    playlist_items_calls = 0

    def current_user(self):
        return {"id": "user-1", "display_name": "Test User", "images": [{"url": "https://img", "width": 64, "height": 64}]}

    def current_user_playlists(self, limit=50, offset=0):
        return {
            "items": [
                {
                    "id": "playlist-1",
                    "name": "Liked Imports",
                    "images": [],
                    "owner": {"id": "user-1", "display_name": "Test User"},
                    "tracks": {"total": 2},
                    "public": False,
                    "collaborative": False,
                },
                {
                    "id": "playlist-2",
                    "name": "Followed Playlist",
                    "images": [],
                    "owner": {"id": "other-user", "display_name": "Other User"},
                    "tracks": {"total": 10},
                    "public": True,
                    "collaborative": False,
                }
            ],
            "next": None,
        }

    def _get_id(self, kind, value):
        assert kind == "playlist"
        return value

    def _get(self, path, **kwargs):
        self.playlist_items_calls += 1
        raise SpotifyException(403, -1, "Forbidden")


def fake_session():
    return UserSession(
        id="session",
        spotify_user_id="user-1",
        display_name="Test User",
        csrf_token="csrf-token",
        token_info={"access_token": "token", "refresh_token": "refresh", "expires_at": 9999999999},
    )


@pytest.fixture(autouse=True)
def clear_forbidden_playlists():
    FORBIDDEN_TRACK_PLAYLISTS.clear()
    yield
    FORBIDDEN_TRACK_PLAYLISTS.clear()


def test_me_returns_profile_and_csrf():
    app.dependency_overrides[get_spotify] = lambda: FakeSpotify()
    app.dependency_overrides[get_current_session] = fake_session
    client = TestClient(app)

    response = client.get("/api/me")

    assert response.status_code == 200
    assert response.json()["display_name"] == "Test User"
    assert response.json()["total_playlists"] == 2
    assert response.json()["csrf_token"] == "csrf-token"
    app.dependency_overrides.clear()


def test_playlists_returns_cards_data():
    app.dependency_overrides[get_spotify] = lambda: FakeSpotify()
    client = TestClient(app)

    response = client.get("/api/playlists")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Liked Imports"
    assert response.json()[0]["tracks_total"] == 2
    assert response.json()[0]["tracks_readable"] is True
    assert response.json()[1]["tracks_readable"] is False
    app.dependency_overrides.clear()


def test_playlist_tracks_returns_clear_error_for_unreadable_playlist():
    spotify = FakeSpotify()
    app.dependency_overrides[get_spotify] = lambda: spotify
    app.dependency_overrides[get_current_session] = fake_session
    client = TestClient(app)

    response = client.get("/api/playlists/playlist-2/tracks")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "playlist_tracks_forbidden"
    assert spotify.playlist_items_calls == 0
    app.dependency_overrides.clear()


def test_playlist_tracks_remembers_spotify_forbidden_response():
    spotify = FakeSpotify()
    app.dependency_overrides[get_spotify] = lambda: spotify
    app.dependency_overrides[get_current_session] = fake_session
    client = TestClient(app)

    first_response = client.get("/api/playlists/playlist-1/tracks")
    second_response = client.get("/api/playlists/playlist-1/tracks")
    playlists_response = client.get("/api/playlists")

    assert first_response.status_code == 403
    assert second_response.status_code == 403
    assert spotify.playlist_items_calls == 1
    assert playlists_response.json()[0]["tracks_readable"] is False
    app.dependency_overrides.clear()
