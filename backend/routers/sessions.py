from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ChatMessage, ChatSession, User
from backend.routers.auth import get_current_user
from backend.schemas.sessions import ChatSessionDetail, ChatSessionResponse


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def get_owned_session(db: Session, user: User, session_id: int) -> ChatSession:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Conversa nao encontrada.")
    return session


@router.post("", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatSession:
    session = ChatSession(user_id=user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("", response_model=list[ChatSessionResponse])
def list_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ChatSession]:
    return (
        db.query(ChatSession)
        .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.id)
        .filter(ChatSession.user_id == user.id)
        .group_by(ChatSession.id)
        .order_by(
            func.max(ChatMessage.id).desc(),
            ChatSession.updated_at.desc(),
            ChatSession.id.desc(),
        )
        .all()
    )


@router.get("/{session_id}", response_model=ChatSessionDetail)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatSession:
    return get_owned_session(db, user, session_id)
