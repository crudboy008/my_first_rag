from typing import Any

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    doc_id: str
    chunk_count: int
    filename: str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    # True 时走 Milvus top-20 → reranker 精排 → top_k
    # False 时直接返回 Milvus top_k（baseline 对比用）
    use_reranker: bool = Field(default=False)


class SearchChunk(BaseModel):
    id: str
    text: str
    # 向量余弦相似度（Milvus 返回）
    score: float
    # reranker 打分，仅 use_reranker=True 时有值
    rerank_score: float | None = None
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    chunks: list[SearchChunk]
