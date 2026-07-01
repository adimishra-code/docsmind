from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
import uuid
from pydantic import BaseModel


class MessageRole(str, Enum):
    """Chat message role types."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatSessionBase(BaseModel):
    title: str


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSessionResponse(ChatSessionBase):
    id: uuid.UUID
    user_id: uuid.UUID
    is_pinned: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    content: str
    document_ids: list[uuid.UUID] | None = None
    multi_query: bool = False
    expand_context: bool = False


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    chat_id: uuid.UUID
    role: str
    content: str
    citations: list[dict[str, Any]] | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionListResponse(BaseModel):
    items: list[ChatSessionResponse]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


class ChatSessionDetailResponse(ChatSessionResponse):
    messages: list[ChatMessageResponse] = []
