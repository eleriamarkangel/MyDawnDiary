from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import DailyDiary, SocialDraft, User
from .schemas import SocialDraftCreate, SocialDraftOut, SocialDraftPatch
from .security import current_user
from .service import owned_note, owned_record, utc_now


router = APIRouter(prefix="/social-drafts", tags=["social drafts"])


def owned_draft(db: Session, user: User, draft_id: str) -> SocialDraft:
    draft = db.scalar(select(SocialDraft).where(SocialDraft.id == draft_id, SocialDraft.user_id == user.id))
    if draft is None:
        raise HTTPException(status_code=404, detail="Social draft not found")
    return draft


@router.post("", response_model=SocialDraftOut, status_code=201)
def create_draft(body: SocialDraftCreate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> SocialDraft:
    if (body.source_kind is None) != (body.source_id is None):
        raise HTTPException(status_code=422, detail="Source kind and ID must be supplied together")
    if body.source_kind == "diary":
        source = db.scalar(select(DailyDiary).where(DailyDiary.id == body.source_id, DailyDiary.user_id == user.id))
        if source is None:
            raise HTTPException(status_code=404, detail="Source not found")
    elif body.source_kind == "record":
        owned_record(db, user, body.source_id)
    elif body.source_kind == "note":
        owned_note(db, user, body.source_id)
    draft = SocialDraft(
        user_id=user.id,
        source_kind=body.source_kind,
        source_id=body.source_id,
        platform=body.platform,
        content=body.content,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


@router.get("", response_model=list[SocialDraftOut])
def list_drafts(
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[SocialDraft]:
    return list(db.scalars(select(SocialDraft).where(SocialDraft.user_id == user.id).order_by(SocialDraft.created_at.desc()).limit(limit).offset(offset)))


@router.get("/{draft_id}", response_model=SocialDraftOut)
def get_draft(draft_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> SocialDraft:
    return owned_draft(db, user, draft_id)


@router.patch("/{draft_id}", response_model=SocialDraftOut)
def edit_draft(draft_id: str, body: SocialDraftPatch, user: User = Depends(current_user), db: Session = Depends(get_db)) -> SocialDraft:
    draft = owned_draft(db, user, draft_id)
    if draft.status != "draft":
        raise HTTPException(status_code=409, detail="An approved draft cannot be edited")
    if "content" in body.model_fields_set:
        if body.content is None:
            raise HTTPException(status_code=422, detail="Content cannot be empty")
        draft.content = body.content
    if "platform" in body.model_fields_set:
        draft.platform = body.platform
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/{draft_id}/approve", response_model=SocialDraftOut)
def approve_draft(draft_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> SocialDraft:
    draft = owned_draft(db, user, draft_id)
    if draft.status != "draft":
        raise HTTPException(status_code=409, detail="Draft is already approved")
    draft.status = "approved"
    draft.approved_at = utc_now()
    db.commit()
    db.refresh(draft)
    return draft


@router.delete("/{draft_id}", status_code=204)
def delete_draft(draft_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    db.delete(owned_draft(db, user, draft_id))
    db.commit()
