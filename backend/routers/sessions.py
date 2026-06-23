from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ChatMessage, ChatSession
from backend.routers.auth import get_current_user
from backend.models import User as UserModel
from backend.schemas.chat import (
    ChatSessionCreate,
    ChatSessionList,
    ChatSessionMessages,
    ChatSessionOut,
    ChatTitleUpdate,
)

router = APIRouter()


@router.get("/api/sessions", response_model=ChatSessionList)
def list_sessions(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista todas as sessoes do usuario, da mais recente para a mais antiga."""
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


@router.post("/api/sessions", response_model=ChatSessionOut, status_code=201)
def create_session(
    payload: ChatSessionCreate = None,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cria uma nova sessao de chat vazia para o usuario."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    session = ChatSession(
        user_id=current_user.id,
        title="Nova conversa",
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return ChatSessionOut(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/api/sessions/{session_id}/messages", response_model=ChatSessionMessages)
def get_session_messages(
    session_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna as mensagens de uma sessao, garantindo que pertence ao usuario."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada.")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return ChatSessionMessages(
        session_id=session_id,
        messages=[
            {"role": m.role, "content": m.content}
            for m in messages
        ],
    )


@router.put("/api/sessions/{session_id}/title", response_model=ChatSessionOut)
def update_session_title(
    session_id: int,
    payload: ChatTitleUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Atualiza o titulo de uma sessao. Usado para titulo automatico."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada.")

    # So atualiza se ainda for "Nova conversa" (titulo automatico uma unica vez)
    if session.title == "Nova conversa" and payload.title.strip():
        session.title = payload.title.strip()
        db.commit()
        db.refresh(session)

    return ChatSessionOut(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )