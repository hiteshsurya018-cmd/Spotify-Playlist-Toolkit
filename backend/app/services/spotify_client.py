import time
from collections.abc import Callable
from itertools import count
from threading import Lock
from typing import Any

import spotipy
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOAuth

from app.core.config import Settings
from app.models.schemas import Image, PlaylistSummary, Track

SCOPES = " ".join(
    [
        "playlist-read-private",
        "playlist-read-collaborative",
        "playlist-modify-private",
        "playlist-modify-public",
        "user-read-private",
    ]
)

PLAYLIST_FETCH_COUNTER = count(1)
PLAYLIST_CACHE_TTL_SECONDS = 60
PLAYLIST_CACHE_LOCK = Lock()
PLAYLIST_CACHE: dict[str, tuple[float, list[PlaylistSummary]]] = {}


def oauth_manager(settings: Settings) -> SpotifyOAuth:
    return SpotifyOAuth(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
        redirect_uri=settings.spotify_redirect_uri,
        scope=SCOPES,
        open_browser=False,
        cache_handler=None,
        show_dialog=False,
    )


def retry_spotify(call: Callable[[], Any], attempts: int = 4) -> Any:
    for index in range(attempts):
        try:
            return call()
        except SpotifyException as exc:
            attempt_number = index + 1
            retry_after_header = exc.headers.get("Retry-After") if getattr(exc, "headers", None) else None
            print(
                "[spotify_client] SpotifyException "
                f"attempt={attempt_number}/{attempts} "
                f"http_status={exc.http_status!r} "
                f"msg={exc.msg!r} "
                f"reason={exc.reason!r} "
                f"headers={dict(exc.headers) if getattr(exc, 'headers', None) else {}} "
                f"retry_after={retry_after_header!r}"
            )
            if exc.http_status == 429 and index < attempts - 1:
                retry_after = 2
                if getattr(exc, "headers", None):
                    try:
                        retry_after = int(retry_after_header or retry_after)
                    except (TypeError, ValueError):
                        retry_after = 2
                time.sleep(retry_after)
                continue
            if exc.http_status and 500 <= exc.http_status < 600 and index < attempts - 1:
                time.sleep(2**index)
                continue
            raise
    return call()


def describe_spotify_session(sp: spotipy.Spotify) -> dict[str, Any]:
    session = getattr(sp, "_session", None)
    details: dict[str, Any] = {
        "spotify_retries": getattr(sp, "retries", None),
        "spotify_status_retries": getattr(sp, "status_retries", None),
        "spotify_status_forcelist": list(getattr(sp, "status_forcelist", []) or []),
        "spotify_backoff_factor": getattr(sp, "backoff_factor", None),
        "session_type": type(session).__name__ if session is not None else None,
    }

    if hasattr(session, "get_adapter"):
        try:
            adapter = session.get_adapter("https://api.spotify.com/v1/me/playlists")
            max_retries = getattr(adapter, "max_retries", None)
            details.update(
                {
                    "adapter_type": type(adapter).__name__,
                    "adapter_max_retries_total": getattr(max_retries, "total", None),
                    "adapter_max_retries_status": getattr(max_retries, "status", None),
                    "adapter_max_retries_connect": getattr(max_retries, "connect", None),
                    "adapter_max_retries_read": getattr(max_retries, "read", None),
                    "adapter_status_forcelist": list(getattr(max_retries, "status_forcelist", []) or []),
                    "adapter_allowed_methods": sorted(getattr(max_retries, "allowed_methods", []) or []),
                    "adapter_backoff_factor": getattr(max_retries, "backoff_factor", None),
                    "adapter_raise_on_status": getattr(max_retries, "raise_on_status", None),
                }
            )
        except Exception as exc:
            details["adapter_inspection_error"] = repr(exc)

    return details


