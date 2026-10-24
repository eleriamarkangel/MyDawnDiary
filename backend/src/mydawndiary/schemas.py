from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    time_zone: str
    display_name: str | None = Field(default=None, max_length=120)

    @field_validator("time_zone")
    @classmethod
    def valid_time_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Use an IANA time zone such as Asia/Manila") from exc
        return value


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class EmailVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationCode(EmailVerificationRequest):
    code: str = Field(pattern=r"^[0-9]{6}$")


class PasswordReset(EmailVerificationCode):
    new_password: str = Field(min_length=12, max_length=128)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=128)


Theme = Literal["orange-yellow", "blue-yellow", "green-yellow"]


class AccountDelete(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)


class ProfilePatch(BaseModel):
    theme: Theme | None = None
    display_name: str | None = Field(default=None, max_length=120)
    time_zone: str | None = None

    @field_validator("time_zone")
    @classmethod
    def valid_time_zone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise ValueError("Use an IANA time zone such as Asia/Manila") from exc
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    email_verified_at: datetime | None
    display_name: str | None
    time_zone: str
    theme: Theme
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DiaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    diary_date: date
    ai_combined_entry: str | None
    edited_combined_entry: str | None
    combined_entry_stale: bool
    created_at: datetime
    updated_at: datetime


class DiaryDetail(DiaryOut):
    records: list["RecordOut"]
    notes: list["NoteOut"]


class RecordCreate(BaseModel):
    diary_date: date | None = None
    title: str | None = Field(default=None, max_length=200)


class RecordTitlePatch(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class RecordComplete(BaseModel):
    ai_summary: str = Field(min_length=1, max_length=100_000)
    diary_date: date | None = None


class SummaryEdit(BaseModel):
    text: str = Field(min_length=1, max_length=100_000)


class EntryCreate(BaseModel):
    speaker: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=100_000)
    model_name: str | None = Field(default=None, max_length=120)
    occurred_at: datetime | None = None


class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    position: int
    speaker: str
    content: str
    model_name: str | None
    occurred_at: datetime | None
    created_at: datetime


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    diary_id: str
    diary_date: date
    title: str | None
    status: str
    started_at: datetime
    ended_at: datetime | None
    ai_summary: str | None
    edited_summary: str | None
    deleted_at: datetime | None
    purge_after: datetime | None
    created_at: datetime
    updated_at: datetime


class RecordDetail(RecordOut):
    entries: list[EntryOut]


class CombinedGenerated(BaseModel):
    text: str = Field(min_length=1, max_length=200_000)
    replace_user_edit: bool = False


class NoteCreate(BaseModel):
    diary_date: date | None = None
    title: str | None = Field(default=None, max_length=200)
    content: str = Field(min_length=1, max_length=200_000)
    record_id: str | None = None


class NotePatch(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=200_000)
    record_id: str | None = None


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    diary_id: str
    diary_date: date
    record_id: str | None
    title: str | None
    content: str
    deleted_at: datetime | None
    purge_after: datetime | None
    created_at: datetime
    updated_at: datetime


class TrashOut(BaseModel):
    records: list[RecordDetail]
    notes: list[NoteOut]


class SocialDraftCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)
    platform: str | None = Field(default=None, max_length=60)
    source_kind: Literal["diary", "record", "note"] | None = None
    source_id: str | None = None


class SocialDraftPatch(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=20_000)
    platform: str | None = Field(default=None, max_length=60)


class SocialDraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_kind: str | None
    source_id: str | None
    platform: str | None
    content: str
    status: str
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ActivityDay(BaseModel):
    diary_date: date
    conversations: int
    notes: int
    messages: int


class ActivityReview(BaseModel):
    start_date: date
    end_date: date
    active_days: int
    conversations: int
    notes: int
    messages: int
    days: list[ActivityDay]
