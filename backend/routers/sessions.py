from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ChatMessage, ChatSession
from backend.routers.auth import _get_current_user
from backend.models import User
from backend.schemas.session import ChatSessionOut


router = APIRouter()


@router.get("/api/sessions")
def list_sessions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_user),
) -> list[ChatSessionOut]:
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return [ChatSessionOut.model_validate(s) for s in sessions]


@router.post("/api/sessions", response_model=ChatSessionOut)
def create_session(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_user),
) -> ChatSession:
    session = ChatSession(user_id=current_user.id, title=None)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/api/sessions/{session_id}/messages")
def get_session_messages(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_user),
) -> list[dict]:
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessao nao encontrada")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
        for m in messages
    ]


@router.delete("/api/sessions/{session_id}")
def delete_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(_get_current_user),
) -> dict:
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sessao nao encontrada")

    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"message": "Sessao removida"}