# -*- coding: utf-8 -*-
"""
V5 Phase 2 — Knowledge Runtime Benchmark（一括計測）。

途中計測なし。完了後に Embedding / Vector Store / Retriever / Provider /
Knowledge Tool / Knowledge Runtime 全体を計測する。
"""
from __future__ import annotations

import json
import os
import statistics
import time
from pathlib import Path
from typing import Any, Callable


def _time_ms(fn: Callable[[], Any], rounds: int = 30, warmup: int = 3) -> dict[str, float]:
    for _ in range(warmup):
        fn()
    samples: list[float] = []
    for _ in range(rounds):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return {
        "rounds": float(rounds),
        "min_ms": round(min(samples), 4),
        "max_ms": round(max(samples), 4),
        "mean_ms": round(statistics.mean(samples), 4),
        "median_ms": round(statistics.median(samples), 4),
        "p95_ms": round(sorted(samples)[max(0, int(len(samples) * 0.95) - 1)], 4),
    }


def run_benchmark(*, rounds: int = 30) -> dict[str, Any]:
    os.environ["F_V5_KNOWLEDGE_RUNTIME"] = "true"
    os.environ["F_V4_KNOWLEDGE_LAYER"] = "true"

    from app.conversation.v4.knowledge import KnowledgeProvider
    from app.conversation.v4.tools import KnowledgeTool, ToolManager
    from app.conversation.v5.knowledge import (
        EmbeddingRuntime,
        KnowledgeRuntime,
        RAGRuntime,
        RetrieverRuntime,
        VectorStoreRuntime,
    )

    query = "本命の意味"
    kr = KnowledgeRuntime()
    emb = kr.embedding
    store = kr.vector_store
    rag = kr.rag
    retriever = kr.retriever
    provider = KnowledgeProvider(runtime=kr)
    tool = KnowledgeTool(provider=provider)
    manager = ToolManager(knowledge_tool=tool)

    results: dict[str, Any] = {
        "benchmark": "v5_knowledge_runtime_phase2",
        "query": query,
        "rounds": rounds,
        "components": {},
    }

    results["components"]["embedding_runtime"] = _time_ms(
        lambda: emb.embed_one(query), rounds=rounds
    )
    # index already built; measure upsert+search path via embed of doc-like text
    sample_vec = emb.embed_one("glossary honmei")

    def _vs() -> None:
        store.similarity_search(sample_vec, limit=5)

    results["components"]["vector_store_runtime"] = _time_ms(_vs, rounds=rounds)

    results["components"]["retriever_runtime"] = _time_ms(
        lambda: retriever.retrieve(query, limit=5), rounds=rounds
    )

    results["components"]["rag_runtime"] = _time_ms(
        lambda: rag.retrieve(query, limit=5), rounds=rounds
    )

    results["components"]["knowledge_provider"] = _time_ms(
        lambda: provider.search(query, limit=5), rounds=rounds
    )

    results["components"]["knowledge_tool"] = _time_ms(
        lambda: tool.invoke(query=query, limit=5), rounds=rounds
    )

    # Tool Manager 経路（Manager 自体は未変更 · 呼び出しのみ）
    results["components"]["knowledge_tool_via_manager"] = _time_ms(
        lambda: manager.search_knowledge(query, limit=5), rounds=rounds
    )

    results["components"]["knowledge_runtime_total"] = _time_ms(
        lambda: kr.search(query, limit=5), rounds=rounds
    )

    # 健全性スナップショット（1回）
    snap = kr.search(query, limit=5)
    results["sanity"] = {
        "hit_count": snap.get("hit_count"),
        "search_path": snap.get("search_path"),
        "phase": snap.get("phase"),
        "embedding_local": snap.get("embedding_local"),
        "vector_store_local": snap.get("vector_store_local"),
        "external_api": snap.get("external_api"),
        "llm": snap.get("llm"),
        "rag": snap.get("rag"),
    }
    results["stack"] = {
        "embedding": emb.meta(),
        "vector_store": store.meta(),
        "rag": rag.meta(),
        "retriever": retriever.meta(),
        "knowledge_runtime": kr.meta(),
    }
    return results


def main() -> None:
    report = run_benchmark(rounds=30)
    # services/win5-ai/tests/ops → KEIBA-Single-AI/docs/releases
    repo_docs = (
        Path(__file__).resolve().parents[2].parent.parent / "docs" / "releases"
    )
    repo_docs.mkdir(parents=True, exist_ok=True)
    json_path = repo_docs / "v5-phase2-knowledge-runtime-benchmark.json"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Wrote {json_path}")


if __name__ == "__main__":
    main()
