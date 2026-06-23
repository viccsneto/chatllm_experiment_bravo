from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession
from backend.routers.auth import get_current_user
from backend.models import User as UserModel
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.openrouter import OpenRouterConfigError, generate_reply, stream_reply
from backend.services.titler import generate_title


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def _get_user_session_or_404(session_id: int, user_id: int, db: Session) -> ChatSession:
    """Busca a sessao e verifica se pertence ao usuario."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada.")
    return session


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    # Verifica a sessao
    session = _get_user_session_or_404(payload.session_id, current_user.id, db)

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

    now_ts = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(ChatMessage(
        user_id=current_user.id,
        session_id=session.id,
        session_key=str(session.id),
        role="user",
        content=payload.message,
        model=resolved_model,
        created_at=now_ts,
    ))
    db.add(ChatMessage(
        user_id=current_user.id,
        session_id=session.id,
        session_key=str(session.id),
        role="assistant",
        content=reply,
        model=resolved_model,
        created_at=now_ts,
    ))
    session.updated_at = now_ts

    # Titulo automatico se ainda nao tem
    if session.title == "Nova conversa":
        title = await generate_title(payload.message, reply)
        if title:
            session.title = title

    db.commit()

    return ChatResponse(reply=reply, model=resolved_model)


@router.post("/api/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT
    # Verifica a sessao
    session = _get_user_session_or_404(payload.session_id, current_user.id, db)

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
            now_ts = datetime.now(timezone.utc).replace(tzinfo=None)
            db.add(
                ChatMessage(
                    user_id=current_user.id,
                    session_id=session.id,
                    session_key=str(session.id),
                    role="user",
                    content=payload.message,
                    model=resolved_model,
                    created_at=now_ts,
                )
            )
            db.add(
                ChatMessage(
                    user_id=current_user.id,
                    session_id=session.id,
                    session_key=str(session.id),
                    role="assistant",
                    content=full_reply,
                    model=resolved_model,
                    created_at=now_ts,
                )
            )
            session.updated_at = now_ts

            # Titulo automatico se ainda nao tem
            if session.title == "Nova conversa":
                title = await generate_title(payload.message, full_reply)
                if title:
                    session.title = title

            db.commit()

        yield f"data: {json.dumps({'done': True, 'title': session.title}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
