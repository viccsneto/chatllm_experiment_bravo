from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from backend.config import SESSION_EXPIRE_HOURS
from backend.database import get_db
from backend.models import Session as SessionModel
from backend.models import User
from backend.schemas.auth import AuthResponse, LoginRequest, MeResponse, SignupRequest

router = APIRouter()

SESSION_COOKIE_NAME = "__Host-session_token"


def _make_session_cookie(token: str) -> dict:
    """Retorna os parametros do cookie de sessao conforme OWASP."""
    return {
        "key": SESSION_COOKIE_NAME,
        "value": token,
        "httponly": True,
        "secure": True,
        "samesite": "strict",
        "path": "/",
    }


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def _create_session(user: User, db: Session) -> str:
    """Cria uma nova sessao para o usuario e retorna o token."""
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=SESSION_EXPIRE_HOURS)
    session = SessionModel(user_id=user.id, token=token, expires_at=expires_at)
    db.add(session)
    db.commit()
    return token


def _delete_session(token: str | None, db: Session) -> bool:
    """Remove a sessao do banco. Retorna True se encontrou e removeu."""
    if not token:
        return False
    session = db.query(SessionModel).filter(SessionModel.token == token).first()
    if not session:
        return False
    db.delete(session)
    db.commit()
    return True


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependency: extrai o usuario autenticado a partir do cookie de sessao."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Nao autenticado.")

    session = (
        db.query(SessionModel)
        .filter(
            SessionModel.token == token,
            SessionModel.expires_at > datetime.now(timezone.utc).replace(tzinfo=None),
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=401, detail="Sessao invalida ou expirada.")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado ou inativo.")

    return user


@router.post("/api/auth/signup", response_model=AuthResponse)
def signup(payload: SignupRequest, response: Response, db: Session = Depends(get_db)):
    """Cadastra um novo usuario e ja inicia a sessao."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email ja cadastrado.")

    user = User(
        email=payload.email,
        hashed_password=_hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = _create_session(user, db)
    cookie = _make_session_cookie(token)
    response.set_cookie(**cookie)

    return AuthResponse(email=user.email, message="Conta criada com sucesso.")


@router.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Autentica o usuario e inicia uma nova sessao."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not _verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Conta desativada.")

    token = _create_session(user, db)
    cookie = _make_session_cookie(token)
    response.set_cookie(**cookie)

    return AuthResponse(email=user.email, message="Login realizado com sucesso.")


@router.post("/api/auth/logout", response_model=AuthResponse)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """Remove a sessao atual e limpa o cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    _delete_session(token, db)

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=True,
        httponly=True,
        samesite="strict",
    )

    return AuthResponse(email="", message="Logout realizado com sucesso.")


@router.get("/api/auth/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)):
    """Retorna dados do usuario autenticado."""
    return MeResponse(email=current_user.email)