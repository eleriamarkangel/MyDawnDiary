from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_otp_hash: Mapped[str | None] = mapped_column(String(64))
    email_otp_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_otp_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_otp_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    email_otp_window_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_otp_sends_in_window: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reset_code_hash: Mapped[str | None] = mapped_column(String(64))
    reset_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reset_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reset_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reset_window_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reset_sends_in_window: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    display_name: Mapped[str | None] = mapped_column(String(120))
    time_zone: Mapped[str] = mapped_column(String(64))
    theme: Mapped[str] = mapped_column(String(20), default="orange-yellow", server_default="orange-yellow")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    diaries: Mapped[list["DailyDiary"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    social_drafts: Mapped[list["SocialDraft"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class DailyDiary(Base):
    __tablename__ = "daily_diaries"
    __table_args__ = (UniqueConstraint("user_id", "diary_date", name="uq_diary_user_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    diary_date: Mapped[date] = mapped_column(Date)
    ai_combined_entry: Mapped[str | None] = mapped_column(Text)
    edited_combined_entry: Mapped[str | None] = mapped_column(Text)
    combined_entry_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    combined_entry_edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    combined_entry_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped[User] = relationship(back_populates="diaries")
    records: Mapped[list["Record"]] = relationship(back_populates="diary", cascade="all, delete-orphan")
    notes: Mapped[list["Note"]] = relationship(back_populates="diary", cascade="all, delete-orphan")


class Record(Base):
    __tablename__ = "records"
    __table_args__ = (CheckConstraint("status IN ('draft', 'complete', 'trashed')", name="ck_record_status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    diary_id: Mapped[str] = mapped_column(ForeignKey("daily_diaries.id", ondelete="CASCADE"), index=True)
    title: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(12), default="draft", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ai_summary: Mapped[str | None] = mapped_column(Text)
    edited_summary: Mapped[str | None] = mapped_column(Text)
    summary_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary_edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    next_position: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    diary: Mapped[DailyDiary] = relationship(back_populates="records")
    entries: Mapped[list["ConversationEntry"]] = relationship(back_populates="record", cascade="all, delete-orphan", order_by="ConversationEntry.position")

    @property
    def diary_date(self) -> date:
        return self.diary.diary_date


class ConversationEntry(Base):
    __tablename__ = "conversation_entries"
    __table_args__ = (
        UniqueConstraint("record_id", "position", name="uq_entry_record_position"),
        CheckConstraint("speaker IN ('user', 'assistant')", name="ck_entry_speaker"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    record_id: Mapped[str] = mapped_column(ForeignKey("records.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    speaker: Mapped[str] = mapped_column(String(12))
    content: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str | None] = mapped_column(String(120))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    record: Mapped[Record] = relationship(back_populates="entries")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    diary_id: Mapped[str] = mapped_column(ForeignKey("daily_diaries.id", ondelete="CASCADE"), index=True)
    record_id: Mapped[str | None] = mapped_column(ForeignKey("records.id", ondelete="SET NULL"), index=True)
    title: Mapped[str | None] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    diary: Mapped[DailyDiary] = relationship(back_populates="notes")
    record: Mapped[Record | None] = relationship()

    @property
    def diary_date(self) -> date:
        return self.diary.diary_date


class SocialDraft(Base):
    __tablename__ = "social_drafts"
    __table_args__ = (CheckConstraint("status IN ('draft', 'approved')", name="ck_social_draft_status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_kind: Mapped[str | None] = mapped_column(String(12))
    source_id: Mapped[str | None] = mapped_column(String(36))
    platform: Mapped[str | None] = mapped_column(String(60))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default="draft")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped[User] = relationship(back_populates="social_drafts")
