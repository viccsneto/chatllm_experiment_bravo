from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None
    created_at: datetime
    updated_at: datetime


class ChatSessionList(BaseModel):
    sessions: list[ChatSessionOut]


class ChatSessionCreate(BaseModel):
    pass