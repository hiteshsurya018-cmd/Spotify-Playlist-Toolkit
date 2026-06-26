from app.core.config import Settings


def test_cors_origins_include_frontend_url_when_different_loopback_host():
    settings = Settings(
        session_secret="test-secret-value-long-enough",
        spotify_client_id="client-id",
        spotify_client_secret="client-secret",
        frontend_url="http://127.0.0.1:5173",
        cors_origins="http://localhost:5173",
    )

    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
