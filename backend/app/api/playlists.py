from fastapi import APIRouter, Depends, Query
import requests
from spotipy.exceptions import SpotifyException
from itertools import count
from urllib.parse import quote

from app.api.deps import get_current_session, get_spotify, require_csrf
from app.core.errors import ApiError
from app.models.db import UserSession
from app.models.schemas import (
    CreatePlaylistRequest,
    PlaylistSummary,
    TrackPage,
    UserProfile,
)
from app.services.spotify_client import (
    clear_playlist_cache,
    get_all_playlists,
    get_playlist_tracks_page,
    normalize_images,
    normalize_playlist,
)

router = APIRouter(prefix="/api", tags=["playlists"])

FORBIDDEN_TRACK_PLAYLISTS: set[tuple[str, str]] = set()
ME_ROUTE_COUNTER = count(1)
PLAYLISTS_ROUTE_COUNTER = count(1)
TRACKS_ROUTE_COUNTER = count(1)
RAW_PLAYLISTS_DEBUG_COUNTER = count(1)
RAW_ENDPOINT_DEBUG_COUNTER = count(1)


def forbidden_playlist_key(
    user_id: str | None,
    playlist_id: str,
) -> tuple[str, str]:
    return (user_id or "unknown", playlist_id)


def playlist_tracks_forbidden() -> ApiError:
    return ApiError(
        403,
        "playlist_tracks_forbidden",
        "Spotify only allows this app to read tracks from playlists you own or collaborate on.",
    )


def redact_request_headers(headers: dict) -> dict:
    redacted = dict(headers)
    for key in list(redacted):
        if key.lower() in {"authorization", "cookie"}:
            redacted[key] = "<redacted>"
    return redacted


def spotipy_playlists_request_debug(sp, params: dict) -> dict:
    url = f"{sp.prefix}me/playlists"
    headers = sp._auth_headers()
    headers["Content-Type"] = "application/json"
    if getattr(sp, "language", None) is not None:
        headers["Accept-Language"] = sp.language

    prepared = requests.Request(
        "GET",
        url,
        headers=headers,
        params=params,
    ).prepare()

    return {
        "method": "GET",
        "url": url,
        "prepared_url": prepared.url,
        "headers": redact_request_headers(headers),
        "timeout": getattr(sp, "requests_timeout", None),
        "proxies": getattr(sp, "proxies", None),
    }


def spotify_raw_headers(session: UserSession) -> dict:
    return {
        "Authorization": f"Bearer {session.token_info['access_token']}",
        "Accept": "application/json",
    }


def raw_spotify_get_debug(
    request_id: int,
    label: str,
    endpoint: str,
    url: str,
    session: UserSession,
    params: dict | None = None,
) -> dict:
    print(
        "[api.playlists] raw spotify debug "
        f"#{request_id} {label} start endpoint={endpoint} url={url} params={params or {}}"
    )
    response = requests.get(
        url,
        headers=spotify_raw_headers(session),
        params=params,
        timeout=20,
    )
    retry_after = response.headers.get("Retry-After")
    body = response.text
    headers = dict(response.headers)
    print(
        "[api.playlists] raw spotify debug "
        f"#{request_id} {label} status={response.status_code} "
        f"retry_after={retry_after!r} headers={headers} body={body}"
    )
    return {
        "endpoint": endpoint,
        "status_code": response.status_code,
        "retry_after": retry_after,
        "body": body,
        "headers": headers,
    }


@router.get("/me", response_model=UserProfile)
def me(
    sp=Depends(get_spotify),
    session: UserSession = Depends(get_current_session),
) -> UserProfile:
    request_id = next(ME_ROUTE_COUNTER)
    print(f"[api.playlists] /api/me #{request_id} start")
    profile = sp.current_user()
    print(f"[api.playlists] /api/me #{request_id} done")

    return UserProfile(
        id=profile["id"],
        display_name=profile.get("display_name"),
        images=normalize_images(profile.get("images")),
        total_playlists=0,
        csrf_token=session.csrf_token,
    )


@router.get("/playlists", response_model=list[PlaylistSummary])
def playlists(sp=Depends(get_spotify)) -> list[PlaylistSummary]:
    request_id = next(PLAYLISTS_ROUTE_COUNTER)
    print(f"[api.playlists] /api/playlists #{request_id} start")
    profile = sp.current_user()

    items = get_all_playlists(
        sp,
        profile["id"],
    )
    print(f"[api.playlists] /api/playlists #{request_id} done total={len(items)}")

    forbidden_ids = {
        playlist_id
        for user_id, playlist_id in FORBIDDEN_TRACK_PLAYLISTS
        if user_id == profile["id"]
    }

    for item in items:
        if item.id in forbidden_ids:
            item.tracks_readable = False

    return items


