from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, export, playlists, tracks
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.db import init_db


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
        init_db()

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
