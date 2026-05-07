import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.dependencies import get_store
from app.milvus_store import MilvusChunkStore
from app.schemas import DeleteResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.delete("/api/docs/{doc_id}", response_model=DeleteResponse)
def delete_doc(
    doc_id: str,
    store: MilvusChunkStore = Depends(get_store),
) -> DeleteResponse:
    try:
        deleted_chunks = store.delete_by_doc_id(doc_id)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"milvus delete failed: {type(e).__name__}: {e}",
        ) from e

    deleted_files: list[str] = []
    upload_dir: Path = settings.upload_dir
    if upload_dir.exists():
        for pdf_path in upload_dir.glob(f"{doc_id}_*.pdf"):
            try:
                pdf_path.unlink()
                deleted_files.append(pdf_path.name)
            except Exception as e:
                logger.warning(
                    "failed to unlink %s: %s: %s",
                    pdf_path, type(e).__name__, e,
                )

    if deleted_chunks == 0 and not deleted_files:
        raise HTTPException(status_code=404, detail="doc_id not found")

    return DeleteResponse(deleted_chunks=deleted_chunks, deleted_files=deleted_files)