@router.get("/debug-raw-playlists")
def debug_raw_playlists(
    sp=Depends(get_spotify),
    session: UserSession = Depends(get_current_session),
) -> dict:
    request_id = next(RAW_PLAYLISTS_DEBUG_COUNTER)
    access_token = session.token_info["access_token"]
    url = "https://api.spotify.com/v1/me/playlists"
    params = {"limit": 1}
    raw_request_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    raw_prepared = requests.Request(
        "GET",
        url,
        headers=raw_request_headers,
        params=params,
    ).prepare()
    raw_request_debug = {
        "method": "GET",
        "url": url,
        "prepared_url": raw_prepared.url,
        "headers": redact_request_headers(raw_request_headers),
        "timeout": 20,
    }
    spotipy_request_debug = spotipy_playlists_request_debug(sp, params)

    print(
        f"[api.playlists] /api/debug-raw-playlists #{request_id} start "
        f"raw_request={raw_request_debug} spotipy_request={spotipy_request_debug}"
    )

    raw_result: dict
    print(
        "[api.playlists] /api/debug-raw-playlists "
        f"#{request_id} raw requests.get start url={url} params={params}"
    )
    try:
        raw_response = requests.get(
            url,
            headers=raw_request_headers,
            params=params,
            timeout=20,
        )
        raw_headers = dict(raw_response.headers)
        raw_body = raw_response.text
        raw_retry_after = raw_response.headers.get("Retry-After")
        raw_result = {
            "ok": 200 <= raw_response.status_code < 400,
            "status_code": raw_response.status_code,
            "headers": raw_headers,
            "retry_after": raw_retry_after,
            "body": raw_body,
        }
        print(
            "[api.playlists] /api/debug-raw-playlists "
            f"#{request_id} raw status={raw_response.status_code} "
            f"retry_after={raw_retry_after!r} headers={raw_headers} body={raw_body}"
        )
    except requests.RequestException as exc:
        raw_result = {
            "ok": False,
            "exception": type(exc).__name__,
            "message": str(exc),
        }
        print(
            "[api.playlists] /api/debug-raw-playlists "
            f"#{request_id} raw RequestException type={type(exc).__name__} message={str(exc)!r}"
        )

    spotipy_result: dict = {"ok": False}
    try:
        print(
            "[api.playlists] /api/debug-raw-playlists "
            f"#{request_id} spotipy current_user_playlists start limit=1"
        )
        page = sp.current_user_playlists(limit=1)
        spotipy_result = {
            "ok": True,
            "items": len(page.get("items", [])),
            "next": page.get("next"),
            "total": page.get("total"),
        }
        print(
            "[api.playlists] /api/debug-raw-playlists "
            f"#{request_id} spotipy success items={spotipy_result['items']} "
            f"total={spotipy_result['total']} next={bool(spotipy_result['next'])}"
        )
    except SpotifyException as exc:
        retry_after = exc.headers.get("Retry-After") if getattr(exc, "headers", None) else None
        spotipy_result = {
            "ok": False,
            "http_status": exc.http_status,
            "msg": exc.msg,
            "reason": str(exc.reason) if exc.reason is not None else None,
            "headers": dict(exc.headers) if getattr(exc, "headers", None) else {},
            "retry_after": retry_after,
        }
        print(
            "[api.playlists] /api/debug-raw-playlists "
            f"#{request_id} spotipy SpotifyException status={exc.http_status!r} "
            f"msg={exc.msg!r} reason={exc.reason!r} "
            f"retry_after={retry_after!r} "
            f"headers={spotipy_result['headers']}"
        )

    comparison = {
        "raw_status_code": raw_result.get("status_code"),
        "spotipy_http_status": spotipy_result.get("http_status"),
        "raw_succeeded": raw_result.get("ok") is True,
        "spotipy_succeeded": spotipy_result.get("ok") is True,
        "raw_succeeded_spotipy_failed": raw_result.get("ok") is True and spotipy_result.get("ok") is False,
        "both_returned_429": raw_result.get("status_code") == 429 and spotipy_result.get("http_status") == 429,
    }
    print(f"[api.playlists] /api/debug-raw-playlists #{request_id} comparison={comparison}")

    return {
        "request_construction": {
            "raw": raw_request_debug,
            "spotipy": spotipy_request_debug,
        },
        "spotipy": spotipy_result,
        "raw": raw_result,
        "comparison": comparison,
    }


@router.get("/debug-profile")
def debug_profile(
    session: UserSession = Depends(get_current_session),
) -> dict:
    request_id = next(RAW_ENDPOINT_DEBUG_COUNTER)
    return raw_spotify_get_debug(
        request_id,
        "profile",
        "/v1/me",
        "https://api.spotify.com/v1/me",
        session,
    )


@router.get("/debug-playlist-by-id")
def debug_playlist_by_id(
    playlist_id: str = Query(...),
    session: UserSession = Depends(get_current_session),
) -> dict:
    request_id = next(RAW_ENDPOINT_DEBUG_COUNTER)
    escaped_playlist_id = quote(playlist_id, safe="")
    return raw_spotify_get_debug(
        request_id,
        "playlist-by-id",
        f"/v1/playlists/{playlist_id}",
        f"https://api.spotify.com/v1/playlists/{escaped_playlist_id}",
        session,
    )


