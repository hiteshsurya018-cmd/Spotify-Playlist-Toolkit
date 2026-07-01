from app.core.config import Settings


def make_settings(**overrides):
    defaults = {
        "session_secret": "test-secret-value-long-enough",
        "spotify_client_id": "client-id",
        "spotify_client_secret": "client-secret",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_cors_origins_include_frontend_url_when_different_loopback_host():
    settings = make_settings(
        frontend_url="http://127.0.0.1:5173",
        cors_origins="http://localhost:5173",
    )

    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_cookie_secure_loads_from_uppercase_environment(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret-value-long-enough")
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("COOKIE_SECURE", "true")

    settings = Settings(_env_file=None)

    assert settings.cookie_secure is True
    assert settings.session_cookie_secure is True


def test_https_backend_uses_cross_site_secure_cookie_policy():
    settings = make_settings(
        frontend_url="https://spotifyplaylisttoolkit.vercel.app",
        backend_url="https://spotify-playlist-toolkit.onrender.com",
        cookie_secure=False,
    )

    assert settings.session_cookie_secure is True
    assert settings.session_cookie_samesite == "none"


def test_local_http_uses_lax_cookie_policy():
    settings = make_settings(
        frontend_url="http://localhost:5173",
        backend_url="http://localhost:8000",
        cookie_secure=False,
    )

    assert settings.session_cookie_secure is False
    assert settings.session_cookie_samesite == "lax"
