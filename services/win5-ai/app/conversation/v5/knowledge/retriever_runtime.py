# -*- coding: utf-8 -*-
"""
Retriever Runtime — Retriever Interface の V5 実装。

Knowledge Source Stub を用いたキーワード検索のみ。
Embedding / Vector DB / 外部 API / LLM には接続しない。
"""
from __future__ import annotations

from typing import Any

from ...v4.knowledge.source import KnowledgeDocument, StubKnowledgeSource


class RetrieverRuntime:
    """
    Retriever Protocol 実装クラス（V5）。
    V4 StubRetriever とは別実装。Source Stub のみ利用。
    """

    name = "retriever_runtime"
    stub_source = True
    uses_embedding = False
    uses_vector_db = False

    def __init__(self, source: StubKnowledgeSource | None = None) -> None:
        self.source = source or StubKnowledgeSource()

    def retrieve(
        self,
        query: str | None = None,
        *,
        category: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        q = str(query or "").strip().lower()
        lim = max(1, min(int(limit or 5), 20))
        hits: list[dict[str, Any]] = []

        for doc in self.source.list_documents():
            if category and doc.category != category:
                continue
            if not q:
                hits.append(self._hit(doc, score=0.1))
                continue
            blob = f"{doc.title} {doc.body} {' '.join(doc.tags)}".lower()
            score = 0.0
            for token in q.replace("　", " ").split():
                if token and token in blob:
                    score += 1.0
            if score > 0 or q in blob:
                if q in blob and score == 0:
                    score = 0.5
                hits.append(self._hit(doc, score=score))

        hits.sort(key=lambda h: float(h.get("score") or 0), reverse=True)
        hits = hits[:lim]
        return {
            "hits": hits,
            "hit_count": len(hits),
            "query": query,
            "category": category,
            "retriever": self.name,
            "source_meta": self.source.meta(),
            **self.meta(),
        }

    def meta(self) -> dict[str, Any]:
        return {
            "runtime": "v5_retriever_runtime",
            "stub": True,
            "vector_db": False,
            "embedding": False,
            "external_api": False,
            "llm": False,
            "uses_embedding_runtime": False,
            "uses_vector_store_runtime": False,
            "knowledge_source": "stub",
        }

    @staticmethod
    def _hit(doc: KnowledgeDocument, *, score: float) -> dict[str, Any]:
        return {
            "score": round(float(score), 3),
            "document": doc.as_dict(),
        }
