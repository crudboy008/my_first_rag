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


settings = Settings()
