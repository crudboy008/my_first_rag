from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.chunking import split_text
from app.config import settings
from app.embeddings import TongyiEmbedder
from app.milvus_store import MilvusChunkStore
from app.pdf_loader import extract_pdf_text, save_upload_file
from app.llm_reranker import LLMReranker
from app.reranker import BGEReranker
from app.schemas import SearchRequest, SearchResponse, UploadResponse


app = FastAPI(title="my_first_rag", version="0.1.0")

_embedder: TongyiEmbedder | None = None
_store: MilvusChunkStore | None = None
_reranker: BGEReranker | LLMReranker | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/upload", response_model=UploadResponse)
def upload_pdf(file: UploadFile = File(...)) -> UploadResponse:
    doc_id = str(uuid4())
    #这行把用户上传的 PDF 保存到本地目录，文件名前缀用 doc_id 保持一致
    pdf_path = save_upload_file(settings.upload_dir, file, doc_id)

    try:
        #pdf提取文本
        #文本太大一次性处理很难
        text = extract_pdf_text(pdf_path)
        chunks = split_text(text, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            raise HTTPException(status_code=400, detail="No chunks generated")
        #向量化
        vectors = get_embedder().embed_texts(chunks)
        #验证向量维度
        _validate_vectors(vectors)
        #插入向量并返回影响条数
        chunk_count = get_store().insert_chunks(
            doc_id=doc_id,
            #有文件名正常存，没文件名用pdf路径名
            source_filename=file.filename or pdf_path.name,
            chunks=chunks,
            vectors=vectors,
        )
        return UploadResponse(
            doc_id=doc_id,
            chunk_count=chunk_count,
            filename=file.filename or pdf_path.name,
        )
    except HTTPException:
        # 已经是规范的 HTTP 异常,直接清理副作用并重抛
        #TODO: 为什么这里要写两次pdf_path.unlink(missing_ok=True)判断
        pdf_path.unlink(missing_ok=True)
        raise
    except Exception as e:
        # 其他未预料异常,清理副作用 + 包装成 500 抛出
        pdf_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"upload failed: {type(e).__name__}: {e}",
        ) from e
    finally:
        # 无论成败都关闭上传文件描述符
        file.file.close()




@app.post("/api/search", response_model=SearchResponse)
def search_chunks(request: SearchRequest) -> SearchResponse:
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query must not be empty")

    query_vector = get_embedder().embed_query(query)
    _validate_vectors([query_vector])

    if request.use_reranker:
        # 两阶段召回：Milvus 粗召 candidate_k 条 → reranker 精排 → 返回 top_k
        #TODO:settings.reranker_candidate_k为什么要设置为20，为什么这里要作对比取最大值？
        candidate_k = max(request.top_k, settings.reranker_candidate_k)
        candidates = get_store().sea1.rch(query_vector, candidate_k)
        chunks = get_reranker().rerank(query, candidates, request.top_k)
    else:
        # baseline：直接返回 Milvus 向量相似度 top_k
        chunks = get_store().search(query_vector, request.top_k)

    return SearchResponse(chunks=chunks)

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

def _validate_vectors(vectors: list[list[float]]) -> None:
    for vector in vectors:
        #确认 DashScope 实际返回的向量维度和 Milvus 建表时声明的维度一致
        if len(vector) != settings.embedding_dim:
            raise HTTPException(
                status_code=502,
                detail=f"Embedding dim mismatch: expected {settings.embedding_dim}, got {len(vector)}",
            )
