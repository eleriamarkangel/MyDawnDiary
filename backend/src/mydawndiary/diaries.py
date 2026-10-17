from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import DailyDiary, Note, Record, User
from .schemas import CombinedGenerated, DiaryDetail, DiaryOut, NoteOut, RecordOut, SummaryEdit
from .security import current_user
from .service import owned_diary, utc_now


router = APIRouter(prefix="/diaries", tags=["diaries"])


@router.get("", response_model=list[DiaryOut])
def list_diaries(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[DailyDiary]:
    return list(db.scalars(
        select(DailyDiary)
        .where(DailyDiary.user_id == user.id)
        .order_by(DailyDiary.diary_date.desc())
        .limit(limit)
        .offset(offset)
    ))


@router.get("/{diary_date}", response_model=DiaryDetail)
def get_diary(diary_date: date, user: User = Depends(current_user), db: Session = Depends(get_db)) -> DiaryDetail:
    diary = owned_diary(db, user, diary_date)
    records = db.scalars(select(Record).where(Record.diary_id == diary.id, Record.status != "trashed").order_by(Record.started_at)).all()
    notes = db.scalars(select(Note).where(Note.diary_id == diary.id, Note.deleted_at.is_(None)).order_by(Note.created_at)).all()
    return DiaryDetail(
        **DiaryOut.model_validate(diary).model_dump(),
        records=[RecordOut.model_validate(record) for record in records],
        notes=[NoteOut.model_validate(note) for note in notes],
    )


@router.put("/{diary_date}/ai-entry", response_model=DiaryOut)
def store_ai_entry(
    diary_date: date,
    body: CombinedGenerated,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> DailyDiary:
    """Store AI output; the AI provider is connected in a later phase."""
    diary = owned_diary(db, user, diary_date)
    if not db.scalar(select(Record.id).where(Record.diary_id == diary.id, Record.status == "complete")) and not db.scalar(
        select(Note.id).where(Note.diary_id == diary.id, Note.deleted_at.is_(None))
    ):
        raise HTTPException(status_code=409, detail="Diary has no completed content to summarize")
    if diary.edited_combined_entry is not None and not body.replace_user_edit:
        raise HTTPException(status_code=409, detail="Regenerating would replace the user's edited daily entry")
    diary.ai_combined_entry = body.text
    diary.edited_combined_entry = None
    diary.combined_entry_generated_at = utc_now()
    diary.combined_entry_edited_at = None
    diary.combined_entry_stale = False
    db.commit()
    db.refresh(diary)
    return diary


@router.patch("/{diary_date}/entry", response_model=DiaryOut)
def edit_entry(
    diary_date: date,
    body: SummaryEdit,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> DailyDiary:
    diary = owned_diary(db, user, diary_date)
    if diary.ai_combined_entry is None:
        raise HTTPException(status_code=409, detail="Generate the combined entry before editing it")
    diary.edited_combined_entry = body.text
    diary.combined_entry_edited_at = utc_now()
    db.commit()
    db.refresh(diary)
    return diary
