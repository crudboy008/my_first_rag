from fastapi import APIRouter, HTTPException

from app.config import settings
from app.dependencies import get_embedder, get_reranker, get_store, validate_vectors
from app.schemas import SearchRequest, SearchResponse


router = APIRouter()


@router.post("/api/search", response_model=SearchResponse)
def search_chunks(request: SearchRequest) -> SearchResponse:
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query must not be empty")

    query_vector = get_embedder().embed_query(query)
    validate_vectors([query_vector])

    if request.use_reranker:
        # 两阶段召回：Milvus 粗召 candidate_k 条 → reranker 精排 → 返回 top_k
        #TODO:settings.reranker_candidate_k为什么要设置为20，为什么这里要作对比取最大值？
        candidate_k = max(request.top_k, settings.reranker_candidate_k)
        candidates = get_store().search(query_vector, candidate_k)
        chunks = get_reranker().rerank(query, candidates, request.top_k)
    else:
        # baseline：直接返回 Milvus 向量相似度 top_k
        chunks = get_store().search(query_vector, request.top_k)

    return SearchResponse(chunks=chunks)
