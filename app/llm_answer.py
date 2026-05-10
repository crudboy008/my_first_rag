"""LLM 答案生成：基于检索到的 chunks 和用户 query，调通义生成中文答案。

设计取舍：
- SYSTEM prompt 从 app/prompts/answer_prompt_v1.txt 读，模块加载时一次。
  路径用 Path(__file__).parent / "prompts" / "answer_prompt_v1.txt"，
  不依赖启动 cwd，更稳。
- USER_TEMPLATE 顶部硬编码，禁止由调用方拼接，保证 prompt 形态稳定。
- DashScope SDK 用模块级全局 dashscope.api_key 赋值，与 llm_reranker
  共用同一全局，不重复 instance 化客户端。
- chunks 用 dict 访问（c["text"]），与 milvus_store.search 返回类型对齐。
- 非 200 抛 HTTPException(502)，让 router 向前端透传。
- LLM 输出空字符串 → 返回硬编码 NO_ANSWER_TEXT，由 router 决定是否清空 citations。
"""

from __future__ import annotations

from pathlib import Path

import dashscope
from dashscope import Generation
from fastapi import HTTPException

from app.config import settings


_PROMPT_PATH = Path(__file__).parent / "prompts" / "answer_prompt_v1.txt"
SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

USER_TEMPLATE = "[Context]\n{context}\n\n[Question]\n{query}\n\n[Answer]\n"

NO_ANSWER_TEXT = "未在已知文档中找到相关内容"

# 模块级全局赋值 api_key，与 llm_reranker.py 共用同一全局
dashscope.api_key = settings.dashscope_api_key


def generate_answer(query: str, chunks: list[dict]) -> str:
    """基于 chunks 上下文，让 LLM 生成 query 的答案。

    chunks 为空或 LLM 返回空 → 返回 NO_ANSWER_TEXT，由调用方决定是否清空 citations。
    """
    context = "\n".join(f"[{i + 1}] {c['text']}" for i, c in enumerate(chunks))
    user_content = USER_TEMPLATE.format(context=context, query=query)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    try:
        response = Generation.call(
            model=settings.answer_model,
            messages=messages,
            result_format="message",
            max_tokens=settings.answer_max_tokens,
            temperature=settings.answer_temperature,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"LLM 调用失败: {exc}") from exc

    """
    try/except 和 if status_code != 200                        
    处理的是两类完全不同的失败 —— 这是 SDK                     
    调用的标准双层守卫模式
    """
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"LLM 调用失败: status={response.status_code} message={response.message}",
        )
    #打印响应全部参数，自测用
    print(f"=== response repr ===\n{repr(response)}")
    #踩坑记录，调用是通过sdk调用所以查看qwen-turbo的返回结果还不行还要看DashScope这个sdk的响应结果
    answer = (response.output.choices[0].message.content or "").strip()
    if not answer:
        return NO_ANSWER_TEXT
    return answer
