"""LLM 兜底重排器：用通义 API 给每个 query-doc 对打 0-10 分，按分数精排。

设计取舍：
- 串行调用（非 batch），每次 1 个 doc，实现简单，失败隔离彻底。
  代价是 20 个候选 ≈ 20 次 API，生产环境耗时 10-30 秒，
  简历叙述时定位为"功能验证版"，不宜吹成高性能方案。
- temperature=0 保证同一 query-doc 对每次得分稳定，Eval 数据可复现。
- 每个 doc 独立 try-except，单次 API 失败 fallback score=0，
  不会因 1 次超时让整个 rerank 流程崩溃。
"""

from __future__ import annotations

import re

import dashscope
from dashscope import Generation


# 检查点 1：prompt 强约束输出格式
_SCORE_PROMPT_TEMPLATE = """\
你是相关性评分员。判断以下 doc 是否能回答 query。

query: {query}
doc: {doc}

只输出一个 0-10 的整数，10=完全相关，0=完全无关。不要输出任何其他字符。"""


def _parse_score(text: str) -> float:
    """从 LLM 输出中提取整数分数。

    检查点 1 的兜底解析：LLM 偶尔会输出 "8分" "得分8" 等格式，
    用正则提取第一个数字，提取失败返回 0。
    """
    match = re.search(r"\d+", text or "")
    if match is None:
        return 0.0
    return min(float(match.group()), 10.0)


class LLMReranker:
    """用通义大模型对 Milvus 粗召回结果做精排。"""

    def __init__(
        self,
        api_key: str | None,
        model: str = "qwen-turbo",
        doc_max_chars: int = 500,
    ) -> None:
        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY is not set, LLMReranker cannot initialize")
        dashscope.api_key = api_key
        self.model = model
        # 检查点 3：doc 截断上限，超长 chunk 会让 LLM 注意力分散、打分不准
        self.doc_max_chars = doc_max_chars

    def rerank(
        self,
        query: str,
        chunks: list[dict],
        top_k: int,
    ) -> list[dict]:
        """对 chunks 逐一用 LLM 打分，返回 top_k 条（含 rerank_score 字段）。"""
        if not chunks:
            return []

        scored_chunks: list[dict] = []
        for chunk in chunks:
            score = self._score_one(query, chunk["text"])
            scored_chunks.append({**chunk, "rerank_score": score})

        ranked = sorted(scored_chunks, key=lambda x: x["rerank_score"], reverse=True)
        return ranked[:top_k]

    def _score_one(self, query: str, doc_text: str) -> float:
        """对单个 doc 调用 LLM 打分，失败时 fallback 到 0。

        检查点 2：try-except 包裹单次调用，任何异常（超时/限流/解析失败）
        都不向上抛出，而是 fallback score=0，让该 doc 排到末尾。
        """
        try:
            # 检查点 3：截断 doc，防止 prompt 过长
            doc_snippet = doc_text[: self.doc_max_chars]

            prompt = _SCORE_PROMPT_TEMPLATE.format(query=query, doc=doc_snippet)

            # 检查点 5：temperature=0，保证打分可复现
            response = Generation.call(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                result_format="message",
                temperature=0,
                top_p=0.01,   # 配合 temperature=0，进一步压低随机性
                max_tokens=8,  # 只需输出 1 个数字，严格限制输出长度
            )

            if response.status_code != 200:
                return 0.0

            raw_text: str = response.output.choices[0].message.content
            return _parse_score(raw_text)

        except Exception:  # noqa: BLE001
            # 检查点 2：任何异常都 fallback，不    崩整个 rerank
            return 0.0
