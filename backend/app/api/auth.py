import uuid
import logging

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import ApiError
from app.core.security import (
    clear_oauth_state_cookie,
    clear_session_cookie,
    create_oauth_state,
    random_token,
    read_oauth_state_cookie,
    set_oauth_state_cookie,
    set_session_cookie,
    verify_oauth_state,
)
from app.db import get_db
from app.models.db import UserSession
from app.services.spotify_client import (
    oauth_manager,
    spotify_from_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.get("/login")
def login(settings: Settings = Depends(get_settings)) -> Response:
    state = create_oauth_state(settings.session_secret)

    manager = oauth_manager(settings)
    auth_url = manager.get_authorize_url(state=state)

    response = RedirectResponse(auth_url)

    set_oauth_state_cookie(
        response,
        state,
        settings.session_secret,
        settings.session_cookie_secure,
        settings.session_cookie_samesite,
    )

    return response


@router.get("/callback")
def callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    expected_state = read_oauth_state_cookie(
        request,
        settings.session_secret,
    )

    if expected_state and expected_state != state:
        raise ApiError(
            400,
            "invalid_oauth_state",
            "OAuth state validation failed.",
        )

    if not expected_state and not verify_oauth_state(settings.session_secret, state):
        raise ApiError(
            400,
            "invalid_oauth_state",
            "OAuth state is missing, expired, or invalid.",
        )

    manager = oauth_manager(settings)

    token_info = manager.get_access_token(
        code,
        as_dict=True,
        check_cache=False,
    )

    sp = spotify_from_token(token_info)

    profile = sp.current_user()

    session = UserSession(
        id=str(uuid.uuid4()),
        spotify_user_id=profile["id"],
        display_name=profile.get("display_name"),
        csrf_token=random_token(),
        token_info=token_info,
    )

    db.add(session)
    db.commit()

    frontend_url = str(settings.frontend_url).rstrip("/")
    redirect_url = f"{frontend_url}/dashboard"

    response = RedirectResponse(redirect_url)

    clear_oauth_state_cookie(
        response,
        settings.session_cookie_secure,
        settings.session_cookie_samesite,
    )

    set_session_cookie(
        response,
        session.id,
        settings.session_secret,
        settings.session_cookie_secure,
        settings.session_cookie_samesite,
    )

    logger.info(
        "spotify callback created session redirect_url=%s cookie_secure=%s cookie_samesite=%s",
        redirect_url,
        settings.session_cookie_secure,
        settings.session_cookie_samesite,
    )

    return response


@router.post("/logout")
def logout(response: Response, settings: Settings = Depends(get_settings)) -> dict:
    clear_session_cookie(
        response,
        settings.session_cookie_secure,
        settings.session_cookie_samesite,
    )
    return {"ok": True}
