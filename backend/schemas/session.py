from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    pass


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: str | None = None
    updated_at: str | None = None
    message_count: int = 0

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]


class SessionMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    model: str
    created_at: str | None = None

    model_config = {"from_attributes": True}


class SessionDetailResponse(BaseModel):
    id: str
    title: str
    created_at: str | None = None
    updated_at: str | None = None
    messages: list[SessionMessageResponse] = []

    model_config = {"from_attributes": True}