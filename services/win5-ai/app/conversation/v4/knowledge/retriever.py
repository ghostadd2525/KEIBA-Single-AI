# -*- coding: utf-8 -*-
"""
Retriever Interface と Stub 実装。

Knowledge Provider は本 Interface のみを利用する。
Stub 実装は Knowledge Source（既存 Stub）のキーワード照合のみ。
Embedding / Vector Store には接続しない（参照保持のみ · Flag ON 時）。
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .embedding_adapter import EmbeddingAdapter, UnconnectedEmbeddingAdapter
from .source import KnowledgeDocument, StubKnowledgeSource
from .vector_store_adapter import UnconnectedVectorStoreAdapter, VectorStoreAdapter


@runtime_checkable
class Retriever(Protocol):
    """共通知識検索の契約。"""

    def retrieve(
        self,
        query: str | None = None,
        *,
        category: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        ...

    def meta(self) -> dict[str, Any]:
        ...


class StubRetriever:
    """
    Retriever Interface の Stub 実装。
    Knowledge Source のみ使用。Embedding / Vector DB は未接続。
    """

    stub = True

    def __init__(
        self,
        source: StubKnowledgeSource | None = None,
        *,
        embedding: EmbeddingAdapter | None = None,
        vector_store: VectorStoreAdapter | None = None,
        integration_wired: bool = False,
    ) -> None:
        self.source = source or StubKnowledgeSource()
        # Interface 配線用（呼び出し禁止 · 実接続なし）
        self.embedding = embedding
        self.vector_store = vector_store
        self.integration_wired = bool(integration_wired)

    def retrieve(
        self,
        query: str | None = None,
        *,
        category: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        # Embedding / Vector Store は呼ばない（Interface only）
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
            "retriever": "stub_retriever",
            "source_meta": self.source.meta(),
            **self.meta(),
        }

    def meta(self) -> dict[str, Any]:
        emb_meta = (
            self.embedding.meta()
            if self.embedding is not None and hasattr(self.embedding, "meta")
            else {"connected": False, "interface_only": True, "wired": False}
        )
        vs_meta = (
            self.vector_store.meta()
            if self.vector_store is not None and hasattr(self.vector_store, "meta")
            else {"connected": False, "interface_only": True, "wired": False}
        )
        return {
            "stub": True,
            "integration_wired": self.integration_wired,
            "vector_db": False,
            "embedding": False,
            "external_api": False,
            "embedding_adapter": emb_meta,
            "vector_store_adapter": vs_meta,
            "uses_embedding_runtime": False,
            "uses_vector_store_runtime": False,
        }

    @staticmethod
    def _hit(doc: KnowledgeDocument, *, score: float) -> dict[str, Any]:
        return {
            "score": round(float(score), 3),
            "document": doc.as_dict(),
        }


def build_default_retriever(*, integration: bool = False) -> StubRetriever:
    """
    既定 Retriever。
    integration=True のとき Embedding / VectorStore Adapter を配線するが未接続のまま。
    """
    if integration:
        return StubRetriever(
            embedding=UnconnectedEmbeddingAdapter(),
            vector_store=UnconnectedVectorStoreAdapter(),
            integration_wired=True,
        )
    return StubRetriever(integration_wired=False)
