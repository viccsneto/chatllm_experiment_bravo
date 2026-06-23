from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession, User
from backend.routers.auth import get_current_user
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.openrouter import OpenRouterConfigError, generate_reply, stream_reply


router = APIRouter(dependencies=[Depends(get_current_user)])

_TITLE_PROMPT = (
    "Resuma o assunto desta conversa em ate 6 palavras, sem pontuacao, "
    "apenas as palavras-chave. Nao use aspas."
)


def _auto_title(history: list[dict]) -> str | None:
    """Gera titulo automatico com base na primeira interacao."""
    try:
        reply, _ = generate_reply(user_message=_TITLE_PROMPT, history=history[:2])
        title = reply.strip().strip('"').strip("'")
        return title[:255] if title else None
    except Exception:
        return None


def _persist_messages(db: Session, user_id: int, session_id: int | None, message: str, reply: str, model: str):
    """Persiste mensagens e gera titulo automatico se necessario."""
    session = None
    if session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        ).first()

    sid = session.id if session else None

    db.add(ChatMessage(session_id=sid, session_key="default", role="user", content=message, model=model))
    db.add(ChatMessage(session_id=sid, session_key="default", role="assistant", content=reply, model=model))

    if session and session.title in ("Nova Conversa", None, ""):
        auto_title = _auto_title([
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply},
        ])
        if auto_title:
            session.title = auto_title

    db.commit()


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
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
    _persist_messages(db, current_user.id, payload.session_id, payload.message, reply, resolved_model)

    return ChatResponse(reply=reply, model=resolved_model)


@router.post("/api/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT

    async def event_generator():
        full_reply = ""
        try:
            async for delta in stream_reply(
                user_message=payload.message,
                history=[item.model_dump() for item in payload.history],
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
            _persist_messages(db, current_user.id, payload.session_id, payload.message, full_reply, resolved_model)

        yield f"data: {json.dumps({'done': True}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
