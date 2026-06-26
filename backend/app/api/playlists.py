from fastapi import APIRouter, Depends, Query
from spotipy.exceptions import SpotifyException

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
    get_all_playlists,
    get_playlist_tracks_page,
    normalize_images,
    normalize_playlist,
)

router = APIRouter(prefix="/api", tags=["playlists"])

FORBIDDEN_TRACK_PLAYLISTS: set[tuple[str, str]] = set()


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


@router.get("/me", response_model=UserProfile)
def me(
    sp=Depends(get_spotify),
    session: UserSession = Depends(get_current_session),
) -> UserProfile:
    profile = sp.current_user()
    playlists = get_all_playlists(sp, profile["id"])

    return UserProfile(
        id=profile["id"],
        display_name=profile.get("display_name"),
        images=normalize_images(profile.get("images")),
        total_playlists=len(playlists),
        csrf_token=session.csrf_token,
    )


@router.get("/playlists", response_model=list[PlaylistSummary])
def playlists(sp=Depends(get_spotify)) -> list[PlaylistSummary]:
    profile = sp.current_user()

    items = get_all_playlists(
        sp,
        profile["id"],
    )

    forbidden_ids = {
        playlist_id
        for user_id, playlist_id in FORBIDDEN_TRACK_PLAYLISTS
        if user_id == profile["id"]
    }

    for item in items:
        if item.id in forbidden_ids:
            item.tracks_readable = False

    return items


@router.get("/debug-token")
def debug_token(session: UserSession = Depends(get_current_session)):
    return session.token_info


@router.get("/debug-playlist")
def debug_playlist(
    playlist_id: str,
    sp=Depends(get_spotify),
):
    return sp.playlist(playlist_id)


@router.get("/debug-tracks")
def debug_tracks(
    playlist_id: str,
    sp=Depends(get_spotify),
):
    return sp.playlist_items(
        playlist_id,
        limit=1,
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

    profile = sp.current_user()

    key = forbidden_playlist_key(
        session.spotify_user_id or profile["id"],
        playlist_id,
    )

    if key in FORBIDDEN_TRACK_PLAYLISTS:
        raise playlist_tracks_forbidden()

    user_playlists = get_all_playlists(
        sp,
        profile["id"],
    )

    selected_playlist = next(
        (
            playlist
            for playlist in user_playlists
            if playlist.id == playlist_id
        ),
        None,
    )

    if not selected_playlist:
        raise ApiError(
            404,
            "playlist_not_found",
            "Playlist was not found in your Spotify library.",
        )

    if not selected_playlist.tracks_readable:
        FORBIDDEN_TRACK_PLAYLISTS.add(key)
        raise playlist_tracks_forbidden()

    print("\n========== PLAYLIST DEBUG ==========")
    print("Current User ID:", profile["id"])
    print("Playlist ID:", selected_playlist.id)
    print("Playlist Name:", selected_playlist.name)
    print("Playlist Owner:", selected_playlist.owner)
    print("Playlist Owner ID:", selected_playlist.owner_id)
    print("Collaborative:", selected_playlist.collaborative)
    print("Tracks Readable:", selected_playlist.tracks_readable)
    print("====================================\n")

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

    return normalize_playlist(
        playlist,
        user["id"],
    )
