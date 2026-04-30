from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.chunking import split_text
from app.config import settings
from app.embeddings import TongyiEmbedder
from app.milvus_store import MilvusChunkStore
from app.pdf_loader import extract_pdf_text, save_upload_file
from app.schemas import SearchRequest, SearchResponse, UploadResponse


app = FastAPI(title="my_first_rag", version="0.1.0")

_embedder: TongyiEmbedder | None = None
_store: MilvusChunkStore | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/upload", response_model=UploadResponse)
def upload_pdf(file: UploadFile = File(...)) -> UploadResponse:
    doc_id = str(uuid4())
    #这行把用户上传的 PDF 保存到本地目录
    pdf_path = save_upload_file(settings.upload_dir, file)

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
    except:
        pdf_path.unlink(missing_ok=True)
    finally:
        file.file.close()

    return UploadResponse(
        doc_id=doc_id,
        chunk_count=chunk_count,
        filename=file.filename or pdf_path.name,
    )


@app.post("/api/search", response_model=SearchResponse)
def search_chunks(request: SearchRequest) -> SearchResponse:
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query must not be empty")

    query_vector = get_embedder().embed_query(query)
    _validate_vectors([query_vector])
    chunks = get_store().search(query_vector, request.top_k)

    return SearchResponse(chunks=chunks)

#TODO：为什么这里要用单例设计模式懒加载？
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

#TODO: 同理，为什么这种建立数据库连接的操作为什么不专门做个类去存放而是塞进main里？这里是不是可以考虑多线程做个连接池？
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

#TODO:为什么这_validate_vectors也要抽一个方法出来，如果这段代码使用频繁为什么不抽一个公共方法，这种情况一般传入多少维度的向量数据不都应该提前规划好么，什么场景会传入维度不匹配的字段
def _validate_vectors(vectors: list[list[float]]) -> None:
    for vector in vectors:
        #确认 DashScope 实际返回的向量维度和 Milvus 建表时声明的维度一致
        if len(vector) != settings.embedding_dim:
            raise HTTPException(
                status_code=502,
                detail=f"Embedding dim mismatch: expected {settings.embedding_dim}, got {len(vector)}",
            )
