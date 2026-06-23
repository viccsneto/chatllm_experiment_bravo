from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, ChatSession
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.openrouter import OpenRouterConfigError, generate_reply, generate_title, stream_reply
from backend.routers.auth import get_current_user
from backend.models import User


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


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

    # Resolve session_id: usa a fornecida ou cria uma nova
    sid = payload.session_id
    if sid is None:
        session = ChatSession(user_id=current_user.id, title="Nova conversa")
        db.add(session)
        db.commit()
        db.refresh(session)
        sid = session.id
    else:
        session = db.query(ChatSession).filter(
            ChatSession.id == sid,
            ChatSession.user_id == current_user.id,
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Sessao nao encontrada.")

    db.add(ChatMessage(session_id=sid, role="user", content=payload.message, model=resolved_model))
    db.add(ChatMessage(session_id=sid, role="assistant", content=reply, model=resolved_model))
    db.commit()

    return ChatResponse(reply=reply, model=resolved_model, session_id=sid)


@router.post("/api/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    resolved_model = payload.model or OPENROUTER_MODEL_DEFAULT

    async def event_generator():
        full_reply = ""

        # Resolve session_id: usa a fornecida ou cria uma nova
        sid = payload.session_id
        if sid is None:
            session = ChatSession(user_id=current_user.id, title="Nova conversa")
            db.add(session)
            db.commit()
            db.refresh(session)
            sid = session.id
        else:
            session = db.query(ChatSession).filter(
                ChatSession.id == sid,
                ChatSession.user_id == current_user.id,
            ).first()
            if not session:
                yield f"data: {json.dumps({'error': 'Sessao nao encontrada.'})}\n\n"
                return

        try:
            async for delta in stream_reply(
                user_message=payload.message,
                history=[item.model_dump() for item in payload.history],
                model=payload.model,
            ):
                full_reply += delta
                yield f"data: {json.dumps({'delta': delta, 'session_id': sid}, ensure_ascii=True)}\n\n"
        except OpenRouterConfigError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=True)}\n\n"
            return
        except RuntimeError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=True)}\n\n"
            return

        if full_reply.strip():
            db.add(
                ChatMessage(
                    session_id=sid,
                    role="user",
                    content=payload.message,
                    model=resolved_model,
                )
            )
            db.add(
                ChatMessage(
                    session_id=sid,
                    role="assistant",
                    content=full_reply,
                    model=resolved_model,
                )
            )
            # Titulo automatico na primeira resposta
            if session.title == "Nova conversa":
                title = await generate_title(
                    user_message=payload.message,
                    assistant_reply=full_reply,
                    model=resolved_model,
                )
                session.title = title
            session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()

        yield f"data: {json.dumps({'done': True, 'session_id': sid}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
