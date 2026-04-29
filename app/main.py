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
        text = extract_pdf_text(pdf_path)
        chunks = split_text(text, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            raise HTTPException(status_code=400, detail="No chunks generated")

        vectors = get_embedder().embed_texts(chunks)
        _validate_vectors(vectors)
        chunk_count = get_store().insert_chunks(
            doc_id=doc_id,
            source_filename=file.filename or pdf_path.name,
            chunks=chunks,
            vectors=vectors,
        )
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


def get_embedder() -> TongyiEmbedder:
    global _embedder

    if _embedder is None:
        _embedder = TongyiEmbedder(
            api_key=settings.dashscope_api_key,
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


def _validate_vectors(vectors: list[list[float]]) -> None:
    for vector in vectors:
        if len(vector) != settings.embedding_dim:
            raise HTTPException(
                status_code=502,
                detail=f"Embedding dim mismatch: expected {settings.embedding_dim}, got {len(vector)}",
            )
