import logging

logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, export, playlists, tracks
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.db import init_db

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Spotify Playlist Bulk Transfer Manager", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_error_handlers(app)
    app.include_router(auth.router)
    app.include_router(playlists.router)
    app.include_router(tracks.router)
    app.include_router(export.router)

    @app.on_event("startup")
    def on_startup() -> None:
        logger.info(
            "settings loaded app_env=%s frontend_url=%s backend_url=%s cookie_secure_configured=%s "
            "session_cookie_secure=%s session_cookie_samesite=%s cors_origins=%s spotify_redirect_uri=%s",
            settings.app_env,
            settings.frontend_url,
            settings.backend_url,
            settings.cookie_secure,
            settings.session_cookie_secure,
            settings.session_cookie_samesite,
            settings.cors_origin_list,
            settings.spotify_redirect_uri,
        )
        init_db()

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
