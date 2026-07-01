from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid
from pydantic import BaseModel


class DocumentBase(BaseModel):
    filename: str


class DocumentResponse(DocumentBase):
    id: uuid.UUID
    file_type: str
    file_size: int
    status: str
    doc_metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    progress_pct: float | None = None
    error_message: str | None = None


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int = 1
    page_size: int = 100
    total_pages: int = 1