@router.get("/debug-playlist-items")
def debug_playlist_items(
    playlist_id: str = Query(...),
    session: UserSession = Depends(get_current_session),
) -> dict:
    request_id = next(RAW_ENDPOINT_DEBUG_COUNTER)
    escaped_playlist_id = quote(playlist_id, safe="")
    return raw_spotify_get_debug(
        request_id,
        "playlist-items",
        f"/v1/playlists/{playlist_id}/items",
        f"https://api.spotify.com/v1/playlists/{escaped_playlist_id}/items",
        session,
        params={"limit": 1},
    )


@router.get("/playlists/{playlist_id}/tracks", response_model=TrackPage)
def playlist_tracks(
    playlist_id: str,
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = None,
    artist: str | None = None,
    album: str | None = None,
    min_duration_ms: int | None = Query(None, ge=0),
    max_duration_ms: int | None = Query(None, ge=0),
    sort_by: str = Query(
        "added_at",
        pattern="^(name|artist|album|duration_ms|added_at)$",
    ),
    sort_order: str = Query(
        "desc",
        pattern="^(asc|desc)$",
    ),
    sp=Depends(get_spotify),
    session: UserSession = Depends(get_current_session),
) -> TrackPage:
    request_id = next(TRACKS_ROUTE_COUNTER)
    print(f"[api.playlists] /api/playlists/{playlist_id}/tracks #{request_id} start")

    profile = sp.current_user()

    key = forbidden_playlist_key(
        session.spotify_user_id or profile["id"],
        playlist_id,
    )

    if key in FORBIDDEN_TRACK_PLAYLISTS:
        raise playlist_tracks_forbidden()

    try:
        playlist = sp.playlist(
            playlist_id,
            fields="id,name,images,owner(id,display_name),tracks(total),public,collaborative",
        )
    except SpotifyException as exc:
        if exc.http_status == 404:
            raise ApiError(
                404,
                "playlist_not_found",
                "Playlist was not found in your Spotify library.",
            ) from exc
        raise

    selected_playlist = normalize_playlist(playlist, profile["id"])

    if not selected_playlist.id:
        raise ApiError(
            404,
            "playlist_not_found",
            "Playlist was not found in your Spotify library.",
        )

    if not selected_playlist.tracks_readable:
        FORBIDDEN_TRACK_PLAYLISTS.add(key)
        raise playlist_tracks_forbidden()

    try:
        tracks, total, has_more = get_playlist_tracks_page(
            sp,
            playlist_id,
            limit=limit,
            offset=offset,
        )

    except SpotifyException as exc:
        if exc.http_status == 403:
            FORBIDDEN_TRACK_PLAYLISTS.add(key)
            raise playlist_tracks_forbidden() from exc
        raise
    print(f"[api.playlists] /api/playlists/{playlist_id}/tracks #{request_id} spotify tracks loaded total={total}")

    search_value = (search or "").lower().strip()

    if search_value:
        tracks = [
            track
            for track in tracks
            if (
                search_value in track.name.lower()
                or search_value in track.album.lower()
                or any(
                    search_value in artist_name.lower()
                    for artist_name in track.artists
                )
            )
        ]

    if artist:
        tracks = [
            track
            for track in tracks
            if artist.lower() in [name.lower() for name in track.artists]
        ]

    if album:
        tracks = [
            track
            for track in tracks
            if track.album.lower() == album.lower()
        ]

    if min_duration_ms is not None:
        tracks = [
            track
            for track in tracks
            if track.duration_ms >= min_duration_ms
        ]

    if max_duration_ms is not None:
        tracks = [
            track
            for track in tracks
            if track.duration_ms <= max_duration_ms
        ]

    reverse = sort_order == "desc"

    key_map = {
        "name": lambda track: track.name.lower(),
        "artist": lambda track: ", ".join(track.artists).lower(),
        "album": lambda track: track.album.lower(),
        "duration_ms": lambda track: track.duration_ms,
        "added_at": lambda track: track.added_at or "",
    }

    tracks = sorted(
        tracks,
        key=key_map[sort_by],
        reverse=reverse,
    )

    artists = sorted(
        {
            artist_name
            for track in tracks
            for artist_name in track.artists
        }
    )

    albums = sorted(
        {
            track.album
            for track in tracks
        }
    )

    next_offset = offset + limit if has_more else None

    return TrackPage(
        playlist_id=playlist_id,
        tracks=tracks,
        total=total,
        offset=offset,
        limit=limit,
        next_offset=next_offset,
        has_more=has_more,
        artists=artists,
        albums=albums,
    )


@router.post(
    "/playlists/create",
    response_model=PlaylistSummary,
    dependencies=[Depends(require_csrf)],
)
def create_playlist(
    payload: CreatePlaylistRequest,
    sp=Depends(get_spotify),
) -> PlaylistSummary:

    user = sp.current_user()

    playlist = sp.user_playlist_create(
        user=user["id"],
        name=payload.name,
        public=payload.public,
        description=payload.description,
    )
    clear_playlist_cache(user["id"])

    return normalize_playlist(
        playlist,
        user["id"],
    )
