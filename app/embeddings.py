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

        dashscope.api_key = api_key
        self.batch_size = batch_size

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []

        for batch in _batched(texts, self.batch_size):
            response = TextEmbedding.call(
                model=TextEmbedding.Models.text_embedding_v2,
                input=batch,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"DashScope embedding failed: {response.message}",
                )

            embeddings = response.output.get("embeddings", [])
            embeddings = sorted(embeddings, key=lambda item: item["text_index"])
            vectors.extend(item["embedding"] for item in embeddings)

        if len(vectors) != len(texts):
            raise HTTPException(
                status_code=502,
                detail="DashScope returned an unexpected embedding count",
            )

        return vectors

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


def _batched(items: list[str], batch_size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]
