from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import get_db
from .models import DailyDiary, Note, Record, User
from .schemas import ActivityDay, ActivityReview
from .security import current_user
from .service import local_today, utc_now


router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/activity", response_model=ActivityReview)
def activity_review(user: User = Depends(current_user), db: Session = Depends(get_db)) -> ActivityReview:
    end = local_today(user, utc_now())
    start = end - timedelta(days=29)
    days = {start + timedelta(days=i): ActivityDay(diary_date=start + timedelta(days=i), conversations=0, notes=0, messages=0) for i in range(30)}

    records = db.execute(
        select(DailyDiary.diary_date, func.count(Record.id), func.coalesce(func.sum(Record.next_position - 1), 0))
        .join(Record, Record.diary_id == DailyDiary.id)
        .where(DailyDiary.user_id == user.id, DailyDiary.diary_date.between(start, end), Record.status == "complete")
        .group_by(DailyDiary.diary_date)
    ).all()
    for day, count, messages in records:
        days[day].conversations = count
        days[day].messages = messages

    notes = db.execute(
        select(DailyDiary.diary_date, func.count(Note.id))
        .join(Note, Note.diary_id == DailyDiary.id)
        .where(DailyDiary.user_id == user.id, DailyDiary.diary_date.between(start, end), Note.deleted_at.is_(None))
        .group_by(DailyDiary.diary_date)
    ).all()
    for day, count in notes:
        days[day].notes = count

    rows = list(days.values())
    return ActivityReview(
        start_date=start,
        end_date=end,
        active_days=sum(day.conversations > 0 or day.notes > 0 for day in rows),
        conversations=sum(day.conversations for day in rows),
        notes=sum(day.notes for day in rows),
        messages=sum(day.messages for day in rows),
        days=rows,
    )
