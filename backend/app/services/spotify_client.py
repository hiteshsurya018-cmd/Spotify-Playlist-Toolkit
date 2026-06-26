import time
from collections.abc import Callable
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
            if exc.http_status == 429 and index < attempts - 1:
                retry_after = 2
                if getattr(exc, "headers", None):
                    retry_after = int(exc.headers.get("Retry-After", retry_after))
                time.sleep(retry_after)
                continue
            if exc.http_status and 500 <= exc.http_status < 600 and index < attempts - 1:
                time.sleep(2**index)
                continue
            raise
    return call()


def spotify_from_token(token_info: dict) -> spotipy.Spotify:
    return spotipy.Spotify(auth=token_info["access_token"], requests_timeout=20, retries=0)


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

    print("\n========== TRACK DEBUG ==========")
    print(track)
    print("TYPE:", track.get("type") if track else None)
    print("URI:", track.get("uri") if track else None)
    print("=================================\n")

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
    print("CUSTOM PLAYLIST_ITEMS_PAGE EXECUTED")
    playlist_spotify_id = sp._get_id("playlist", playlist_id)

    return sp._get(
        f"playlists/{playlist_spotify_id}/items",
        fields=fields,
        limit=limit,
        offset=offset,
        additional_types="track",
    )


def debug_add_track(sp: spotipy.Spotify, playlist_id: str):
    return sp._post(
        f"playlists/{playlist_id}/items",
        payload={
            "uris": ["spotify:track:11dFghVXANMlKmJXsNCbNl"],
        },
    )


def get_all_playlists(sp: spotipy.Spotify, current_user_id: str | None = None) -> list[PlaylistSummary]:
    playlists: list[PlaylistSummary] = []
    offset = 0
    while True:
        page = retry_spotify(lambda: sp.current_user_playlists(limit=50, offset=offset))
        playlists.extend(normalize_playlist(item, current_user_id) for item in page.get("items", []))
        if not page.get("next"):
            break
        offset += 50
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
    print("GET_PLAYLIST_TRACKS_PAGE EXECUTED")

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

        print("\n========== RAW ITEMS ==========")

        for item in page.get("items", []):
            print(item)

        print("================================\n")

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
