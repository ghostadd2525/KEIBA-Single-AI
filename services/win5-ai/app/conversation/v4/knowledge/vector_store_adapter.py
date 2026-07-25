# -*- coding: utf-8 -*-
"""
Vector Store Adapter — Interface only。

実 Vector DB / 外部 API には接続しない。
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class VectorStoreAdapter(Protocol):
    """ベクトル類似検索の契約（未実装接続）。"""

    connected: bool

    def similarity_search(
        self,
        query_vector: list[float],
        *,
        limit: int = 5,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        クエリベクトルに近いドキュメントを返す。
        Phase 10 では Interface のみ。Vector DB 接続は行わない。
        """
        ...

    def meta(self) -> dict[str, object]:
        ...


class UnconnectedVectorStoreAdapter:
    """
    Vector Store Adapter の未接続プレースホルダ。
    実 Vector DB / 外部 API には接続しない。
    """

    connected = False
    provider_name = "unconnected_vector_store_adapter"

    def similarity_search(
        self,
        query_vector: list[float],
        *,
        limit: int = 5,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError(
            "Vector Store Adapter は Interface のみです。実 Vector DB には接続しません。"
        )

    def meta(self) -> dict[str, object]:
        return {
            "adapter": self.provider_name,
            "connected": False,
            "vector_db": False,
            "external_api": False,
            "interface_only": True,
        }
