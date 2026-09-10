from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession, User
from backend.routers.auth import get_current_user
from backend.routers.sessions import get_owned_session
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.openrouter import OpenRouterConfigError, generate_reply, stream_reply
from backend.services.titles import derive_session_title


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _stored_history(db: Session, session: ChatSession) -> list[dict[str, str]]:
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    return [{"role": message.role, "content": message.content} for message in messages]


def _persist_exchange(
    db: Session,
    session: ChatSession,
    *,
    user_message: str,
    assistant_reply: str,
    model: str,
) -> None:
    if session.id is None:
        db.add(session)
        db.flush()

    session_key = str(session.id)
    db.add(
        ChatMessage(
            session_id=session.id,
            session_key=session_key,
            role="user",
            content=user_message,
            model=model,
        )
    )
    db.add(
        ChatMessage(
            session_id=session.id,
            session_key=session_key,
            role="assistant",
            content=assistant_reply,
            model=model,
        )
    )
    if not session.title:
        session.title = derive_session_title(user_message, assistant_reply)
    session.updated_at = _utc_now()
    db.commit()


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatResponse:
    session = (
        get_owned_session(db, user, payload.session_id)
        if payload.session_id is not None
        else None
    )
    history = _stored_history(db, session) if session is not None else []
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
    if session is None:
        session = ChatSession(user_id=user.id)
    _persist_exchange(
        db,
        session,
        user_message=payload.message,
        assistant_reply=reply,
        model=resolved_model,
    )

    return ChatResponse(
        reply=reply,
        model=resolved_model,
        session_id=session.id,
        title=session.title,
    )


@router.post("/api/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT
    session = (
        get_owned_session(db, user, payload.session_id)
        if payload.session_id is not None
        else None
    )
    history = _stored_history(db, session) if session is not None else []
    session_id = session.id if session is not None else None
    user_id = user.id
    database_bind = db.get_bind()

    async def event_generator():
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

        if not full_reply.strip():
            yield f"data: {json.dumps({'error': 'O modelo nao retornou conteudo.'})}\n\n"
            return

        with Session(bind=database_bind) as stream_db:
            if session_id is None:
                persistent_session = ChatSession(user_id=user_id)
            else:
                persistent_session = (
                    stream_db.query(ChatSession)
                    .filter(
                        ChatSession.id == session_id,
                        ChatSession.user_id == user_id,
                    )
                    .first()
                )
                if persistent_session is None:
                    yield f"data: {json.dumps({'error': 'Conversa nao encontrada.'})}\n\n"
                    return

            _persist_exchange(
                stream_db,
                persistent_session,
                user_message=payload.message,
                assistant_reply=full_reply,
                model=resolved_model,
            )
            persisted_session_id = persistent_session.id
            session_title = persistent_session.title

        done_event = {
            "done": True,
            "session_id": persisted_session_id,
            "title": session_title,
        }
        yield f"data: {json.dumps(done_event, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
