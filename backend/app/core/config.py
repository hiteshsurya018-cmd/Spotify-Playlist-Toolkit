from functools import lru_cache
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def get_settings() -> Settings:
    return Settings()
