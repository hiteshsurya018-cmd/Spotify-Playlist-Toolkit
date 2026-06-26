import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.deps import get_spotify
from app.services.spotify_client import get_playlist_tracks_page

router = APIRouter(prefix="/api/export", tags=["export"])


def selected_tracks(sp, playlist_id: str, track_uris: str):
    wanted = {item for item in track_uris.split(",") if item}
    tracks = []
    offset = 0
    while True:
        page_tracks, _, has_more = get_playlist_tracks_page(sp, playlist_id, limit=100, offset=offset)
        tracks.extend([track for track in page_tracks if track.uri in wanted])
        if not has_more:
            break
        offset += 100
    return tracks


@router.get("/csv")
def export_csv(
    playlist_id: str = Query(...),
    track_uris: str = Query(...),
    sp=Depends(get_spotify),
) -> StreamingResponse:
    tracks = selected_tracks(sp, playlist_id, track_uris)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["uri", "name", "artists", "album", "duration_ms", "added_at"])
    for track in tracks:
        writer.writerow([track.uri, track.name, "; ".join(track.artists), track.album, track.duration_ms, track.added_at])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=selected-tracks.csv"},
    )


@router.get("/json")
def export_json(
    playlist_id: str = Query(...),
    track_uris: str = Query(...),
    sp=Depends(get_spotify),
) -> JSONResponse:
    tracks = selected_tracks(sp, playlist_id, track_uris)
    return JSONResponse([track.model_dump() for track in tracks])
