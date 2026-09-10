from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.config import (
    AUTH_COOKIE_NAME,
    AUTH_COOKIE_SECURE,
    AUTH_SESSION_DAYS,
)
from backend.database import get_db
from backend.models import AuthSession, User
from backend.schemas.auth import CredentialsIn, UserResponse
from backend.services.auth import (
    create_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _set_session_cookie(response: Response, token: str) -> None:
    max_age = AUTH_SESSION_DAYS * 24 * 60 * 60
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def _create_auth_session(db: Session, user: User) -> str:
    token = create_session_token()
    db.add(
        AuthSession(
            user=user,
            token_hash=hash_session_token(token),
            expires_at=_utc_now() + timedelta(days=AUTH_SESSION_DAYS),
        )
    )
    return token


def get_current_user(
    session_token: str | None = Cookie(default=None, alias=AUTH_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autenticacao necessaria.",
    )
    if not session_token:
        raise unauthorized

    auth_session = (
        db.query(AuthSession)
        .filter(
            AuthSession.token_hash == hash_session_token(session_token),
            AuthSession.expires_at > _utc_now(),
        )
        .first()
    )
    if auth_session is None:
        raise unauthorized

    return auth_session.user


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: CredentialsIn, response: Response, db: Session = Depends(get_db)) -> User:
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail ja esta cadastrado.",
        )

    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)

    try:
        db.flush()
        token = _create_auth_session(db, user)
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail ja esta cadastrado.",
        ) from exc

    _set_session_cookie(response, token)
    return user


@router.post("/login", response_model=UserResponse)
def login(payload: CredentialsIn, response: Response, db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha invalidos.",
        )

    token = _create_auth_session(db, user)
    db.commit()
    _set_session_cookie(response, token)
    return user


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(
    session_token: str | None = Cookie(default=None, alias=AUTH_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> Response:
    if session_token:
        db.query(AuthSession).filter(
            AuthSession.token_hash == hash_session_token(session_token)
        ).delete(synchronize_session=False)
        db.commit()

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/me", response_model=UserResponse)
def current_user(user: User = Depends(get_current_user)) -> User:
    return user
