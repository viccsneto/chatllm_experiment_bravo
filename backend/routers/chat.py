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

_TITLE_PROMPT = (
    "Generate a concise title (max 6 words) for a chat conversation based on the user's first message. "
    "Respond with ONLY the title, no quotes, no punctuation."
)

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def _get_or_create_session(
    db: Session, user: User, session_id: int | None
) -> ChatSession:
    """Resolve session_id: if None, create a new session for the user."""
    if session_id is not None:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user.id,
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Sessao nao encontrada")
        return session
    # Create a new session
    session = ChatSession(user_id=user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


async def _auto_title(
    db: Session, session: ChatSession, message: str
) -> None:
    """Generate a title from the user's first message if session has no title yet."""
    if session.title is not None:
        return
    try:
        title, _ = await generate_reply(
            user_message=message,
            history=[],
            model=None,
            system_prompt=_TITLE_PROMPT,
        )
        title = title.strip().strip('"\' .')
        if title:
            session.title = title[:255]
            db.commit()
    except Exception:
        pass  # Best-effort; title stays None


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    session = _get_or_create_session(db, current_user, payload.session_id)

    # Load message history for this session to send as context
    history_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in history_messages]

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

    await _auto_title(db, session, payload.message)

    return ChatResponse(reply=reply, model=resolved_model)


@router.post("/api/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    session = _get_or_create_session(db, current_user, payload.session_id)

    # Load message history for this session
    history_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in history_messages]

    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT

    async def event_generator():
        nonlocal session
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
                    content=full_reply,
                    model=resolved_model,
                )
            )
            db.commit()

        # Auto-title after first response
        await _auto_title(db, session, payload.message)

        yield f"data: {json.dumps({'done': True}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