def spotify_from_token(token_info: dict) -> spotipy.Spotify:
    sp = spotipy.Spotify(
        auth=token_info["access_token"],
        requests_timeout=20,
        retries=0,
        status_retries=0,
    )
    print(f"[spotify_client] Spotify client constructed {describe_spotify_session(sp)}")
    return sp


def clone_playlists(playlists: list[PlaylistSummary]) -> list[PlaylistSummary]:
    return [playlist.model_copy() for playlist in playlists]


def get_cached_playlists(current_user_id: str | None) -> list[PlaylistSummary] | None:
    if not current_user_id:
        return None

    now = time.monotonic()
    with PLAYLIST_CACHE_LOCK:
        cached = PLAYLIST_CACHE.get(current_user_id)
        if not cached:
            return None

        expires_at, playlists = cached
        if expires_at <= now:
            PLAYLIST_CACHE.pop(current_user_id, None)
            return None

        return clone_playlists(playlists)


def cache_playlists(current_user_id: str | None, playlists: list[PlaylistSummary]) -> None:
    if not current_user_id:
        return

    with PLAYLIST_CACHE_LOCK:
        PLAYLIST_CACHE[current_user_id] = (
            time.monotonic() + PLAYLIST_CACHE_TTL_SECONDS,
            clone_playlists(playlists),
        )


def clear_playlist_cache(current_user_id: str | None = None) -> None:
    with PLAYLIST_CACHE_LOCK:
        if current_user_id:
            PLAYLIST_CACHE.pop(current_user_id, None)
        else:
            PLAYLIST_CACHE.clear()


def normalize_images(images: list[dict] | None) -> list[Image]:
    return [Image(url=item["url"], width=item.get("width"), height=item.get("height")) for item in images or []]


def normalize_playlist(item: dict, current_user_id: str | None = None) -> PlaylistSummary:
    owner = item.get("owner", {})
    owner_id = owner.get("id")
    collaborative = item.get("collaborative", False)
    return PlaylistSummary(
        id=item["id"],
        name=item["name"],
        images=normalize_images(item.get("images")),
        owner=owner.get("display_name") or owner.get("id", "Unknown"),
        owner_id=owner_id,
        tracks_total=item.get("tracks", {}).get("total", 0),
        public=item.get("public"),
        collaborative=collaborative,
        tracks_readable=bool(current_user_id and owner_id == current_user_id) or collaborative,
    )


def normalize_track(item: dict) -> Track | None:
    track = item.get("track") or item.get("item") or item

    if not track:
        return None

    album = track.get("album") or {}
    images = album.get("images") or []

    return Track(
        id=track.get("id"),
        uri=track.get("uri", ""),
        name=track.get("name", "Unknown track"),
        artists=[artist.get("name", "Unknown artist") for artist in track.get("artists", [])],
        album=album.get("name", "Unknown album"),
        album_art=images[0]["url"] if images else None,
        duration_ms=track.get("duration_ms", 0),
        added_at=item.get("added_at"),
    )


def playlist_items_page(
    sp: spotipy.Spotify,
    playlist_id: str,
    fields: str,
    limit: int,
    offset: int,
) -> dict:
    playlist_spotify_id = sp._get_id("playlist", playlist_id)

    return sp._get(
        f"playlists/{playlist_spotify_id}/items",
        fields=fields,
        limit=limit,
        offset=offset,
        additional_types="track",
    )


def playlist_add_items_v2(sp: spotipy.Spotify, playlist_id: str, uris: list[str]) -> dict:
    playlist_spotify_id = sp._get_id("playlist", playlist_id)

    return sp._post(
        f"playlists/{playlist_spotify_id}/items",
        payload={
            "uris": uris,
        },
    )


def playlist_remove_items_v2(sp: spotipy.Spotify, playlist_id: str, uris: list[str]) -> dict:
    playlist_spotify_id = sp._get_id("playlist", playlist_id)

    return sp._delete(
        f"playlists/{playlist_spotify_id}/items",
        payload={
            "items": [{"uri": uri} for uri in uris],
        },
    )


