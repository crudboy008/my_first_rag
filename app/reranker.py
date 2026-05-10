from __future__ import annotations

from FlagEmbedding import FlagReranker


class BGEReranker:
    """封装 BAAI/bge-reranker-base，对 Milvus 粗召回结果做精排。

    为什么需要 reranker：
    - Milvus 用向量余弦相似度召回，衡量的是"语义方向接近"，
      但不擅长判断"这段文字到底有没有回答这个问题"。
    - Cross-encoder reranker 把 (query, doc) 拼在一起过一个完整的
      attention，能捕捉细粒度的词级匹配，精排质量更高。
    - 代价是 reranker 不能做 ANN，只能对少量候选逐一打分，
      所以典型用法是：Milvus top-20 粗召 → reranker 精排 → 返回 top-5。
    """
    def __init__(self, model_name: str, use_fp16: bool = False) -> None:
        # model_name 传本地路径时直接加载，传 HF model ID 时才会联网下载到 ~/.cache/huggingface/hub/
        self._model = FlagReranker(model_name, use_fp16=use_fp16)

    def rerank(
        self,
        query: str,
        chunks: list[dict],
        top_k: int,
    ) -> list[dict]:
        """对 chunks 按与 query 的相关性重排，返回 top_k 条。

        每条 chunk 会增加 rerank_score 字段（float），
        调用方可用该字段和原始向量 score 做对比分析。
        """
        if not chunks:
            return []

        texts = [c["text"] for c in chunks]
        pairs = [[query, text] for text in texts]

        # compute_score 返回 List[float]，顺序与 pairs 一一对应
        scores: list[float] = self._model.compute_score(pairs)

        # 把 rerank_score 写回每个 chunk dict（不影响原始 score 字段）
        #`**` 在 dict 字面量里是**解包操作符**：把 `chunk` 这个 dict 的所有 key-value **复制进新 dict**，然后再加上 `"rerank_score": float(score)` 这一对
        scored_chunks = [
            {**chunk, "rerank_score": float(score)}
            for chunk, score in zip(chunks, scores)
        ]
        #以rerank_score排序
        #`reverse=False`（默认）：**升序**（从小到大）
        ranked = sorted(scored_chunks, key=lambda x: x["rerank_score"], reverse=True)
        return ranked[:top_k]
