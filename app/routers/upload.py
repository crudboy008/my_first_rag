from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.chunking import split_text
from app.config import settings
from app.dependencies import get_embedder, get_store, validate_vectors
from app.pdf_loader import extract_pdf_text, save_upload_file
from app.schemas import UploadResponse


router = APIRouter()


@router.post("/api/upload", response_model=UploadResponse)
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
        validate_vectors(vectors)
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
