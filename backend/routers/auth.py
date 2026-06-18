from __future__ import annotations

import re
from datetime import datetime, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas.auth import AuthResponse, LoginRequest, SignupRequest, UserResponse


router = APIRouter()

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _get_current_user_or_none(request: Request, db: Session) -> User | None:
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id).first()


def _get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = _get_current_user_or_none(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Nao autenticado. Faca login primeiro.")
    return user


@router.post("/api/auth/signup", response_model=AuthResponse)
def signup(payload: SignupRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()

    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Formato de email invalido.")

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email ja cadastrado.")

    hashed = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt())
    user = User(
        email=email,
        password_hash=hashed.decode("utf-8"),
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    request.session["user_id"] = user.id

    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at.isoformat() if user.created_at else None,
        ),
        message="Conta criada com sucesso.",
    )


@router.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()

    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Formato de email invalido.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Email ou senha incorretos.")

    if not bcrypt.checkpw(payload.password.encode("utf-8"), user.password_hash.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos.")

    user.last_login = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()

    request.session["user_id"] = user.id

    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at.isoformat() if user.created_at else None,
        ),
        message="Login realizado com sucesso.",
    )


@router.post("/api/auth/logout")
def logout(request: Request, response: Response):
    request.session.clear()
    return {"message": "Logout realizado com sucesso."}


@router.get("/api/auth/me", response_model=UserResponse)
def me(request: Request, db: Session = Depends(get_db)):
    user = _get_current_user(request, db)
    return UserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )