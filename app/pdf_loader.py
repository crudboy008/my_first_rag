import shutil
from pathlib import Path
from uuid import uuid4

import pdfplumber
from fastapi import HTTPException, UploadFile

#确保文件有名字,防止路径遍历攻击，只取文件名
#TODO:既然要抽出来为什么不抽成公共方法
def _safe_filename(filename: str) -> str:
    return Path(filename).name or "uploaded.pdf"

#保存文件
#TODO: 同步方法掉异步方法会有什么问题？ /abs/path/E:/mytest/my_first_rag_v2/main.py:21 upload() 是同步函数，但它调用的 save_pdf_by_upload() 实际上是异步流程。在当前代码里：def upload(...):pdf_path = save_pdf_by_upload(...)而 /abs/path/E:/mytest/my_first_rag_v2/main.py:52 内部又在用 read() / seek() 这类应当 await 的接口。这样运行时要么拿到的是协程对象，要么后续把协程对象当 Path用，最终会在 get_pdf_text(pdf_path) 之类的位置炸掉。没搞懂为什么
def save_upload_file(upload_dir: Path, file: UploadFile) -> Path:
    #TODO：application/octet-stream是什么格式
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    filename = _safe_filename(file.filename or "uploaded.pdf")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    #parents=True允许创建中间不存在的父目录 exist_ok=True如果目录已经存在,不报错。
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
    #拼接页
    full_text = "\n\n".join(pages).strip()
    if not full_text:
        raise HTTPException(status_code=400, detail="No extractable text found in PDF")

    return full_text
