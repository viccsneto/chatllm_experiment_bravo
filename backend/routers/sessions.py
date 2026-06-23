from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from backend.auth import create_access_token, get_current_user
from backend.database import get_db
from backend.models import ChatMessage, Session, User
from backend.schemas.session import ChatMessageOut, SessionCreateResponse, SessionOut

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("/", response_model=list[SessionOut])
def list_sessions(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna todas as sessoes do usuario, ordenadas pela mais recente."""
    sessions = (
        db.query(Session)
        .filter(Session.user_id == current_user.id)
        .order_by(Session.updated_at.desc())
        .all()
    )
    return sessions


@router.post("/", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria uma nova sessao sem titulo."""
    session = Session(user_id=current_user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}/messages", response_model=list[ChatMessageOut])
def get_session_messages(
    session_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna todas as mensagens de uma sessao."""
    session = db.query(Session).filter(Session.id == session_id, Session.user_id == current_user.id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessao nao encontrada.",
        )

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return messages


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove uma sessao e todas as suas mensagens."""
    session = db.query(Session).filter(Session.id == session_id, Session.user_id == current_user.id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessao nao encontrada.",
        )
    db.delete(session)
    db.commit()