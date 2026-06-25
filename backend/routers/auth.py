from __future__ import annotations

import hashlib
import os

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AuthSession, User
from backend.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MeResponse,
    MessageResponse,
    SignupRequest,
)


router = APIRouter()


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _generate_token() -> str:
    return hashlib.sha256(os.urandom(32)).hexdigest()


def _get_current_user(token: str | None = Header(None), db: Session = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="Token nao fornecido")
    auth_session = db.query(AuthSession).filter(AuthSession.token == token).first()
    if not auth_session:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado")
    user = db.query(User).filter(User.id == auth_session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado")
    return user


@router.post("/api/auth/signup", response_model=AuthResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email ja cadastrado")

    user = User(email=payload.email, password_hash=_hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = _generate_token()
    db.add(AuthSession(user_id=user.id, token=token))
    db.commit()

    return AuthResponse(token=token, email=user.email)


@router.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or user.password_hash != _hash_password(payload.password):
        raise HTTPException(status_code=401, detail="Email ou senha invalidos")

    token = _generate_token()
    db.add(AuthSession(user_id=user.id, token=token))
    db.commit()

    return AuthResponse(token=token, email=user.email)


@router.post("/api/auth/logout", response_model=MessageResponse)
def logout(token: str | None = Header(None), db: Session = Depends(get_db)):
    if token:
        auth_session = db.query(AuthSession).filter(AuthSession.token == token).first()
        if auth_session:
            db.delete(auth_session)
            db.commit()
    return MessageResponse(message="Logout realizado com sucesso")


@router.get("/api/auth/me", response_model=MeResponse)
def me(current_user: User = Depends(_get_current_user)):
    return MeResponse(email=current_user.email)