# -*- coding: utf-8 -*-
"""
RAG Runtime — V5 Phase 2。

Embedding Runtime + Vector Store Runtime + Knowledge Source Stub。
外部 RAG SaaS / LLM 生成は行わない（検索ランタイムのみ）。
"""
from __future__ import annotations

from typing import Any

from ...v4.knowledge.source import StubKnowledgeSource
from .embedding_runtime import EmbeddingRuntime
from .vector_store_runtime import VectorStoreRuntime


class RAGRuntime:
    """共通知識 RAG 検索 Runtime（生成なし）。"""

    name = "rag_runtime"
    uses_llm = False

    def __init__(
        self,
        *,
        source: StubKnowledgeSource | None = None,
        embedding: EmbeddingRuntime | None = None,
        vector_store: VectorStoreRuntime | None = None,
        auto_index: bool = True,
    ) -> None:
        self.source = source or StubKnowledgeSource()
        self.embedding = embedding or EmbeddingRuntime()
        self.vector_store = vector_store or VectorStoreRuntime()
        self._indexed = False
        if auto_index:
            self.build_index()

    def build_index(self) -> dict[str, Any]:
        self.vector_store.clear()
        docs = self.source.list_documents()
        for doc in docs:
            text = f"{doc.title}\n{doc.body}\n{' '.join(doc.tags)}"
            vec = self.embedding.embed_one(text)
            self.vector_store.upsert(
                doc_id=doc.doc_id,
                vector=vec,
                document=doc.as_dict(),
                category=doc.category,
            )
        self._indexed = True
        return {
            "indexed": True,
            "document_count": len(docs),
            "vector_count": self.vector_store.count(),
        }

    def retrieve(
        self,
        query: str | None = None,
        *,
        category: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        if not self._indexed:
            self.build_index()
        q = str(query or "").strip()
        qvec = self.embedding.embed_one(q)
        hits = self.vector_store.similarity_search(
            qvec, limit=limit, category=category
        )
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
            "runtime": self.name,
            "indexed": self._indexed,
            "embedding": self.embedding.meta(),
            "vector_store": self.vector_store.meta(),
            "llm": False,
            "external_api": False,
            "generation": False,
            "rag_search_only": True,
        }
