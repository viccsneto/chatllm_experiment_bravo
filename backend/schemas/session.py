from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ChatSessionOut(BaseModel):
    id: int
    title: str | None
    created_at: datetime
    updated_at: datetime


class ChatSessionList(BaseModel):
    sessions: list[ChatSessionOut]


class ChatMessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    model: str
    created_at: datetime


class SessionMessagesOut(BaseModel):
    messages: list[ChatMessageOut]