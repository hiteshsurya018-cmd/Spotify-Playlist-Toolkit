from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import ApiError
from app.core.security import read_session_cookie
from app.db import get_db
from app.models.db import UserSession
from app.services.spotify_client import oauth_manager, spotify_from_token


def get_current_session(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserSession:
    session_id = read_session_cookie(request, settings.session_secret)
    if not session_id:
        raise ApiError(401, "not_authenticated", "Please log in with Spotify.")
    session = db.get(UserSession, session_id)
    if not session:
        raise ApiError(401, "not_authenticated", "Session expired. Please log in again.")
    return session


def require_csrf(
    x_csrf_token: str | None = Header(default=None),
    session: UserSession = Depends(get_current_session),
) -> None:
    if not x_csrf_token or x_csrf_token != session.csrf_token:
        raise ApiError(403, "csrf_failed", "Invalid CSRF token.")


def get_spotify(
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    manager = oauth_manager(settings)
    token_info = session.token_info
    token_expired = manager.is_token_expired(token_info)
    print(
        "[api.deps] get_spotify "
        f"session_id={session.id} spotify_user_id={session.spotify_user_id} "
        f"token_expired={token_expired}"
    )
    if token_expired:
        print(f"[api.deps] refresh_access_token start session_id={session.id}")
        token_info = manager.refresh_access_token(token_info["refresh_token"])
        print(f"[api.deps] refresh_access_token done session_id={session.id}")
        session.token_info = token_info
        db.add(session)
        db.commit()
        db.refresh(session)
    return spotify_from_token(token_info)
