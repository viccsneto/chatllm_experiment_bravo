from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.jwt import create_token, verify_token
from backend.models import User
from backend.schemas.auth import AuthResponse, LoginRequest, SignupRequest, UserResponse


logger = logging.getLogger("auth")
logging.basicConfig(level=logging.INFO)

router = APIRouter()

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _get_current_user_or_none(authorization: str | None = None, db: Session | None = None) -> User | None:
    if not authorization or not db:
        return None
    token = _extract_token(authorization)
    if not token:
        return None
    user_id = verify_token(token)
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id).first()


def _get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> User:
    logger.info("=== _get_current_user called ===")
    logger.info(f"Authorization header raw: {authorization}")
    token = _extract_token(authorization or "")
    if not token:
        logger.warning("No Bearer token found in authorization header")
        raise HTTPException(status_code=401, detail="Token de autenticacao nao fornecido.")
    logger.info(f"Extracted token (first 30 chars): {token[:30]}...")
    user_id = verify_token(token)
    if user_id is None:
        logger.warning(f"Token verification failed for token: {token[:30]}...")
        raise HTTPException(status_code=401, detail="Token invalido ou expirado.")
    logger.info(f"Token verified, user_id: {user_id}")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        logger.warning(f"User not found for id: {user_id}")
        raise HTTPException(status_code=401, detail="Usuario nao encontrado.")
    logger.info(f"Authenticated user: {user.email}")
    return user


def _extract_token(authorization: str) -> str | None:
    """Extrai o token Bearer do header Authorization."""
    if not authorization:
        return None
    parts = authorization.split()
    logger.info(f"Authorization parts: {parts}")
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


@router.post("/api/auth/signup", response_model=AuthResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
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

    token = create_token(user.id)

    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at.isoformat() if user.created_at else None,
        ),
        token=token,
        message="Conta criada com sucesso.",
    )


@router.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
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

    token = create_token(user.id)

    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at.isoformat() if user.created_at else None,
        ),
        token=token,
        message="Login realizado com sucesso.",
    )


@router.post("/api/auth/logout")
def logout():
    return {"message": "Logout realizado com sucesso."}


@router.get("/api/auth/me", response_model=UserResponse)
def me(
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    user = _get_current_user_or_none(authorization, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Nao autenticado. Faca login primeiro.")
    return UserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )