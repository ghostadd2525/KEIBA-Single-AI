# -*- coding: utf-8 -*-
"""
Vector Store Runtime — V5 Phase 2。

インメモリベクトル格納 · コサイン類似度検索。
外部 Vector DB / クラウド API には接続しない。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VectorRecord:
    doc_id: str
    vector: list[float]
    document: dict[str, Any]
    category: str | None = None


class VectorStoreRuntime:
    """インメモリ Vector Store Runtime。"""

    name = "vector_store_runtime"
    external_api = False
    backend = "in_memory"

    def __init__(self) -> None:
        self._records: list[VectorRecord] = []

    def clear(self) -> None:
        self._records.clear()

    def upsert(
        self,
        *,
        doc_id: str,
        vector: list[float],
        document: dict[str, Any],
        category: str | None = None,
    ) -> None:
        self._records = [r for r in self._records if r.doc_id != doc_id]
        self._records.append(
            VectorRecord(
                doc_id=doc_id,
                vector=list(vector),
                document=dict(document),
                category=category,
            )
        )

    def count(self) -> int:
        return len(self._records)

    def similarity_search(
        self,
        query_vector: list[float],
        *,
        limit: int = 5,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        lim = max(1, min(int(limit or 5), 50))
        scored: list[tuple[float, VectorRecord]] = []
        for rec in self._records:
            if category and rec.category != category:
                continue
            score = self._cosine(query_vector, rec.vector)
            scored.append((score, rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        hits: list[dict[str, Any]] = []
        for score, rec in scored[:lim]:
            hits.append(
                {
                    "score": round(float(score), 6),
                    "document": dict(rec.document),
                    "doc_id": rec.doc_id,
                }
            )
        return hits

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        n = min(len(a), len(b))
        if n == 0:
            return 0.0
        dot = 0.0
        na = 0.0
        nb = 0.0
        for i in range(n):
            dot += a[i] * b[i]
            na += a[i] * a[i]
            nb += b[i] * b[i]
        denom = math.sqrt(na) * math.sqrt(nb)
        if denom <= 1e-12:
            return 0.0
        return dot / denom

    def meta(self) -> dict[str, Any]:
        return {
            "runtime": self.name,
            "backend": self.backend,
            "external_api": False,
            "vector_db_cloud": False,
            "record_count": self.count(),
            "connected": True,
            "local_only": True,
        }
