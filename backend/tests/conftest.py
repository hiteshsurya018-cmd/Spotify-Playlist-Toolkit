import os
from pathlib import Path

import pytest

os.environ.setdefault("SESSION_SECRET", "test-secret-value-long-enough")
os.environ.setdefault("SPOTIFY_CLIENT_ID", "client-id")
os.environ.setdefault("SPOTIFY_CLIENT_SECRET", "client-secret")
os.environ.setdefault("SPOTIFY_REDIRECT_URI", "http://localhost:8000/api/auth/callback")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_spotify_transfer.db")
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")
os.environ.setdefault("BACKEND_URL", "http://localhost:8000")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")


@pytest.fixture(autouse=True)
def test_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret-value-long-enough")
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", "http://localhost:8000/api/auth/callback")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:5173")
    monkeypatch.setenv("BACKEND_URL", "http://localhost:8000")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
    yield
