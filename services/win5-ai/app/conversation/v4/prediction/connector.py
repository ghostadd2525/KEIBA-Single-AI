# -*- coding: utf-8 -*-
"""
Prediction Connector — Conversation → Prediction API（Read Only）。

Prediction を変更・再計算しない。取得のみ。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class PredictionReadable(Protocol):
    def get_with_meta(self, race_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        ...


@dataclass
class OfficialPredictionFetch:
    ok: bool
    race_id: str | None
    bundle: dict[str, Any] | None = None
    api_meta: dict[str, Any] | None = None
    error: str | None = None
    available: bool = False


@dataclass
class PredictionConnector:
    """
    Prediction API 接続口（Read Only）。
    既定は engine.adapters.prediction_adapter。
    """

    source: PredictionReadable | None = None
    _timeout_note: str = field(default="read_only", repr=False)

    def _source(self) -> PredictionReadable:
        if self.source is not None:
            return self.source
        from ....engine.adapters import prediction_adapter

        return prediction_adapter

    def fetch(self, race_id: str | None) -> OfficialPredictionFetch:
        rid = str(race_id or "").strip()
        if not rid:
            return OfficialPredictionFetch(
                ok=False,
                race_id=None,
                error="race_id_missing",
                available=False,
            )
        try:
            bundle, meta = self._source().get_with_meta(rid)
        except Exception as exc:  # noqa: BLE001 — fail-open
            return OfficialPredictionFetch(
                ok=False,
                race_id=rid,
                error=f"prediction_api_error:{type(exc).__name__}",
                available=False,
            )

        if bundle is None:
            return OfficialPredictionFetch(
                ok=False,
                race_id=rid,
                api_meta=meta if isinstance(meta, dict) else None,
                error="prediction_unavailable",
                available=False,
            )

        # 読み取り成功（内容の改変は Adapter 側で投影のみ）
        return OfficialPredictionFetch(
            ok=True,
            race_id=rid,
            bundle=bundle,
            api_meta=meta if isinstance(meta, dict) else None,
            available=True,
            error=None,
        )
