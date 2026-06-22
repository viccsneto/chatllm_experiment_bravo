from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession, User
from backend.routers.auth import get_current_user
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.openrouter import OpenRouterConfigError, generate_reply, generate_title, stream_reply


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def _load_session_history(session_id: int, db: Session) -> list[dict]:
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [{"role": msg.role, "content": msg.content} for msg in msgs]


def _get_user_session(
    session_id: int | None,
    user: User,
    db: Session,
) -> ChatSession:
    """Retorna a sessao do usuario. Se session_id for None, cria uma nova."""
    if session_id is not None:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
            .first()
        )
        if session:
            return session
    session = ChatSession(user_id=user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


async def _auto_title(session: ChatSession, db: Session) -> None:
    """Gera titulo automatico para a sessao em background."""
    await asyncio.sleep(0.5)
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(4)
        .all()
    )
    if not msgs:
        return
    conversation = [{"role": m.role, "content": m.content} for m in msgs]
    title = await generate_title(conversation=conversation)
    session.title = title
    db.commit()


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    session = _get_user_session(payload.session_id, current_user, db)
    history = _load_session_history(session.id, db)

    try:
        reply, model_name = await generate_reply(
            user_message=payload.message,
            history=history,
            model=payload.model,
        )
    except OpenRouterConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    resolved_model = payload.model or model_name or OPENROUTER_MODEL_DEFAULT

    db.add(ChatMessage(session_id=session.id, role="user", content=payload.message, model=resolved_model))
    db.add(ChatMessage(session_id=session.id, role="assistant", content=reply, model=resolved_model))
    db.commit()

    if session.title == "Nova conversa":
        asyncio.create_task(_auto_title(session, db))

    return ChatResponse(reply=reply, model=resolved_model)


@router.post("/api/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    session = _get_user_session(payload.session_id, current_user, db)
    history = _load_session_history(session.id, db)
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT
    needs_title = session.title == "Nova conversa"

    async def event_generator():
        nonlocal needs_title
        full_reply = ""
        try:
            async for delta in stream_reply(
                user_message=payload.message,
                history=history,
                model=payload.model,
            ):
                full_reply += delta
                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=True)}\n\n"
        except OpenRouterConfigError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=True)}\n\n"
            return
        except RuntimeError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=True)}\n\n"
            return

        if full_reply.strip():
            db.add(ChatMessage(session_id=session.id, role="user", content=payload.message, model=resolved_model))
            db.add(ChatMessage(session_id=session.id, role="assistant", content=full_reply, model=resolved_model))
            db.commit()

            if needs_title:
                asyncio.create_task(_auto_title(session, db))

        yield f"data: {json.dumps({'done': True, 'session_id': session.id}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
