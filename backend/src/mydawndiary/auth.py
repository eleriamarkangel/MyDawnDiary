import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .email_delivery import EmailDeliveryError, send_verification_email
from .models import User, utc_now
from .schemas import EmailVerificationCode, EmailVerificationRequest, LoginIn, PasswordChange, ProfilePatch, RegisterIn, TokenOut, UserOut
from .security import current_user, hash_password, make_token, verify_password


router = APIRouter(prefix="/auth", tags=["accounts"])
logger = logging.getLogger(__name__)
OTP_LIFETIME = timedelta(minutes=10)
OTP_RESEND_WAIT = timedelta(minutes=5)
OTP_SEND_WINDOW = timedelta(hours=1)
OTP_MAX_SENDS = 5
OTP_MAX_ATTEMPTS = 5


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _otp_hash(user: User, code: str) -> str:
    return hmac.new(
        get_settings().jwt_secret.encode("utf-8"),
        f"email-verification:{user.id}:{code}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _can_send(user: User, now: datetime) -> bool:
    if user.email_otp_sent_at is not None and now - _aware(user.email_otp_sent_at) < OTP_RESEND_WAIT:
        return False
    if user.email_otp_window_started_at is not None and now - _aware(user.email_otp_window_started_at) < OTP_SEND_WINDOW:
        return user.email_otp_sends_in_window < OTP_MAX_SENDS
    return True


def _issue_code(user: User, now: datetime) -> str:
    if user.email_otp_window_started_at is None or now - _aware(user.email_otp_window_started_at) >= OTP_SEND_WINDOW:
        user.email_otp_window_started_at = now
        user.email_otp_sends_in_window = 0
    previous_hash = user.email_otp_hash
    while True:
        code = f"{secrets.randbelow(1_000_000):06d}"
        code_hash = _otp_hash(user, code)
        if code_hash != previous_hash:
            break
    user.email_otp_hash = code_hash
    user.email_otp_expires_at = now + OTP_LIFETIME
    user.email_otp_sent_at = now
    user.email_otp_attempts = 0
    user.email_otp_sends_in_window += 1
    return code


@router.post(
    "/register",
    response_model=UserOut,
    status_code=201,
    responses={503: {"description": "Verification email is unavailable"}},
)
def register(body: RegisterIn, db: Session = Depends(get_db)) -> User:
    email = str(body.email).lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="Email is already registered")
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        time_zone=body.time_zone,
        display_name=body.display_name,
    )
    db.add(user)
    try:
        db.flush()
        code = _issue_code(user, utc_now())
        send_verification_email(email, code)
        db.commit()
    except EmailDeliveryError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered") from None
    db.refresh(user)
    return user


@router.post("/resend-verification", status_code=202)
def resend_verification(body: EmailVerificationRequest, db: Session = Depends(get_db)) -> None:
    email = str(body.email).lower()
    user = db.scalar(select(User).where(User.email == email).with_for_update())
    if user is None or user.email_verified_at is not None:
        return
    now = utc_now()
    if not _can_send(user, now):
        return
    code = _issue_code(user, now)
    try:
        send_verification_email(email, code)
        db.commit()
    except EmailDeliveryError:
        db.rollback()
        logger.error("Verification resend delivery failed")


@router.post("/verify-email", status_code=204)
def verify_email(body: EmailVerificationCode, db: Session = Depends(get_db)) -> None:
    user = db.scalar(select(User).where(User.email == str(body.email).lower()).with_for_update())
    invalid = HTTPException(status_code=400, detail="Invalid or expired verification code")
    if user is None or user.email_verified_at is not None or user.email_otp_hash is None or user.email_otp_expires_at is None:
        raise invalid
    if utc_now() >= _aware(user.email_otp_expires_at) or user.email_otp_attempts >= OTP_MAX_ATTEMPTS:
        raise invalid
    if not hmac.compare_digest(_otp_hash(user, body.code), user.email_otp_hash):
        user.email_otp_attempts += 1
        db.commit()
        raise invalid
    user.email_verified_at = utc_now()
    user.email_otp_hash = None
    user.email_otp_expires_at = None
    user.email_otp_attempts = 0
    db.commit()


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = db.scalar(select(User).where(User.email == str(body.email).lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.email_verified_at is None:
        raise HTTPException(status_code=403, detail="Verify your email before signing in")
    return TokenOut(access_token=make_token(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> User:
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: ProfilePatch, user: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
    if "display_name" in body.model_fields_set:
        user.display_name = body.display_name
    if "time_zone" in body.model_fields_set:
        if body.time_zone is None:
            raise HTTPException(status_code=422, detail="Time zone cannot be empty")
        user.time_zone = body.time_zone
    db.commit()
    db.refresh(user)
    return user


@router.post("/change-password", status_code=204)
def change_password(body: PasswordChange, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    user.token_version += 1
    db.commit()


@router.post("/sign-out-all", status_code=204)
def sign_out_all(user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    user.token_version += 1
    db.commit()
