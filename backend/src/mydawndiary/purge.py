"""Run with `python -m mydawndiary.purge` from a scheduled server job."""

from sqlalchemy import select

from .database import session_factory
from .models import Note, Record
from .service import utc_now


def purge_expired() -> tuple[int, int]:
    now = utc_now()
    with session_factory()() as db:
        notes = db.scalars(select(Note).where(Note.deleted_at.is_not(None), Note.purge_after <= now)).all()
        for note in notes:
            db.delete(note)
        records = db.scalars(select(Record).where(Record.status == "trashed", Record.purge_after <= now)).all()
        for record in records:
            linked_notes = db.scalars(select(Note).where(Note.record_id == record.id)).all()
            for note in linked_notes:
                note.record_id = None
            db.delete(record)
        db.commit()
    return len(records), len(notes)


if __name__ == "__main__":
    record_count, note_count = purge_expired()
    print(f"Purged {record_count} conversations and {note_count} notes")
