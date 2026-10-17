from datetime import timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import ConversationEntry, DailyDiary, Note, Record, User
from .schemas import EntryCreate, EntryOut, RecordComplete, RecordCreate, RecordDetail, RecordOut, RecordTitlePatch, SummaryEdit
from .security import current_user
from .service import allowed_new_date, clear_combined, get_or_create_diary, mark_stale, owned_record, trash_deadline, utc_now


router = APIRouter(prefix="/records", tags=["conversations"])


@router.get("", response_model=list[RecordOut])
def list_records(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Literal["draft", "complete"] | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[Record]:
    query = select(Record).join(DailyDiary).where(DailyDiary.user_id == user.id, Record.status != "trashed")
    if status is not None:
        query = query.where(Record.status == status)
    return list(db.scalars(query.order_by(Record.started_at.desc(), Record.id.desc()).limit(limit).offset(offset)))


@router.post("", response_model=RecordOut, status_code=201)
def start_record(
    body: RecordCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Record:
    now = utc_now()
    diary_date = allowed_new_date(user, body.diary_date, now)
    diary = get_or_create_diary(db, user, diary_date)
    record = Record(diary_id=diary.id, title=body.title, started_at=now)
    db.add(record)
    mark_stale(diary)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{record_id}", response_model=RecordDetail)
def get_record(record_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> RecordDetail:
    record = owned_record(db, user, record_id)
    entries = db.scalars(select(ConversationEntry).where(ConversationEntry.record_id == record.id).order_by(ConversationEntry.position)).all()
    return RecordDetail(**RecordOut.model_validate(record).model_dump(), entries=[EntryOut.model_validate(entry) for entry in entries])


@router.patch("/{record_id}", response_model=RecordOut)
def edit_title(
    record_id: str,
    body: RecordTitlePatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Record:
    record = owned_record(db, user, record_id)
    record.title = body.title
    db.commit()
    db.refresh(record)
    return record


@router.post("/{record_id}/entries", response_model=EntryOut, status_code=201)
def append_entry(
    record_id: str,
    body: EntryCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ConversationEntry:
    record = owned_record(db, user, record_id)
    if record.status != "draft":
        raise HTTPException(status_code=409, detail="Only an in-progress conversation accepts entries")
    # Lock the parent on PostgreSQL so concurrent turns get distinct positions.
    db.scalar(select(Record).where(Record.id == record.id).with_for_update())
    entry = ConversationEntry(
        record_id=record.id,
        position=record.next_position,
        speaker=body.speaker,
        content=body.content,
        model_name=body.model_name,
        occurred_at=body.occurred_at,
    )
    record.next_position += 1
    db.add(entry)
    mark_stale(record.diary)
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/{record_id}/complete", response_model=RecordOut)
def complete_record(
    record_id: str,
    body: RecordComplete,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Record:
    record = owned_record(db, user, record_id)
    if record.status != "draft":
        raise HTTPException(status_code=409, detail="Conversation is already complete")
    if record.next_position == 1:
        raise HTTPException(status_code=409, detail="Cannot complete an empty conversation")
    now = utc_now()
    selected = allowed_new_date(user, body.diary_date or record.diary.diary_date, now)
    if selected != record.diary.diary_date:
        old_diary = record.diary
        new_diary = get_or_create_diary(db, user, selected)
        linked_notes = db.scalars(select(Note).where(Note.record_id == record.id)).all()
        for note in linked_notes:
            note.diary = new_diary
        record.diary = new_diary
        clear_combined(old_diary)
        mark_stale(new_diary)
    record.ai_summary = body.ai_summary
    record.summary_generated_at = now
    record.ended_at = now
    record.status = "complete"
    mark_stale(record.diary)
    db.commit()
    db.refresh(record)
    return record


@router.patch("/{record_id}/summary", response_model=RecordOut)
def edit_summary(
    record_id: str,
    body: SummaryEdit,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Record:
    record = owned_record(db, user, record_id)
    if record.status != "complete":
        raise HTTPException(status_code=409, detail="Complete the conversation before editing its summary")
    record.edited_summary = body.text
    record.summary_edited_at = utc_now()
    mark_stale(record.diary)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=204)
def delete_record(record_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    record = owned_record(db, user, record_id)
    now = utc_now()
    record.status = "trashed"
    record.deleted_at = now
    record.purge_after = trash_deadline(now)
    clear_combined(record.diary)
    db.commit()


@router.post("/{record_id}/restore", response_model=RecordOut)
def restore_record(record_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Record:
    record = owned_record(db, user, record_id, include_trash=True)
    if record.status != "trashed":
        raise HTTPException(status_code=409, detail="Conversation is not in the recycle bin")
    if record.purge_after is None or record.purge_after.replace(tzinfo=record.purge_after.tzinfo or timezone.utc) <= utc_now():
        raise HTTPException(status_code=410, detail="Restore period has expired")
    record.status = "complete" if record.ended_at is not None else "draft"
    record.deleted_at = None
    record.purge_after = None
    mark_stale(record.diary)
    db.commit()
    db.refresh(record)
    return record
