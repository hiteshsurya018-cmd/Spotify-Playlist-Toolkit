from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_session, get_spotify, require_csrf
from app.db import get_db
from app.models.db import UserSession
from app.models.schemas import DuplicateSummary, TransferRequest, TransferResult, UndoResult
from app.services.transfer import detect_duplicates, transfer_tracks, undo_transfer

router = APIRouter(prefix="/api/tracks", tags=["tracks"])


@router.post("/duplicates", response_model=DuplicateSummary, dependencies=[Depends(require_csrf)])
def duplicates(payload: TransferRequest, sp=Depends(get_spotify)) -> DuplicateSummary:
    return detect_duplicates(sp, payload.destination_playlist_id, payload.track_uris)


@router.post("/copy", response_model=TransferResult, dependencies=[Depends(require_csrf)])
def copy_tracks(
    payload: TransferRequest,
    sp=Depends(get_spotify),
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> TransferResult:
    result = transfer_tracks(sp, session, "copy", payload)
    db.add(session)
    db.commit()
    return result


@router.post("/move", response_model=TransferResult, dependencies=[Depends(require_csrf)])
def move_tracks(
    payload: TransferRequest,
    sp=Depends(get_spotify),
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> TransferResult:
    result = transfer_tracks(sp, session, "move", payload)
    db.add(session)
    db.commit()
    return result


@router.post("/undo", response_model=UndoResult, dependencies=[Depends(require_csrf)])
def undo(
    sp=Depends(get_spotify),
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> UndoResult:
    restored, message = undo_transfer(sp, session)
    db.add(session)
    db.commit()
    return UndoResult(restored=restored, action="undo", message=message)
