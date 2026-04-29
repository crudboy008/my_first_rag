import shutil
from pathlib import Path
from uuid import uuid4

import pdfplumber
from fastapi import HTTPException, UploadFile


def _safe_filename(filename: str) -> str:
    return Path(filename).name or "uploaded.pdf"


def save_upload_file(upload_dir: Path, file: UploadFile) -> Path:
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    filename = _safe_filename(file.filename or "uploaded.pdf")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    upload_dir.mkdir(parents=True, exist_ok=True)
    target_path = upload_dir / f"{uuid4()}_{filename}"

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

    full_text = "\n\n".join(pages).strip()
    if not full_text:
        raise HTTPException(status_code=400, detail="No extractable text found in PDF")

    return full_text
