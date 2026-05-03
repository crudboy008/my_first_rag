import shutil
from pathlib import Path

import pdfplumber
from fastapi import HTTPException, UploadFile

#确保文件有名字,防止路径遍历攻击，只取文件名
def _safe_filename(filename: str) -> str:
    return Path(filename).name or "uploaded.pdf"

#保存文件，文件名前缀复用 doc_id，让磁盘文件和 Milvus 记录可互相反查
def save_upload_file(upload_dir: Path, file: UploadFile, doc_id: str) -> Path:
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    filename = _safe_filename(file.filename or "uploaded.pdf")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    #parents=True允许创建中间不存在的父目录 exist_ok=True如果目录已经存在,不报错。
    upload_dir.mkdir(parents=True, exist_ok=True)
    target_path = upload_dir / f"{doc_id}_{filename}"

    with target_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    return target_path

#提取pdf文本
def extract_pdf_text(pdf_path: Path) -> str:
    pages: list[str] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text)
    #拼接页
    full_text = "\n\n".join(pages).strip()
    if not full_text:
        raise HTTPException(status_code=400, detail="No extractable text found in PDF")

    return full_text
