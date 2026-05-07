"""POST /api/ask：检索 + LLM 答案生成。

流程仿 routers/search.py：
- query 空校验 → 400
- embed → validate → Milvus 召回（可选 reranker 精排）
- llm_answer.generate_answer 生成答案
- 命中 NO_ANSWER_TEXT 时 citations=[]
"""

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.dependencies import get_embedder, get_reranker, get_store, validate_vectors
from app.llm_answer import NO_ANSWER_TEXT, generate_answer
from app.schemas import AskRequest, AskResponse, Citation


router = APIRouter()


@router.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query must not be empty")

    query_vector = get_embedder().embed_query(query)
    validate_vectors([query_vector])

    if request.use_reranker:
        # 两阶段召回：Milvus 粗召 candidate_k 条 → reranker 精排 → top_k
        candidate_k = max(request.top_k, settings.reranker_candidate_k)
        candidates = get_store().search(query_vector, candidate_k)
        chunks = get_reranker().rerank(query, candidates, request.top_k)
    else:
        # baseline：直接返回 Milvus top_k
        chunks = get_store().search(query_vector, request.top_k)

    answer = generate_answer(query, chunks)

    if answer == NO_ANSWER_TEXT:
        return AskResponse(answer=answer, citations=[])

    citations = [
        Citation(
            chunk_id=c["id"],
            score=float(
                c["rerank_score"]
                if c.get("rerank_score") is not None
                else c["score"]
            ),
            text_snippet=c["text"][:100],
        )
        for c in chunks
    ]
    return AskResponse(answer=answer, citations=citations)
