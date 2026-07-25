# -*- coding: utf-8 -*-
"""
Knowledge Provider — Retriever Interface のみ利用。

V5: F_V5_KNOWLEDGE_RUNTIME=ON 時は Knowledge Runtime → Retriever Runtime → Source Stub。
V4: Flag OFF 時は既存 StubRetriever 経路（Platform Freeze 互換）。

Conversation Platform 構造は変更しない。
Embedding / Vector DB / 外部 API には Provider から直接触れない。
"""
from __future__ import annotations

from typing import Any

from ..flags import knowledge_integration_enabled, knowledge_runtime_enabled
from .retriever import Retriever, build_default_retriever
from .source import StubKnowledgeSource


class KnowledgeProvider:
    """
    共通知識 Provider。
    検索は Retriever Interface 経由のみ。
    """

    stub = True

    def __init__(
        self,
        retriever: Retriever | None = None,
        *,
        source: StubKnowledgeSource | None = None,
        runtime: Any | None = None,
    ) -> None:
        self._runtime = None
        if retriever is not None:
            self.retriever = retriever
            if source is not None and hasattr(self.retriever, "source"):
                self.retriever.source = source  # type: ignore[attr-defined]
        elif runtime is not None:
            self._runtime = runtime
            self.retriever = runtime.retriever
        elif knowledge_runtime_enabled():
            from ...v5.knowledge import KnowledgeRuntime

            self._runtime = KnowledgeRuntime(source=source)
            self.retriever = self._runtime.retriever
        else:
            self.retriever = build_default_retriever(
                integration=knowledge_integration_enabled()
            )
            if source is not None and hasattr(self.retriever, "source"):
                self.retriever.source = source  # type: ignore[attr-defined]

    @property
    def source(self) -> StubKnowledgeSource | None:
        return getattr(self.retriever, "source", None)

    @property
    def runtime_enabled(self) -> bool:
        return self._runtime is not None

    def search(
        self,
        query: str | None = None,
        *,
        category: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        # Runtime がある場合は Runtime.search を優先（同一 Retriever 経路）
        if self._runtime is not None:
            out = self._runtime.search(
                query, category=category, limit=limit
            )
            return {
                "stub": True,
                "provider": "knowledge_provider",
                "via_retriever": True,
                "via_retriever_runtime": bool(out.get("via_retriever_runtime")),
                "via_rag_runtime": bool(out.get("via_rag_runtime")),
                "retriever_interface": True,
                "knowledge_runtime": True,
                "knowledge_integration": knowledge_integration_enabled(),
                "search_path": out.get("search_path"),
                "phase": out.get("phase"),
                "query": out.get("query", query),
                "category": out.get("category", category),
                "hits": out.get("hits") or [],
                "hit_count": int(out.get("hit_count") or 0),
                "source_meta": out.get("source_meta")
                or (self.source.meta() if self.source else {}),
                "retriever_meta": out.get("retriever_meta") or {},
                "embedding_meta": out.get("embedding_meta") or {},
                "vector_store_meta": out.get("vector_store_meta") or {},
                "runtime": out.get("runtime"),
                "version": out.get("version"),
                "vector_db": False,
                "embedding": bool(out.get("embedding")),
                "embedding_local": bool(out.get("embedding_local")),
                "rag": bool(out.get("rag")),
                "external_api": False,
                "user_private": False,
                "prediction_rationale": False,
                "message": out.get("message")
                or (
                    "Knowledge Provider → Knowledge Runtime → "
                    "RAG/Retriever Runtime → Source Stub"
                ),
            }

        # Provider → Retriever Interface のみ（V4 互換）
        result = self.retriever.retrieve(
            query, category=category, limit=limit
        )
        integration = knowledge_integration_enabled()
        return {
            "stub": True,
            "provider": "knowledge_provider",
            "via_retriever": True,
            "via_retriever_runtime": False,
            "retriever_interface": True,
            "knowledge_runtime": False,
            "knowledge_integration": integration,
            "query": result.get("query", query),
            "category": result.get("category", category),
            "hits": result.get("hits") or [],
            "hit_count": int(result.get("hit_count") or 0),
            "source_meta": result.get("source_meta")
            or (self.source.meta() if self.source else {}),
            "retriever_meta": {
                k: v
                for k, v in result.items()
                if k
                not in (
                    "hits",
                    "hit_count",
                    "query",
                    "category",
                    "source_meta",
                )
            },
            "vector_db": False,
            "embedding": False,
            "external_api": False,
            "user_private": False,
            "prediction_rationale": False,
            "message": (
                "Knowledge Provider は Retriever Interface 経由です。"
                " Embedding / Vector DB は未接続（Interface only）。"
            ),
        }


# Phase 9 互換エイリアス
StubKnowledgeProvider = KnowledgeProvider
