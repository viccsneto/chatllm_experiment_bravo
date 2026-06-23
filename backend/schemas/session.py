from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    title: str = Field(default="Nova Conversa", max_length=255)


class SessionUpdateTitle(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class SessionOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionList(BaseModel):
    sessions: list[SessionOut]


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    model: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionMessages(BaseModel):
    messages: list[MessageOut]