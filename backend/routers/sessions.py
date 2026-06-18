from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import Header
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ChatSession, User
from backend.routers.auth import _get_current_user
from backend.schemas.session import (
    CreateSessionRequest,
    SessionDetailResponse,
    SessionListResponse,
    SessionMessageResponse,
    SessionResponse,
)
from backend.services.openrouter import generate_title


logger = logging.getLogger("sessions")
logging.basicConfig(level=logging.INFO)

router = APIRouter()


@router.post("/api/sessions", response_model=SessionResponse, status_code=201)
async def create_session(
    payload: CreateSessionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
):
    logger.info(f"[sessions] create_session user_id={user.id}")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    session = ChatSession(
        user_id=user.id,
        title="New chat",
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info(f"[sessions] sessao criada: id={session.id}, title='{session.title}'")
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at.isoformat() if session.created_at else None,
        updated_at=session.updated_at.isoformat() if session.updated_at else None,
        message_count=0,
    )


@router.get("/api/sessions", response_model=SessionListResponse)
def list_sessions(
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
):
    logger.info(f"[sessions] list_sessions user_id={user.id}")
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    logger.info(f"[sessions] list_sessions encontrou {len(sessions)} sessoes")
    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=s.id,
                title=s.title,
                created_at=s.created_at.isoformat() if s.created_at else None,
                updated_at=s.updated_at.isoformat() if s.updated_at else None,
                message_count=len(s.messages),
            )
            for s in sessions
        ]
    )


@router.get("/api/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada.")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Acesso negado a esta sessao.")

    return SessionDetailResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at.isoformat() if session.created_at else None,
        updated_at=session.updated_at.isoformat() if session.updated_at else None,
        messages=[
            SessionMessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                model=m.model,
                created_at=m.created_at.isoformat() if m.created_at else None,
            )
            for m in session.messages
        ],
    )


@router.delete("/api/sessions/{session_id}")
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(_get_current_user),
):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada.")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Acesso negado a esta sessao.")

    db.delete(session)
    db.commit()
    return {"message": "Sessao removida com sucesso."}