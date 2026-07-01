from functools import lru_cache
import logging
from typing import Literal
from urllib.parse import urlparse

from pydantic import AnyHttpUrl, Field
from pydantic_core import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


CookieSameSite = Literal["lax", "strict", "none"]
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    app_env: str = "development"
    frontend_url: AnyHttpUrl = "http://localhost:5173"
    backend_url: AnyHttpUrl = "http://localhost:8000"
    session_secret: str = Field(min_length=16)
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str = "http://localhost:8000/api/auth/callback"

    database_url: str = "sqlite:///./spotify_transfer.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [item.strip().rstrip("/") for item in self.cors_origins.split(",") if item.strip()]
        frontend_origin = str(self.frontend_url).rstrip("/")
        if frontend_origin not in origins:
            origins.append(frontend_origin)
        return origins

    @property
    def session_cookie_secure(self) -> bool:
        backend_scheme = urlparse(str(self.backend_url)).scheme
        return self.cookie_secure or backend_scheme == "https" or self.app_env.lower() in {"prod", "production"}

    @property
    def session_cookie_samesite(self) -> CookieSameSite:
        frontend_origin = str(self.frontend_url).rstrip("/")
        backend_origin = str(self.backend_url).rstrip("/")
        if self.session_cookie_secure and frontend_origin != backend_origin:
            return "none"
        return "lax"


@lru_cache
def get_settings() -> Settings:
    try:
        settings = Settings()
    except ValidationError as exc:
        logger.error(
            "settings validation failed errors=%s",
            exc.errors(include_input=False),
        )
        raise

    logger.info(
        "settings loaded app_env=%s frontend_url=%s backend_url=%s cookie_secure=%s "
        "session_cookie_secure=%s session_cookie_samesite=%s cors_origins=%s spotify_redirect_uri=%s "
        "database_url_scheme=%s",
        settings.app_env,
        settings.frontend_url,
        settings.backend_url,
        settings.cookie_secure,
        settings.session_cookie_secure,
        settings.session_cookie_samesite,
        settings.cors_origin_list,
        settings.spotify_redirect_uri,
        settings.database_url.split(":", 1)[0],
    )
    return settings
