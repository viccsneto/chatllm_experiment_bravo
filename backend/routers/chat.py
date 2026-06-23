from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.config import OPENROUTER_MODEL_DEFAULT
from backend.database import get_db
from backend.models import ChatMessage, Session, User
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.openrouter import OpenRouterConfigError, generate_reply, stream_reply


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def _resolve_session(payload: ChatRequest, db: Session, current_user: User) -> Session:
    """Retorna a sessao existente ou cria uma nova."""
    if payload.session_id:
        session = (
            db.query(Session)
            .filter(Session.id == payload.session_id, Session.user_id == current_user.id)
            .first()
        )
        if not session:
            raise HTTPException(status_code=404, detail="Sessao nao encontrada.")
    else:
        session = Session(user_id=current_user.id)
        db.add(session)
        db.commit()
        db.refresh(session)
    return session


async def _generate_title(user_message: str) -> str | None:
    """Gera um titulo curto para a sessao baseado na mensagem do usuario."""
    try:
        title, _ = await generate_reply(
            user_message=user_message,
            history=[],
            model=None,
            system_override="You are a title generator. Generate a very short title (maximum 6 words) in Portuguese that summarizes the user's message below. Return ONLY the title, no quotes, no punctuation, no explanation.",
        )
        title = title.strip().strip('"').strip("'").strip(".").strip()
        if len(title) > 255:
            title = title[:252] + "..."
        return title or None
    except RuntimeError:
        return None


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    session = _resolve_session(payload, db, current_user)

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
            user_id=current_user.id,
            role="user",
            content=payload.message,
            model=resolved_model,
        )
    )
    db.add(
        ChatMessage(
            session_id=session.id,
            user_id=current_user.id,
            role="assistant",
            content=reply,
            model=resolved_model,
        )
    )

    # Titulo automatico na primeira resposta
    if session.title is None:
        session.title = await _generate_title(payload.message)
        db.add(session)

    db.commit()

    return ChatResponse(reply=reply, model=resolved_model)


@router.post("/api/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    session = _resolve_session(payload, db, current_user)
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
                yield f"data: {json.dumps({'delta': delta, 'session_id': session.id}, ensure_ascii=True)}\n\n"
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
                    user_id=current_user.id,
                    role="user",
                    content=payload.message,
                    model=resolved_model,
                )
            )
            db.add(
                ChatMessage(
                    session_id=session.id,
                    user_id=current_user.id,
                    role="assistant",
                    content=full_reply,
                    model=resolved_model,
                )
            )

            # Titulo automatico na primeira resposta
            title_updated = None
            if session.title is None:
                gen_title = await _generate_title(payload.message)
                if gen_title:
                    session.title = gen_title
                    db.add(session)
                    title_updated = gen_title

            db.commit()

            if title_updated:
                yield f"data: {json.dumps({'title': title_updated, 'session_id': session.id}, ensure_ascii=True)}\n\n"

        yield f"data: {json.dumps({'done': True, 'session_id': session.id}, ensure_ascii=True)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
