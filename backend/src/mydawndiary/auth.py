from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .schemas import LoginIn, PasswordChange, ProfilePatch, RegisterIn, TokenOut, UserOut
from .security import current_user, hash_password, make_token, verify_password


router = APIRouter(prefix="/auth", tags=["accounts"])


@router.post("/register", response_model=UserOut, status_code=201)
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
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered") from None
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = db.scalar(select(User).where(User.email == str(body.email).lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
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
