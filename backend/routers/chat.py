from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession, User
from backend.schemas.chat import ChatRequest, ChatResponse, ChatMessageIn
from backend.services.auth import get_current_user
from backend.services.openrouter import OpenRouterConfigError, generate_reply, stream_reply
from backend.services.title import generate_session_title


router = APIRouter()


def _resolve_session(
    *,
    session_id: int | None,
    current_user: User,
    db: Session,
    user_message: str,
) -> ChatSession:
    """Resolve a sessao: usa a existente ou cria uma nova. Gera titulo se necessario."""
    if session_id:
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


async def _maybe_generate_title(session: ChatSession, user_message: str, db: Session) -> None:
    """Gera titulo automatico se a sessao ainda estiver com o titulo padrao."""
    if session.title == "Nova conversa":
        title = await generate_session_title(user_message)
        session.title = title[:255]
        db.commit()


@router.get("/api/sessions/{session_id}/messages")
def get_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
        .order_by(ChatMessage.created_at)
        .all()
    )
    return [
        {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
        for m in messages
    ]


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    session = _resolve_session(
        session_id=payload.session_id,
        current_user=current_user,
        db=db,
        user_message=payload.message,
    )

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

    db.add(
        ChatMessage(
            session_id=session.id,
            role="user",
            content=payload.message,
            model=resolved_model,
        )
    )
    db.add(
        ChatMessage(
            session_id=session.id,
            role="assistant",
            content=reply,
            model=resolved_model,
        )
    )
    session.updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).replace(tzinfo=None)
    db.commit()

    await _maybe_generate_title(session, payload.message, db)

    return ChatResponse(reply=reply, model=resolved_model, session_id=session.id)


@router.post("/api/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    session = _resolve_session(
        session_id=payload.session_id,
        current_user=current_user,
        db=db,
        user_message=payload.message,
    )
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT
    session_id_value = session.id
    is_new_session = session.title == "Nova conversa"

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
                ChatMessage(
                    session_id=session_id_value,
                    role="user",
                    content=payload.message,
                    model=resolved_model,
                )
            )
            db.add(
                ChatMessage(
                    session_id=session_id_value,
                    role="assistant",
                    content=full_reply,
                    model=resolved_model,
                )
            )
            db.query(ChatSession).filter(ChatSession.id == session_id_value).update(
                {"updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).replace(tzinfo=None)}
            )
            db.commit()

            # Generate title for new sessions
            if is_new_session:
                title = await generate_session_title(payload.message)
                db.query(ChatSession).filter(ChatSession.id == session_id_value).update(
                    {"title": title[:255]}
                )
                db.commit()

        yield f"data: {json.dumps({'done': True, 'session_id': session_id_value}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# Deprecated health endpoint kept for backward compat
@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
