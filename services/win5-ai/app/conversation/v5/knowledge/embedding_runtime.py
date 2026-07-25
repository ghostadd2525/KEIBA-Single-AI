# -*- coding: utf-8 -*-
"""
Embedding Runtime — V5 Phase 2。

ローカル決定的ハッシュ埋め込みのみ。
外部 Embedding API / LLM には接続しない。
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Any


_TOKEN_RE = re.compile(r"[\wぁ-んァ-ヶ一-龥]+", re.UNICODE)


class EmbeddingRuntime:
    """共通知識用のローカル埋め込み Runtime。"""

    name = "embedding_runtime"
    external_api = False
    provider = "local_hashing"

    def __init__(self, *, dimensions: int = 64) -> None:
        self.dimensions = max(8, int(dimensions))

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_one(t) for t in texts]

    def embed_one(self, text: str | None) -> list[float]:
        raw = str(text or "").strip().lower()
        vec = [0.0] * self.dimensions
        if not raw:
            return vec
        tokens = _TOKEN_RE.findall(raw) or [raw]
        for tok in tokens:
            digest = hashlib.sha256(tok.encode("utf-8")).digest()
            # 複数バケットへ分散
            for i in range(0, min(16, len(digest) - 1), 2):
                idx = digest[i] % self.dimensions
                sign = 1.0 if (digest[i + 1] % 2 == 0) else -1.0
                vec[idx] += sign
            # 文字 n-gram 補助
            for n in (2, 3):
                for j in range(max(0, len(tok) - n + 1)):
                    gram = tok[j : j + n]
                    g = hashlib.md5(gram.encode("utf-8")).digest()
                    idx = g[0] % self.dimensions
                    vec[idx] += 0.5
        return self._l2_normalize(vec)

    @staticmethod
    def _l2_normalize(vec: list[float]) -> list[float]:
        norm = math.sqrt(sum(v * v for v in vec))
        if norm <= 1e-12:
            return vec
        return [v / norm for v in vec]

    def meta(self) -> dict[str, Any]:
        return {
            "runtime": self.name,
            "provider": self.provider,
            "dimensions": self.dimensions,
            "external_api": False,
            "llm": False,
            "connected": True,
            "local_only": True,
        }
