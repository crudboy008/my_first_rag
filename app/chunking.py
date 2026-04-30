from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        #separators：让切块器优先在"\n\n"这种条款边界切
        separators=["\n\n", "\n", "。", "，", " ", ""],
    )
    #防止纯空白页被切进数据库
    return [chunk for chunk in splitter.split_text(text) if chunk.strip()]
