import json
import time
from pathlib import Path

import numpy as np
import requests


def load_testset(path: str) -> list[dict]:
    """读 jsonl,返回测试用例列表"""
    cases = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    if not cases:
        raise ValueError("testset is empty")
    return cases


def search_one(query: str, top_k: int = 5, base_url: str = "http://localhost:18088") -> tuple[list[str], float]:
    """
    调一次 search 接口（开启 BGE rerank），返回 (returned_ids, elapsed_ms)
    服务端行为：Milvus 粗召 candidate_k(默认20) → BGE rerank → 返回 top_k
    """
    url = f"{base_url}/api/search"
    payload = {"query": query, "top_k": top_k, "use_reranker": True}
    try:
        start = time.perf_counter()
        response = requests.post(url, json=payload, timeout=120)  # rerank CPU 推理耗时长
        elapsed_ms = (time.perf_counter() - start) * 1000
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error calling search: {e}") from e

    if response.status_code != 200:
        raise RuntimeError(f"Search returned status {response.status_code}: {response.text}")

    data = response.json()
    returned_ids = [chunk["id"] for chunk in data["chunks"]]
    return returned_ids, elapsed_ms


def evaluate(testset: list[dict], top_k: int = 5) -> dict:
    """跑完整 Eval,返回结构化结果"""
    if not testset:
        raise ValueError("testset is empty")

    details = []
    latencies_ms = []

    for case in testset:
        expected = case["expected_doc_id"]
        try:
            returned_ids, elapsed_ms = search_one(case["query"], top_k=top_k)
            latencies_ms.append(elapsed_ms)
            if expected in returned_ids:
                hit = 1
                rank = returned_ids.index(expected) + 1
                rr = 1 / rank
            else:
                hit = 0
                rank = None
                rr = 0.0
            detail = {
                "id": case["id"],
                "query": case["query"],
                "expected_doc_id": expected,
                "topic": case["topic"],
                "difficulty": case["difficulty"],
                "hit": hit,
                "rank": rank,
                "rr": rr,
                "latency_ms": elapsed_ms,
                "returned_ids": returned_ids,
            }
        except RuntimeError as e:
            detail = {
                "id": case["id"],
                "query": case["query"],
                "expected_doc_id": expected,
                "topic": case["topic"],
                "difficulty": case["difficulty"],
                "hit": 0,
                "rank": None,
                "rr": 0.0,
                "latency_ms": -1,
                "returned_ids": [],
                "error": str(e),
            }
        details.append(detail)

    total = len(details)
    hit_at_k = sum(d["hit"] for d in details) / total
    mrr = sum(d["rr"] for d in details) / total

    if latencies_ms:
        lat_arr = np.array(latencies_ms)
        p50 = float(np.percentile(lat_arr, 50))
        p95 = float(np.percentile(lat_arr, 95))
        p99 = float(np.percentile(lat_arr, 99))
    else:
        p50 = p95 = p99 = -1.0

    # by_topic
    topics = {}
    for d in details:
        t = d["topic"]
        if t not in topics:
            topics[t] = []
        topics[t].append(d)

    by_topic = {}
    for t, items in topics.items():
        n = len(items)
        by_topic[t] = {
            "total": n,
            "hit_at_k": sum(i["hit"] for i in items) / n,
            "mrr": sum(i["rr"] for i in items) / n,
        }

    # by_difficulty
    difficulties = {}
    for d in details:
        diff = d["difficulty"]
        if diff not in difficulties:
            difficulties[diff] = []
        difficulties[diff].append(d)

    by_difficulty = {}
    for diff, items in difficulties.items():
        n = len(items)
        by_difficulty[diff] = {
            "total": n,
            "hit_at_k": sum(i["hit"] for i in items) / n,
            "mrr": sum(i["rr"] for i in items) / n,
        }

    return {
        "summary": {
            "total": total,
            "hit_at_k": hit_at_k,
            "mrr": mrr,
            "latency_ms": {"p50": p50, "p95": p95, "p99": p99},
        },
        "by_topic": by_topic,
        "by_difficulty": by_difficulty,
        "details": details,
    }


def write_report(result: dict, output_path: str) -> None:
    """
    生成两份报告:
    1. {output_path}.json - 完整结果
    2. {output_path}.md  - 人类可读报告
    """
    from datetime import datetime

    base = Path(output_path)
    base.parent.mkdir(parents=True, exist_ok=True)

    # JSON report
    with open(f"{output_path}.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Markdown report
    s = result["summary"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    lines.append(f"# Eval Report (BGE Rerank) - {timestamp}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- 测试用例数: {s['total']}")
    lines.append(f"- **Hit@5: {s['hit_at_k']:.2f}**")
    lines.append(f"- **MRR: {s['mrr']:.2f}**")
    lat = s["latency_ms"]
    lines.append(f"- 延迟 (ms): p50={lat['p50']:.1f} / p95={lat['p95']:.1f} / p99={lat['p99']:.1f}")
    lines.append("")

    lines.append("## By Topic")
    lines.append("| Topic | Total | Hit@5 | MRR |")
    lines.append("|---|---|---|---|")
    for topic, stats in result["by_topic"].items():
        lines.append(f"| {topic} | {stats['total']} | {stats['hit_at_k']:.2f} | {stats['mrr']:.2f} |")
    lines.append("")

    lines.append("## By Difficulty")
    lines.append("| Difficulty | Total | Hit@5 | MRR |")
    lines.append("|---|---|---|---|")
    for diff, stats in result["by_difficulty"].items():
        lines.append(f"| {diff} | {stats['total']} | {stats['hit_at_k']:.2f} | {stats['mrr']:.2f} |")
    lines.append("")

    failed = [d for d in result["details"] if d["hit"] == 0]
    lines.append("## Failed Cases (Hit=0)")
    lines.append("| ID | Query | Topic | Difficulty | Returned IDs (top-5) |")
    lines.append("|---|---|---|---|---|")
    for d in failed:
        ids_str = ", ".join(d["returned_ids"]) if d["returned_ids"] else "(error)"
        lines.append(f"| {d['id']} | {d['query']} | {d['topic']} | {d['difficulty']} | {ids_str} |")
    lines.append("")

    with open(f"{output_path}.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    from datetime import datetime

    _here = Path(__file__).parent
    testset_path = str(_here / "testset.jsonl")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = str(_here / "reports" / f"eval_bge_{timestamp}")

    print(f"Loading testset from {testset_path}...")
    testset = load_testset(testset_path)
    print(f"Loaded {len(testset)} cases.")

    print("Running Eval with BGE rerank (Milvus top-20 → BGE → top-5)...")
    print("预计耗时 5-8 分钟（CPU 推理，25 条 × 20 候选）")
    result = evaluate(testset, top_k=5)

    print(f"\n===== BGE RERANK SUMMARY =====")
    print(f"Hit@5: {result['summary']['hit_at_k']:.3f}")
    print(f"MRR:   {result['summary']['mrr']:.3f}")
    print(
        f"Latency p50/p95/p99 (ms): "
        f"{result['summary']['latency_ms']['p50']:.1f} / "
        f"{result['summary']['latency_ms']['p95']:.1f} / "
        f"{result['summary']['latency_ms']['p99']:.1f}"
    )

    write_report(result, report_path)
    print(f"\nReport written to: {report_path}.md and {report_path}.json")
