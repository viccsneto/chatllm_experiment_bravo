from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import SessionLocal, get_db
from backend.models import ChatMessage, ChatSession, User
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.auth import get_current_user
from backend.services.openrouter import OpenRouterConfigError, generate_reply, stream_reply
from backend.services.titling import generate_session_title


router = APIRouter()


def _resolve_session(
    *,
    session_id: int | None,
    current_user: User,
    db: Session,
) -> ChatSession:
    """Retorna a sessao existente ou cria uma nova se session_id for None."""
    if session_id is not None:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Sessao nao encontrada.")
        return session

    session = ChatSession(user_id=current_user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _persist_messages(
    *,
    db: Session,
    session_id: int,
    user_id: int,
    user_content: str,
    assistant_content: str,
    model: str,
):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(
        ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=user_content,
            model=model,
        )
    )
    db.add(
        ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content=assistant_content,
            model=model,
        )
    )
    # Atualiza updated_at da sessao
    db.query(ChatSession).filter(ChatSession.id == session_id).update(
        {"updated_at": now}
    )
    db.commit()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    session = _resolve_session(session_id=payload.session_id, current_user=current_user, db=db)

    try:
        reply, model_name = await generate_reply(
            user_message=payload.message,
            history=[item.model_dump() for item in payload.history],
            model=payload.model,
        )
    except OpenRouterConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    resolved_model = payload.model or model_name or OPENROUTER_MODEL_DEFAULT

    _persist_messages(
        db=db,
        session_id=session.id,
        user_id=current_user.id,
        user_content=payload.message,
        assistant_content=reply,
        model=resolved_model,
    )

    # Auto-titling: se a sessao nao tem titulo, tenta gerar em background
    if session.title is None:
        asyncio.ensure_future(_try_auto_title(
            session_id=session.id,
            user_message=payload.message,
        ))

    return ChatResponse(reply=reply, model=resolved_model, session_id=session.id)


@router.post("/api/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    session = _resolve_session(session_id=payload.session_id, current_user=current_user, db=db)
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT

    async def event_generator():
        full_reply = ""
        replied = False
        try:
            async for delta in stream_reply(
                user_message=payload.message,
                history=[item.model_dump() for item in payload.history],
                model=payload.model,
            ):
                full_reply += delta
                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=True)}\n\n"
            replied = True
        except OpenRouterConfigError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=True)}\n\n"
        except RuntimeError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=True)}\n\n"

        if replied and full_reply.strip():
            _persist_messages(
                db=db,
                session_id=session.id,
                user_id=current_user.id,
                user_content=payload.message,
                assistant_content=full_reply,
                model=resolved_model,
            )

            # Auto-titling em background
            if session.title is None:
                asyncio.ensure_future(_try_auto_title(
                    session_id=session.id,
                    user_message=payload.message,
                ))

        # Sempre sinaliza done para que o frontend adote a sessao
        yield f"data: {json.dumps({'done': True, 'session_id': session.id}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


async def _try_auto_title(
    *,
    session_id: int,
    user_message: str,
):
    """Tenta gerar titulo automatico em background. Falhas silenciosas."""
    try:
        title = await generate_session_title(
            user_message=user_message,
        )
        if title:
            db = SessionLocal()
            try:
                chat_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
                if chat_session and chat_session.title is None:
                    from datetime import datetime, timezone
                    chat_session.title = title
                    chat_session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    db.commit()
            finally:
                db.close()
    except Exception:
        pass
