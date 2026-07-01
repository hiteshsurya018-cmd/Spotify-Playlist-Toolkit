import secrets
from datetime import datetime, timezone
from typing import Literal

from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeSerializer, URLSafeTimedSerializer

SESSION_COOKIE = "spbtm_session"
OAUTH_STATE_COOKIE = "spbtm_oauth_state"
CookieSameSite = Literal["lax", "strict", "none"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def random_token() -> str:
    return secrets.token_urlsafe(32)


def signer(secret: str) -> URLSafeSerializer:
    return URLSafeSerializer(secret_key=secret, salt="spotify-playlist-transfer")


def timed_signer(secret: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key=secret, salt="spotify-playlist-transfer-oauth-state")


def sign_value(secret: str, value: str) -> str:
    return signer(secret).dumps(value)


def unsign_value(secret: str, value: str) -> str | None:
    try:
        return signer(secret).loads(value)
    except BadSignature:
        return None


def create_oauth_state(secret: str) -> str:
    return timed_signer(secret).dumps({"nonce": random_token()})


def verify_oauth_state(secret: str, value: str, max_age: int = 600) -> bool:
    try:
        data = timed_signer(secret).loads(value, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return False
    return isinstance(data, dict) and isinstance(data.get("nonce"), str)


def normalize_cookie_policy(secure: bool, samesite: CookieSameSite) -> tuple[bool, CookieSameSite]:
    if samesite == "none":
        return True, samesite
    return secure, samesite


def set_session_cookie(
    response: Response,
    value: str,
    secret: str,
    secure: bool,
    samesite: CookieSameSite = "lax",
) -> None:
    secure, samesite = normalize_cookie_policy(secure, samesite)
    response.set_cookie(
        SESSION_COOKIE,
        sign_value(secret, value),
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=60 * 60 * 24 * 14,
    )


def read_session_cookie(request: Request, secret: str) -> str | None:
    raw = request.cookies.get(SESSION_COOKIE)
    return unsign_value(secret, raw) if raw else None


def clear_session_cookie(response: Response, secure: bool = False, samesite: CookieSameSite = "lax") -> None:
    secure, samesite = normalize_cookie_policy(secure, samesite)
    response.delete_cookie(SESSION_COOKIE, secure=secure, httponly=True, samesite=samesite)


def set_oauth_state_cookie(
    response: Response,
    value: str,
    secret: str,
    secure: bool,
    samesite: CookieSameSite = "lax",
) -> None:
    secure, samesite = normalize_cookie_policy(secure, samesite)
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        sign_value(secret, value),
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=600,
    )


def read_oauth_state_cookie(request: Request, secret: str) -> str | None:
    raw = request.cookies.get(OAUTH_STATE_COOKIE)
    return unsign_value(secret, raw) if raw else None


def clear_oauth_state_cookie(response: Response, secure: bool = False, samesite: CookieSameSite = "lax") -> None:
    secure, samesite = normalize_cookie_policy(secure, samesite)
    response.delete_cookie(OAUTH_STATE_COOKIE, secure=secure, httponly=True, samesite=samesite)
