from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ChatMessage, ChatSession, User
from backend.routers.auth import _get_current_user
from backend.schemas.session import (
    ChatMessageOut,
    ChatSessionList,
    ChatSessionOut,
    SessionMessagesOut,
)


router = APIRouter(dependencies=[Depends(_get_current_user)])


@router.post("/api/sessions", response_model=ChatSessionOut, status_code=201)
def create_session(current_user: User = Depends(_get_current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    session = ChatSession(user_id=current_user.id, title="Nova conversa", created_at=now, updated_at=now)
    db.add(session)
    db.commit()
    db.refresh(session)
    return ChatSessionOut(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/api/sessions", response_model=ChatSessionList)
def list_sessions(current_user: User = Depends(_get_current_user), db: Session = Depends(get_db)):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return ChatSessionList(
        sessions=[
            ChatSessionOut(
                id=s.id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in sessions
        ]
    )


@router.get("/api/sessions/{session_id}/messages", response_model=SessionMessagesOut)
def get_session_messages(
    session_id: int,
    current_user: User = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return SessionMessagesOut(
        messages=[
            ChatMessageOut(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                model=m.model,
                created_at=m.created_at,
            )
            for m in messages
        ]
    )


@router.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    current_user: User = Depends(_get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()