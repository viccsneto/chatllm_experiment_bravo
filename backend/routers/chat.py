from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession
from backend.routers.auth import _get_current_user
from backend.models import User
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.openrouter import OpenRouterConfigError, generate_reply, stream_reply


router = APIRouter()


def _auto_title(text: str) -> str:
    """Generate an automatic title from the first user message."""
    clean = text.strip().replace("\n", " ")
    if len(clean) <= 60:
        return clean
    return clean[:57] + "..."


def _resolve_session(
    db: Session,
    user_id: int | None,
    session_id: int | None,
) -> tuple[ChatSession | None, bool]:
    """Resolve session; create new one if needed. Returns (session, is_new)."""
    if session_id:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            return session, False

    if user_id is None:
        return None, False

    session = ChatSession(user_id=user_id, title=None)
    db.add(session)
    db.flush()
    return session, True


def _set_title_if_needed(db: Session, session: ChatSession, message: str) -> None:
    """Set automatic title from first user message if session has no title yet."""
    if session.title is None:
        session.title = _auto_title(message)
        db.flush()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
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

    # Resolve user and session
    user: User | None = None
    try:
        user = _get_current_user(request, db)
    except HTTPException:
        pass

    session, is_new = _resolve_session(db, user.id if user else None, payload.session_id)

    if session and session.title is None:
        _set_title_if_needed(db, session, payload.message)

    sid = session.id if session else None
    db.add(ChatMessage(session_id=sid, session_key="default", role="user", content=payload.message, model=resolved_model))
    db.add(ChatMessage(session_id=sid, session_key="default", role="assistant", content=reply, model=resolved_model))

    if session:
        session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    db.commit()

    return ChatResponse(reply=reply, model=resolved_model)


@router.post("/api/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT

    # Resolve user and session
    user: User | None = None
    try:
        user = _get_current_user(request, db)
    except HTTPException:
        pass

    session, is_new = _resolve_session(db, user.id if user else None, payload.session_id)

    async def event_generator():
        nonlocal session
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
            sid = session.id if session else None

            # Auto-title on first user message
            if session and session.title is None:
                _set_title_if_needed(db, session, payload.message)

            db.add(
                ChatMessage(
                    session_id=sid,
                    session_key="default",
                    role="user",
                    content=payload.message,
                    model=resolved_model,
                )
            )
            db.add(
                ChatMessage(
                    session_id=sid,
                    session_key="default",
                    role="assistant",
                    content=full_reply,
                    model=resolved_model,
                )
            )

            # Update session timestamp
            if session:
                session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

            db.commit()

            # Re-fetch to get fresh title
            if session:
                db.refresh(session)

        yield f"data: {json.dumps({'done': True, 'session_id': session.id if session else None, 'title': session.title if session else None}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
