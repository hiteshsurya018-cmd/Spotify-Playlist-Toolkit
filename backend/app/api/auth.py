import uuid

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
    get_all_playlists,
    oauth_manager,
    spotify_from_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


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
        settings.cookie_secure,
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
    playlists = get_all_playlists(sp, profile["id"])

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

    response = RedirectResponse(
        f"{frontend_url}/dashboard"
    )

    clear_oauth_state_cookie(response)

    set_session_cookie(
        response,
        session.id,
        settings.session_secret,
        settings.cookie_secure,
    )

    response.headers["X-Playlist-Count"] = str(len(playlists))

    return response


@router.post("/logout")
def logout(response: Response) -> dict:
    clear_session_cookie(response)
    return {"ok": True}
