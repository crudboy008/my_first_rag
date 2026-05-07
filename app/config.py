import os
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    dashscope_api_key: str | None = os.getenv("DASHSCOPE_API_KEY")
    milvus_host: str = os.getenv("MILVUS_HOST", "localhost")
    milvus_port: str = os.getenv("MILVUS_PORT", "19530")
    milvus_collection: str = os.getenv("MILVUS_COLLECTION", "rag_demo_v1")
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    embedding_dim: int = int(os.getenv("EMBEDDING_DIM", "1536"))
    embedding_batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))
    # 上传 PDF 大小上限（字节），默认 50MB
    max_pdf_size: int = int(os.getenv("MAX_PDF_SIZE", "52428800"))
    # reranker 后端选择："llm" 用通义打分（稳定兜底）；"bge" 用本地模型（需先下载权重）
    reranker_backend: str = os.getenv("RERANKER_BACKEND", "llm")
    # Milvus 初召回候选数量，给 reranker 留足候选池
    reranker_candidate_k: int = int(os.getenv("RERANKER_CANDIDATE_K", "20"))
    # BGE 本地模型配置（backend=bge 时生效）
    reranker_model: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-base")
    #TODO: RERANKER_USE_FP16这个值有什么作用？为什么要传入？
    reranker_use_fp16: bool = os.getenv("RERANKER_USE_FP16", "false").lower() == "true"
    # LLM reranker 配置（backend=llm 时生效）
    llm_reranker_model: str = os.getenv("LLM_RERANKER_MODEL", "qwen-turbo")
    # 每个 doc 送入 prompt 前截断的字符数，避免 prompt 过长、注意力分散
    llm_reranker_doc_max_chars: int = int(os.getenv("LLM_RERANKER_DOC_MAX_CHARS", "500"))
    # LLM 答案生成（/api/ask）配置
    answer_model: str = os.getenv("ANSWER_MODEL", "qwen-turbo")
    answer_max_tokens: int = int(os.getenv("ANSWER_MAX_TOKENS", "500"))
    answer_temperature: float = float(os.getenv("ANSWER_TEMPERATURE", "0.1"))


settings = Settings()
