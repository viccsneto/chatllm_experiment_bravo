from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession, User
from backend.routers.auth import _get_current_user
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.openrouter import OpenRouterConfigError, generate_reply, generate_title, stream_reply


logger = logging.getLogger("chat")
logging.basicConfig(level=logging.INFO)

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def _resolve_session(session_id: str | None, user: User, db: Session) -> ChatSession:
    logger.info(f"[_resolve_session] session_id={session_id}, user_id={user.id}")
    if not session_id:
        logger.info("[_resolve_session] session_id is None -> criando nova sessao")
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
        logger.info(f"[_resolve_session] nova sessao criada: id={session.id}")
        return session

    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        logger.info(f"[_resolve_session] session_id={session_id} nao encontrado no banco -> criando nova")
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
        logger.info(f"[_resolve_session] nova sessao criada: id={session.id}")
        return session

    logger.info(f"[_resolve_session] sessao encontrada: id={session.id}, user_id={session.user_id}, title={session.title}")
    if session.user_id != user.id:
        logger.warning(f"[_resolve_session] acesso negado: session.user_id={session.user_id} != user.id={user.id}")
        raise HTTPException(status_code=403, detail="Acesso negado a esta sessao.")
    return session


@router.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db), user: User = Depends(_get_current_user)) -> ChatResponse:
    logger.info(f"[chat] payload: message='{payload.message[:50]}', session_id={payload.session_id}")
    session = _resolve_session(payload.session_id, user, db)
    logger.info(f"[chat] sessao resolvida: id={session.id}, title='{session.title}'")

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
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    is_first_message = len(session.messages) == 0
    logger.info(f"[chat] persistindo: session_id={session.id}, is_first={is_first_message}, reply_len={len(reply)}")

    db.add(ChatMessage(session_id=session.id, role="user", content=payload.message, model=resolved_model, created_at=now))
    db.add(ChatMessage(session_id=session.id, role="assistant", content=reply, model=resolved_model, created_at=now))

    if is_first_message and session.title == "New chat":
        title_text = payload.message.strip()[:60]
        session.title = title_text
        logger.info(f"[chat] titulo gerado: '{session.title}'")

    session.updated_at = now
    db.commit()
    logger.info(f"[chat] commit ok. session agora tem {len(session.messages)} mensagens")

    return ChatResponse(reply=reply, model=resolved_model)


@router.post("/api/chat/stream")
async def chat_stream(payload: ChatRequest, db: Session = Depends(get_db), user: User = Depends(_get_current_user)) -> StreamingResponse:
    session = _resolve_session(payload.session_id, user, db)
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT

    async def event_generator():
        full_reply = ""
        logger.info(f"[chat_stream] Iniciando stream para session_id={session.id}, is_first={len(session.messages)==0}")
        try:
            async for delta in stream_reply(
                user_message=payload.message,
                history=[item.model_dump() for item in payload.history],
                model=payload.model,
            ):
                full_reply += delta
                yield f"data: {json.dumps({'delta': delta}, ensure_ascii=True)}\n\n"
        except OpenRouterConfigError as exc:
            logger.warning(f"[chat_stream] OpenRouterConfigError: {exc}")
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=True)}\n\n"
        except RuntimeError as exc:
            logger.warning(f"[chat_stream] RuntimeError: {exc}")
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=True)}\n\n"

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        is_first_message = len(session.messages) == 0
        logger.info(f"[chat_stream] Stream finalizado. full_reply_len={len(full_reply)}, is_first_message={is_first_message}, session.title='{session.title}'")

        # Salva mensagem do usuario sempre
        logger.info(f"[chat_stream] Salvando mensagem user na sessao {session.id}")
        db.add(
            ChatMessage(
                session_id=session.id,
                role="user",
                content=payload.message,
                model=resolved_model,
                created_at=now,
            )
        )

        # Salva resposta do assistente apenas se veio algo
        if full_reply.strip():
            db.add(
                ChatMessage(
                    session_id=session.id,
                    role="assistant",
                    content=full_reply,
                    model=resolved_model,
                    created_at=now,
                )
            )

        # Gera titulo baseado na primeira mensagem do usuario (fallback local)
        if is_first_message and session.title == "New chat":
            title_text = payload.message.strip()
            if len(title_text) > 60:
                title_text = title_text[:57] + "..."
            session.title = title_text

        session.updated_at = now
        db.commit()

        yield f"data: {json.dumps({'done': True}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
