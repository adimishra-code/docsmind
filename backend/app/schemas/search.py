from __future__ import annotations

from pydantic import BaseModel


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int | None = None
    score: float
    excerpt: str


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[SearchResultItem]
