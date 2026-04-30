from collections.abc import Iterable

import dashscope
from dashscope import TextEmbedding
from fastapi import HTTPException


class TongyiEmbedder:
    def __init__(self, api_key: str | None, batch_size: int) -> None:
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="DASHSCOPE_API_KEY is not set",
            )
        #TODO: dashscope的作用
        dashscope.api_key = api_key
        self.batch_size = batch_size

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []

        for batch in _batched(texts, self.batch_size):
            #调用大模型
            response = TextEmbedding.call(
                model=TextEmbedding.Models.text_embedding_v2,
                input=batch,
            )

            if response.status_code != 200:
                raise HTTPException(
                    #502上游服务挂了
                    status_code=502,
                    detail=f"DashScope embedding failed: {response.message}",
                )

            embeddings = response.output.get("embeddings", [])
            #DashScope API 批量返回 embeddings 时，不保证返回顺序和输入顺序一致，所以要重排序
            #lambda item: item["text_index"]  经典lambda写法
            #TODO：DashScope 的返回到底有哪些内容，这个item是怎么来的，这个text_index代表什么？
            embeddings = sorted(embeddings, key=lambda item: item["text_index"])
            vectors.extend(item["embedding"] for item in embeddings)
        #切块数量和向量数量一致
        if len(vectors) != len(texts):
            raise HTTPException(
                status_code=502,
                detail="DashScope returned an unexpected embedding count",
            )

        return vectors

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]

#TODO: 为什么这个_batched要拆出来
def _batched(items: list[str], batch_size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]
