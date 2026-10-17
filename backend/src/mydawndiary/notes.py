from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import DailyDiary, Note, User
from .schemas import NoteCreate, NoteOut, NotePatch
from .security import current_user
from .service import allowed_new_date, clear_combined, get_or_create_diary, mark_stale, owned_note, owned_record, trash_deadline, utc_now


router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", response_model=list[NoteOut])
def list_notes(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[Note]:
    return list(db.scalars(
        select(Note).join(DailyDiary).where(DailyDiary.user_id == user.id, Note.deleted_at.is_(None))
        .order_by(Note.created_at.desc(), Note.id.desc()).limit(limit).offset(offset)
    ))


@router.post("", response_model=NoteOut, status_code=201)
def create_note(
    body: NoteCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Note:
    linked = owned_record(db, user, body.record_id) if body.record_id else None
    selected_date = body.diary_date or (linked.diary.diary_date if linked else None)
    diary_date = allowed_new_date(user, selected_date, utc_now())
    diary = get_or_create_diary(db, user, diary_date)
    if linked is not None and linked.diary_id != diary.id:
        raise HTTPException(status_code=422, detail="A linked conversation must be in the same daily diary")
    note = Note(diary_id=diary.id, record_id=linked.id if linked else None, title=body.title, content=body.content)
    db.add(note)
    mark_stale(diary)
    db.commit()
    db.refresh(note)
    return note


@router.get("/{note_id}", response_model=NoteOut)
def get_note(note_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Note:
    return owned_note(db, user, note_id)


@router.patch("/{note_id}", response_model=NoteOut)
def edit_note(
    note_id: str,
    body: NotePatch,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Note:
    note = owned_note(db, user, note_id)
    changed = body.model_fields_set
    if "title" in changed:
        note.title = body.title
    if "content" in changed:
        if body.content is None:
            raise HTTPException(status_code=422, detail="Note content cannot be empty")
        note.content = body.content
    if "record_id" in changed:
        if body.record_id is None:
            note.record_id = None
        else:
            linked = owned_record(db, user, body.record_id)
            if linked.diary_id != note.diary_id:
                raise HTTPException(status_code=422, detail="A linked conversation must be in the same daily diary")
            note.record_id = linked.id
    if changed:
        mark_stale(note.diary)
        db.commit()
        db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    note = owned_note(db, user, note_id)
    now = utc_now()
    note.deleted_at = now
    note.purge_after = trash_deadline(now)
    clear_combined(note.diary)
    db.commit()


@router.post("/{note_id}/restore", response_model=NoteOut)
def restore_note(note_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Note:
    note = owned_note(db, user, note_id, include_trash=True)
    if note.deleted_at is None:
        raise HTTPException(status_code=409, detail="Note is not in the recycle bin")
    expiry = note.purge_after
    if expiry is None or expiry.replace(tzinfo=expiry.tzinfo or timezone.utc) <= utc_now():
        raise HTTPException(status_code=410, detail="Restore period has expired")
    note.deleted_at = None
    note.purge_after = None
    mark_stale(note.diary)
    db.commit()
    db.refresh(note)
    return note
