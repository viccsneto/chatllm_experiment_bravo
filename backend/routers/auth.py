from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Session as SessionModel
from backend.models import User
from backend.schemas.auth import AuthLoginRequest, AuthRegisterRequest, AuthResponse, UserMeResponse


router = APIRouter()


def _get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("session_token")
    if not token:
        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nao autenticado")

    session = db.query(SessionModel).filter(SessionModel.token == token).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao invalida")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario nao encontrado")

    return user


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
        path="/",
    )


@router.post("/api/auth/register", response_model=AuthResponse)
def register(payload: AuthRegisterRequest, response: Response, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email ja cadastrado")

    user = User(email=payload.email)
    user.password_hash = user.hash_password(payload.password)
    db.add(user)
    db.flush()

    token = SessionModel.generate_token()
    db.add(SessionModel(user_id=user.id, token=token))
    db.commit()

    _set_session_cookie(response, token)
    return AuthResponse(token=token, email=user.email)


@router.post("/api/auth/login", response_model=AuthResponse)
def login(payload: AuthLoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.verify_password(payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha invalidos")

    token = SessionModel.generate_token()
    db.add(SessionModel(user_id=user.id, token=token))
    db.commit()

    _set_session_cookie(response, token)
    return AuthResponse(token=token, email=user.email)


@router.post("/api/auth/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("session_token") or request.headers.get("Authorization", "").removeprefix("Bearer ")
    if token:
        db.query(SessionModel).filter(SessionModel.token == token).delete()
        db.commit()
    return {"message": "Desconectado com sucesso"}


@router.get("/api/auth/me", response_model=UserMeResponse)
def me(current_user: User = Depends(_get_current_user)):
    return UserMeResponse(email=current_user.email)