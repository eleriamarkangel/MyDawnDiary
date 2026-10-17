from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import DailyDiary, Note, Record, User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def local_today(user: User, now: datetime) -> date:
    return now.astimezone(ZoneInfo(user.time_zone)).date()


def allowed_new_date(user: User, chosen: date | None, now: datetime) -> date:
    today = local_today(user, now)
    selected = chosen or today
    if selected not in (today, today - timedelta(days=1)):
        raise HTTPException(status_code=422, detail="New content can be saved only to today or yesterday")
    return selected


def owned_diary(db: Session, user: User, diary_date: date) -> DailyDiary:
    diary = db.scalar(select(DailyDiary).where(DailyDiary.user_id == user.id, DailyDiary.diary_date == diary_date))
    if diary is None:
        raise HTTPException(status_code=404, detail="Diary not found")
    return diary


def get_or_create_diary(db: Session, user: User, diary_date: date) -> DailyDiary:
    diary = db.scalar(select(DailyDiary).where(DailyDiary.user_id == user.id, DailyDiary.diary_date == diary_date))
    if diary is not None:
        return diary
    diary = DailyDiary(user_id=user.id, diary_date=diary_date)
    db.add(diary)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        diary = db.scalar(select(DailyDiary).where(DailyDiary.user_id == user.id, DailyDiary.diary_date == diary_date))
        if diary is None:
            raise
    return diary


def owned_record(db: Session, user: User, record_id: str, *, include_trash: bool = False) -> Record:
    record = db.scalar(
        select(Record)
        .join(DailyDiary, Record.diary_id == DailyDiary.id)
        .where(Record.id == record_id, DailyDiary.user_id == user.id)
    )
    if record is None or (record.status == "trashed" and not include_trash):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return record


def owned_note(db: Session, user: User, note_id: str, *, include_trash: bool = False) -> Note:
    note = db.scalar(
        select(Note)
        .join(DailyDiary, Note.diary_id == DailyDiary.id)
        .where(Note.id == note_id, DailyDiary.user_id == user.id)
    )
    if note is None or (note.deleted_at is not None and not include_trash):
        raise HTTPException(status_code=404, detail="Note not found")
    return note


def mark_stale(diary: DailyDiary) -> None:
    if diary.ai_combined_entry is not None:
        diary.combined_entry_stale = True


def clear_combined(diary: DailyDiary) -> None:
    # A deleted source may be quoted in the generated entry, so remove both versions.
    diary.ai_combined_entry = None
    diary.edited_combined_entry = None
    diary.combined_entry_generated_at = None
    diary.combined_entry_edited_at = None
    diary.combined_entry_stale = True


def trash_deadline(now: datetime) -> datetime:
    return now + timedelta(days=3)
