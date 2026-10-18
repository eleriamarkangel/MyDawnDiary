from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import DailyDiary, Note, Record, User
from .schemas import NoteOut, RecordDetail, TrashOut
from .security import current_user
from .service import utc_now


router = APIRouter(tags=["recycle bin"])


@router.get("/trash", response_model=TrashOut)
def list_trash(user: User = Depends(current_user), db: Session = Depends(get_db)) -> TrashOut:
    now = utc_now()
    records = db.scalars(
        select(Record).join(DailyDiary).where(
            DailyDiary.user_id == user.id, Record.status == "trashed", Record.purge_after > now
        ).order_by(Record.deleted_at.desc())
    ).all()
    notes = db.scalars(
        select(Note).join(DailyDiary).where(
            DailyDiary.user_id == user.id, Note.deleted_at.is_not(None), Note.purge_after > now
        ).order_by(Note.deleted_at.desc())
    ).all()
    return TrashOut(
        records=[RecordDetail.model_validate(record) for record in records],
        notes=[NoteOut.model_validate(note) for note in notes],
    )
