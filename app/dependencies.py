from fastapi import HTTPException

from app.config import settings
from app.embeddings import TongyiEmbedder
from app.llm_reranker import LLMReranker
from app.milvus_store import MilvusChunkStore
from app.reranker import BGEReranker


_embedder: TongyiEmbedder | None = None
_store: MilvusChunkStore | None = None
_reranker: BGEReranker | LLMReranker | None = None


def get_embedder() -> TongyiEmbedder:
    global _embedder
    #单例设计模式懒加载
    if _embedder is None:
        _embedder = TongyiEmbedder(
            api_key=settings.dashscope_api_key,
            #DashScope text-embedding-v2 API 单次调用最多支持 **25 条**文本
            batch_size=settings.embedding_batch_size,
        )

    return _embedder


def get_store() -> MilvusChunkStore:
    global _store

    if _store is None:
        _store = MilvusChunkStore(
            host=settings.milvus_host,
            port=settings.milvus_port,
            collection_name=settings.milvus_collection,
            embedding_dim=settings.embedding_dim,
        )

    return _store


def get_reranker() -> BGEReranker | LLMReranker:
    global _reranker
    if _reranker is None:
        if settings.reranker_backend == "bge":
            _reranker = BGEReranker(
                model_name=settings.reranker_model,
                use_fp16=settings.reranker_use_fp16,
            )
        else:
            # 默认 llm 兜底，不依赖本地模型权重
            _reranker = LLMReranker(
                api_key=settings.dashscope_api_key,
                model=settings.llm_reranker_model,
                doc_max_chars=settings.llm_reranker_doc_max_chars,
            )
    return _reranker


def validate_vectors(vectors: list[list[float]]) -> None:
    for vector in vectors:
        #确认 DashScope 实际返回的向量维度和 Milvus 建表时声明的维度一致
        if len(vector) != settings.embedding_dim:
            raise HTTPException(
                status_code=502,
                detail=f"Embedding dim mismatch: expected {settings.embedding_dim}, got {len(vector)}",
            )
