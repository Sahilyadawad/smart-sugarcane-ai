"""Authentication and profile endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    hash_password,
    token_expires_in_seconds,
    verify_password,
)
from app.database import get_db
from app.models import User
from app.schemas.auth import (
    MessageResponse,
    PasswordChange,
    Token,
    UserCreate,
    UserLogin,
    UserOut,
    UserUpdate,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _issue_token(user: User) -> Token:
    return Token(
        access_token=create_access_token(user.id, {"email": user.email, "name": user.name}),
        token_type="bearer",
        expires_in=token_expires_in_seconds(),
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> Token:
    email = payload.email.lower().strip()
    existing = db.scalars(select(User).where(User.email == email)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists. Try signing in instead.",
        )

    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        phone=(payload.phone or "").strip() or None,
        farm_location=(payload.farm_location or "").strip() or None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_token(user)


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> Token:
    user = db.scalars(select(User).where(User.email == payload.email.lower().strip())).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        # Identical message whether the email is unknown or the password is wrong,
        # so the endpoint does not leak which accounts exist. The hint is safe for
        # the same reason - it says nothing about this particular email, and it
        # matters because accounts do not carry across deployments: someone who
        # registered locally has no account on the hosted database.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Incorrect email or password. If you have not registered on this "
                "deployment yet, create an account - accounts are not shared between "
                "the local and hosted versions."
            ),
        )
    return _issue_token(user)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if value is not None:
            setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return UserOut.model_validate(current_user)


@router.post("/me/password", response_model=MessageResponse)
def change_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Your current password is incorrect."
        )
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return MessageResponse(detail="Password updated. Use the new password next time you sign in.")


@router.post("/logout", response_model=MessageResponse)
def logout(current_user: User = Depends(get_current_user)) -> MessageResponse:
    # JWTs are stateless: the client discards the token. Documented here so the
    # behaviour is not mistaken for a missing implementation.
    return MessageResponse(
        detail="Signed out. The access token has been discarded by the client; JWTs are stateless "
        "so there is no server-side session to destroy."
    )


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest) -> MessageResponse:
    """Password reset architecture placeholder.

    Deliberately does NOT send email: no mail provider is configured, and
    pretending to send a reset link would be worse than saying so. The route
    exists so the flow can be completed by adding an email service - see
    docs/API.md for the intended token flow.
    """
    return MessageResponse(
        detail=(
            "Password reset by email is not available - this build has no mail provider "
            "configured, so no reset link can be sent. Register a new account instead, or "
            "see docs/API.md for how to wire up the reset-token flow."
        )
    )
