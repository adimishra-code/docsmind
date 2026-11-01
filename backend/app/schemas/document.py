from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid
from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    filename: str


class DocumentUpdate(BaseModel):
    """Fields that may be updated via PATCH /documents/{id}."""
    filename: str = Field(min_length=1, max_length=512)


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


class DocumentInsightsResponse(BaseModel):
    """Real, model-generated document insights. ``available`` is False (with empty
    fields) when the document isn't indexed yet or generation didn't succeed — the
    UI hides the section rather than showing fabricated values."""
    available: bool = False
    summary: str | None = None
    topics: list[str] = []
    entities: list[str] = []


class RelatedDocument(BaseModel):
    document_id: uuid.UUID
    filename: str
    file_type: str
    similarity: float


class RelatedDocumentsResponse(BaseModel):
    items: list[RelatedDocument] = []
