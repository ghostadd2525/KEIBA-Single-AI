# -*- coding: utf-8 -*-
"""
Knowledge Runtime — V5 Phase 2 Completion。

構成:
  Knowledge Runtime
    → RAG Runtime（既定検索経路）
        → Embedding Runtime
        → Vector Store Runtime
        → Knowledge Source Stub
    → Retriever Runtime（キーワード · Benchmark / フォールバック）

外部 Embedding API / クラウド Vector DB / LLM / Memory / UI は含まない。
"""
from __future__ import annotations

from typing import Any

from ...v4.knowledge.source import StubKnowledgeSource
from .embedding_runtime import EmbeddingRuntime
from .rag_runtime import RAGRuntime
from .retriever_runtime import RetrieverRuntime
from .vector_store_runtime import VectorStoreRuntime


class KnowledgeRuntime:
    """共通知識検索 Runtime（V5 Phase 2）。"""

    version = "v5"
    phase = 2

    def __init__(
        self,
        *,
        source: StubKnowledgeSource | None = None,
        retriever: RetrieverRuntime | None = None,
        embedding: EmbeddingRuntime | None = None,
        vector_store: VectorStoreRuntime | None = None,
        rag: RAGRuntime | None = None,
        use_rag: bool = True,
    ) -> None:
        self.source = source or StubKnowledgeSource()
        self.embedding = embedding or EmbeddingRuntime()
        self.vector_store = vector_store or VectorStoreRuntime()
        self.retriever = retriever or RetrieverRuntime(source=self.source)
        if retriever is not None and source is not None:
            self.retriever.source = source

        self.rag = rag or RAGRuntime(
            source=self.source,
            embedding=self.embedding,
            vector_store=self.vector_store,
            auto_index=True,
        )
        self.use_rag = bool(use_rag)

    def search(
        self,
        query: str | None = None,
        *,
        category: str | None = None,
        limit: int = 5,
        force_rag: bool | None = None,
        force_keyword: bool = False,
    ) -> dict[str, Any]:
        """RAG Runtime（既定）または Retriever Runtime で検索。"""
        use_rag = (
            False
            if force_keyword
            else (self.use_rag if force_rag is None else bool(force_rag))
        )

        if use_rag:
            result = self.rag.retrieve(
                query, category=category, limit=limit
            )
            path = "rag_runtime"
        else:
            result = self.retriever.retrieve(
                query, category=category, limit=limit
            )
            path = "retriever_runtime"

        return {
            "ok": True,
            "runtime": "knowledge_runtime",
            "version": self.version,
            "phase": self.phase,
            "search_path": path,
            "via_retriever_runtime": path == "retriever_runtime",
            "via_rag_runtime": path == "rag_runtime",
            "query": result.get("query", query),
            "category": result.get("category", category),
            "hits": result.get("hits") or [],
            "hit_count": int(result.get("hit_count") or 0),
            "source_meta": result.get("source_meta") or self.source.meta(),
            "retriever_meta": (
                self.rag.meta() if path == "rag_runtime" else self.retriever.meta()
            ),
            "embedding_meta": self.embedding.meta(),
            "vector_store_meta": self.vector_store.meta(),
            "vector_db": False,
            "vector_store_local": True,
            "embedding": True,
            "embedding_local": True,
            "external_api": False,
            "rag": path == "rag_runtime",
            "llm": False,
            "memory": False,
            "user_private": False,
            "prediction_rationale": False,
            "message": (
                "Knowledge Runtime（V5 Phase 2）: "
                f"{path} → Source Stub。"
                " 外部 Embedding/Vector DB/LLM 未接続。"
            ),
        }

    def meta(self) -> dict[str, Any]:
        return {
            "runtime": "knowledge_runtime",
            "version": self.version,
            "phase": self.phase,
            "use_rag": self.use_rag,
            "retriever": self.retriever.name,
            "rag": self.rag.name,
            "embedding": self.embedding.meta(),
            "vector_store": self.vector_store.meta(),
            "source": self.source.meta(),
            "vector_db": False,
            "external_api": False,
        }
