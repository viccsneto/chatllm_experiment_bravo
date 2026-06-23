from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession, User
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.auth import get_current_user
from backend.services.openrouter import OpenRouterConfigError, generate_reply, generate_title, stream_reply


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/sessions/{session_id}/messages")
def get_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
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
        {"id": msg.id, "role": msg.role, "content": msg.content, "created_at": msg.created_at.isoformat()}
        for msg in messages
    ]


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

    db.add(ChatMessage(session_id=payload.session_id, session_key="sessions", role="user", content=payload.message, model=resolved_model))
    db.add(ChatMessage(session_id=payload.session_id, session_key="sessions", role="assistant", content=reply, model=resolved_model))

    # Auto-title: if session has no title, generate one from context
    if payload.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()
        if session and not session.title:
            try:
                title = await generate_title(payload.message, reply)
                session.title = title
            except Exception:
                pass  # Silently fail if title generation fails

    db.commit()

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
            db.add(
                ChatMessage(
                    session_id=payload.session_id,
                    session_key="sessions",
                    role="user",
                    content=payload.message,
                    model=resolved_model,
                )
            )
            db.add(
                ChatMessage(
                    session_id=payload.session_id,
                    session_key="sessions",
                    role="assistant",
                    content=full_reply,
                    model=resolved_model,
                )
            )

            # Auto-title: if session has no title, generate one from context
            if payload.session_id:
                session = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()
                if session and not session.title:
                    try:
                        title = await generate_title(payload.message, full_reply)
                        session.title = title
                    except Exception:
                        pass

            db.commit()

            # Notify frontend if title was generated
            if payload.session_id:
                session = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()
                if session and session.title:
                    yield f"data: {json.dumps({'title': session.title}, ensure_ascii=True)}\n\n"

        yield f"data: {json.dumps({'done': True}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