def get_all_playlists(sp: spotipy.Spotify, current_user_id: str | None = None) -> list[PlaylistSummary]:
    fetch_id = next(PLAYLIST_FETCH_COUNTER)
    print(f"[spotify_client] get_all_playlists #{fetch_id} start current_user_id={current_user_id}")
    cached = get_cached_playlists(current_user_id)
    if cached is not None:
        print(f"[spotify_client] get_all_playlists #{fetch_id} cache hit total={len(cached)}")
        return cached

    playlists: list[PlaylistSummary] = []
    offset = 0
    while True:
        print(f"[spotify_client] get_all_playlists #{fetch_id} -> current_user_playlists limit=50 offset={offset}")
        print(
            "[spotify_client] current_user_playlists session before call "
            f"fetch_id={fetch_id} offset={offset} {describe_spotify_session(sp)}"
        )

        def fetch_current_user_playlists() -> dict:
            print(
                "[spotify_client] current_user_playlists outbound start "
                f"fetch_id={fetch_id} limit=50 offset={offset}"
            )
            started_at = time.monotonic()
            try:
                result = sp.current_user_playlists(limit=50, offset=offset)
                elapsed_ms = round((time.monotonic() - started_at) * 1000, 1)
                print(
                    "[spotify_client] current_user_playlists outbound done "
                    f"fetch_id={fetch_id} offset={offset} elapsed_ms={elapsed_ms} "
                    f"items={len(result.get('items', []))} next={bool(result.get('next'))}"
                )
                return result
            except SpotifyException as exc:
                elapsed_ms = round((time.monotonic() - started_at) * 1000, 1)
                print(
                    "[spotify_client] current_user_playlists outbound SpotifyException "
                    f"fetch_id={fetch_id} offset={offset} elapsed_ms={elapsed_ms} "
                    f"http_status={exc.http_status!r} msg={exc.msg!r} reason={exc.reason!r} "
                    f"headers={dict(exc.headers) if getattr(exc, 'headers', None) else {}}"
                )
                raise

        page = retry_spotify(fetch_current_user_playlists)
        playlists.extend(normalize_playlist(item, current_user_id) for item in page.get("items", []))
        if not page.get("next"):
            break
        offset += 50
    cache_playlists(current_user_id, playlists)
    print(f"[spotify_client] get_all_playlists #{fetch_id} done total={len(playlists)}")
    return playlists


def get_all_playlist_track_uris(sp: spotipy.Spotify, playlist_id: str) -> set[str]:
    uris: set[str] = set()
    offset = 0
    while True:
        page = retry_spotify(
            lambda: playlist_items_page(sp, playlist_id, fields="items(item(uri)),next", limit=50, offset=offset)
        )
        for item in page.get("items", []):
            track = item.get("track") or item.get("item")
            if track and track.get("uri"):
                uris.add(track["uri"])
        if not page.get("next"):
            break
        offset += 50
    return uris


def get_playlist_tracks_page(
    sp: spotipy.Spotify,
    playlist_id: str,
    limit: int,
    offset: int,
) -> tuple[list[Track], int, bool]:

    fields = "items(added_at,item(id,uri,type,name,artists(name),album(name,images),duration_ms)),total,next"

    tracks: list[Track] = []
    total = 0
    next_offset = offset
    has_more = False

    while len(tracks) < limit:
        page_limit = min(50, limit - len(tracks))

        page = retry_spotify(
            lambda: playlist_items_page(
                sp,
                playlist_id,
                fields=fields,
                limit=page_limit,
                offset=next_offset,
            )
        )

        tracks.extend(
            track
            for item in page.get("items", [])
            if (track := normalize_track(item))
        )

        total = page.get("total", total or len(tracks))
        has_more = bool(page.get("next"))

        if not has_more:
            break

        next_offset += page_limit

    return tracks, total, has_more
