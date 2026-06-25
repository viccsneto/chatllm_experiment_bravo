from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession, User
from backend.routers.auth import _get_current_user
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.openrouter import OpenRouterConfigError, generate_reply, stream_reply


logger = logging.getLogger("chat")
logger.setLevel(logging.INFO)

router = APIRouter(dependencies=[Depends(_get_current_user)])

_TITLE_PROMPT = (
    "Create a short title (max 6 words) for this conversation. "
    "Respond with ONLY the title, nothing else. "
    "Never respond with 'Nova conversa' or 'New conversation'."
)


def _ensure_session(session_id: int | None, current_user: User, db: Session) -> ChatSession:
    if session_id:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Sessao nao encontrada")
        return session
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    session = ChatSession(user_id=current_user.id, title="Nova conversa", created_at=now, updated_at=now)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


async def _generate_title(user_msg: str, reply: str, model: str) -> str | None:
    for attempt in range(2):
        try:
            title, _ = await generate_reply(
                user_message=f"{user_msg}\n\n{reply}",
                history=[],
                model=model,
                system_prompt=_TITLE_PROMPT,
            )
            clean = title[:60].strip()
            if clean.lower() == "nova conversa":
                logger.warning("Titulo gerado foi 'Nova conversa', ignorando")
                return None
            logger.info("Titulo gerado: %s", clean)
            return clean
        except RuntimeError as exc:
            logger.warning("Tentativa %d de gerar titulo falhou: %s", attempt + 1, exc)
            if attempt == 0:
                continue
            logger.error("Titulo nao pode ser gerado apos 2 tentativas")
            return None
    return None


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(_get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    session = _ensure_session(payload.session_id, current_user, db)

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

    db.add(ChatMessage(session_id=session.id, role="user", content=payload.message, model=resolved_model))
    db.add(ChatMessage(session_id=session.id, role="assistant", content=reply, model=resolved_model))

    title = None
    logger.info("Verificando titulo da sessao %d: '%s'", session.id, session.title)
    if session.title == "Nova conversa":
        logger.info("Sessao %d sem titulo definitivo, gerando...", session.id)
        title = await _generate_title(payload.message, reply, resolved_model)
        if title:
            session.title = title
            from datetime import datetime, timezone
            session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            logger.info("Titulo salvo na sessao %d: %s", session.id, title)

    db.commit()

    return ChatResponse(reply=reply, model=resolved_model, session_id=session.id, title=title)


@router.post("/api/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    current_user: User = Depends(_get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    session = _ensure_session(payload.session_id, current_user, db)
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
            db.add(
                ChatMessage(session_id=session.id, role="user", content=payload.message, model=resolved_model)
            )
            db.add(
                ChatMessage(session_id=session.id, role="assistant", content=full_reply, model=resolved_model)
            )
            db.commit()

            title = None
            if session.title == "Nova conversa":
                logger.info("Stream: sessao %d sem titulo, gerando...", session.id)
                title = await _generate_title(payload.message, full_reply, resolved_model)
                if title:
                    session.title = title
                    from datetime import datetime, timezone
                    session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                    db.commit()
                    logger.info("Stream: titulo salvo: %s", title)

            yield f"data: {json.dumps({'done': True, 'session_id': session.id, 'title': title}, ensure_ascii=True)}\n\n"
        else:
            yield f"data: {json.dumps({'done': True, 'session_id': session.id}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
