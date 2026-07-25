# -*- coding: utf-8 -*-
"""
Embedding Adapter — Interface only。

実 Embedding / 外部 API には接続しない。
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingAdapter(Protocol):
    """テキスト → ベクトル変換の契約（未実装接続）。"""

    connected: bool

    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        テキスト列を埋め込みベクトルに変換する。
        Phase 10 では Interface のみ。実装・外部接続は行わない。
        """
        ...

    def meta(self) -> dict[str, object]:
        ...


class UnconnectedEmbeddingAdapter:
    """
    Embedding Adapter の未接続プレースホルダ。
    実 Embedding / 外部 API には接続しない。
    """

    connected = False
    provider_name = "unconnected_embedding_adapter"

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "Embedding Adapter は Interface のみです。実 Embedding には接続しません。"
        )

    def meta(self) -> dict[str, object]:
        return {
            "adapter": self.provider_name,
            "connected": False,
            "external_api": False,
            "interface_only": True,
        }
