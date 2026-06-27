from fastapi.testclient import TestClient
import pytest
from spotipy.exceptions import SpotifyException

from app.api.playlists import FORBIDDEN_TRACK_PLAYLISTS
from app.api.deps import get_current_session, get_spotify
from app.main import app
from app.models.db import UserSession
from app.services.spotify_client import clear_playlist_cache


class FakeSpotify:
    playlist_items_calls = 0
    prefix = "https://api.spotify.com/v1/"
    language = None
    requests_timeout = 20
    proxies = None

    def _auth_headers(self):
        return {"Authorization": "Bearer token"}

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

    def playlist(self, playlist_id, fields=None):
        if playlist_id == "playlist-1":
            return {
                "id": "playlist-1",
                "name": "Liked Imports",
                "images": [],
                "owner": {"id": "user-1", "display_name": "Test User"},
                "tracks": {"total": 2},
                "public": False,
                "collaborative": False,
            }
        if playlist_id == "playlist-2":
            return {
                "id": "playlist-2",
                "name": "Followed Playlist",
                "images": [],
                "owner": {"id": "other-user", "display_name": "Other User"},
                "tracks": {"total": 10},
                "public": True,
                "collaborative": False,
            }
        raise SpotifyException(404, -1, "Not Found")

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
    clear_playlist_cache()
    yield
    FORBIDDEN_TRACK_PLAYLISTS.clear()
    clear_playlist_cache()


def test_me_returns_profile_and_csrf():
    app.dependency_overrides[get_spotify] = lambda: FakeSpotify()
    app.dependency_overrides[get_current_session] = fake_session
    client = TestClient(app)

    response = client.get("/api/me")

    assert response.status_code == 200
    assert response.json()["display_name"] == "Test User"
    assert response.json()["total_playlists"] == 0
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


def test_debug_raw_playlists_compares_raw_and_spotipy(monkeypatch):
    class FakeResponse:
        status_code = 429
        headers = {"Retry-After": "12", "X-Spotify-Trace": "trace-id"}
        text = '{"error":{"status":429,"message":"API rate limit exceeded"}}'

    def fake_get(url, headers, params, timeout):
        assert url == "https://api.spotify.com/v1/me/playlists"
        assert headers["Authorization"] == "Bearer token"
        assert params == {"limit": 1}
        assert timeout == 20
        return FakeResponse()

    spotify = FakeSpotify()
    spotify.current_user_playlists = lambda limit=50, offset=0: (_ for _ in ()).throw(
        SpotifyException(429, -1, "Max Retries")
    )
    monkeypatch.setattr("app.api.playlists.requests.get", fake_get)
    app.dependency_overrides[get_spotify] = lambda: spotify
    app.dependency_overrides[get_current_session] = fake_session
    client = TestClient(app)

    response = client.get("/api/debug-raw-playlists")

    assert response.status_code == 200
    data = response.json()
    assert data["raw"]["status_code"] == 429
    assert data["raw"]["retry_after"] == "12"
    assert data["raw"]["body"] == FakeResponse.text
    assert data["spotipy"]["http_status"] == 429
    assert data["comparison"]["both_returned_429"] is True
    assert data["request_construction"]["raw"]["headers"]["Authorization"] == "<redacted>"
    assert data["request_construction"]["spotipy"]["prepared_url"] == (
        "https://api.spotify.com/v1/me/playlists?limit=1"
    )
    app.dependency_overrides.clear()


def test_raw_endpoint_diagnostics(monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 200
        headers = {"Retry-After": "7"}
        text = '{"ok":true}'

    def fake_get(url, headers, params=None, timeout=None):
        calls.append(
            {
                "url": url,
                "headers": headers,
                "params": params,
                "timeout": timeout,
            }
        )
        return FakeResponse()

    monkeypatch.setattr("app.api.playlists.requests.get", fake_get)
    app.dependency_overrides[get_current_session] = fake_session
    client = TestClient(app)

    profile_response = client.get("/api/debug-profile")
    playlist_response = client.get("/api/debug-playlist-by-id", params={"playlist_id": "playlist-1"})
    items_response = client.get("/api/debug-playlist-items", params={"playlist_id": "playlist-1"})

    assert profile_response.status_code == 200
    assert profile_response.json() == {
        "endpoint": "/v1/me",
        "status_code": 200,
        "retry_after": "7",
        "body": '{"ok":true}',
        "headers": {"Retry-After": "7"},
    }
    assert playlist_response.json()["endpoint"] == "/v1/playlists/playlist-1"
    assert items_response.json()["endpoint"] == "/v1/playlists/playlist-1/items"
    assert calls == [
        {
            "url": "https://api.spotify.com/v1/me",
            "headers": {"Authorization": "Bearer token", "Accept": "application/json"},
            "params": None,
            "timeout": 20,
        },
        {
            "url": "https://api.spotify.com/v1/playlists/playlist-1",
            "headers": {"Authorization": "Bearer token", "Accept": "application/json"},
            "params": None,
            "timeout": 20,
        },
        {
            "url": "https://api.spotify.com/v1/playlists/playlist-1/items",
            "headers": {"Authorization": "Bearer token", "Accept": "application/json"},
            "params": {"limit": 1},
            "timeout": 20,
        },
    ]
    app.dependency_overrides.clear()
