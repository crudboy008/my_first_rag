from typing import Any

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    doc_id: str
    chunk_count: int
    filename: str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=3, ge=1, le=20)


class SearchChunk(BaseModel):
    id: str
    text: str
    score: float
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    chunks: list[SearchChunk]
