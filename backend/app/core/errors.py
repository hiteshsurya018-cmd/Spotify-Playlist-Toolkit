from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from spotipy.exceptions import SpotifyException


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    @app.exception_handler(SpotifyException)
    async def spotify_error_handler(_: Request, exc: SpotifyException) -> JSONResponse:
        status_code = exc.http_status or 502
        details = {}
        headers = {}
        message = exc.msg or "Spotify API request failed"

        if status_code == 429:
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            message = "Spotify rate limit reached. Please wait a moment and try again."
            if retry_after:
                details["retry_after_seconds"] = retry_after
                headers["Retry-After"] = retry_after

        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": "spotify_rate_limited" if status_code == 429 else "spotify_error",
                    "message": message,
                    "details": details,
                },
            },
            headers=headers,
        )
