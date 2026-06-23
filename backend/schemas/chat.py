from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: int
    model: str | None = None
    history: list[ChatMessageIn] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    model: str


class ChatSessionOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChatSessionList(BaseModel):
    sessions: list[ChatSessionOut]


class ChatSessionCreate(BaseModel):
    pass


class ChatSessionMessages(BaseModel):
    session_id: int
    messages: list[ChatMessageIn] | list[dict]


class ChatTitleUpdate(BaseModel):
    title: str
