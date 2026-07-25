# -*- coding: utf-8 -*-
"""
ReviewContext — Review Agent の唯一の入力契約。

個別 payload（prediction 単体など）を Agent が直接参照しないための統一 Context。
未接続要素は Stub または None。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ReviewContext:
    mode: str = "review"
    prediction: dict[str, Any] | None = None
    prediction_meta: dict[str, Any] = field(default_factory=dict)
    buy_strategy: dict[str, Any] | None = None
    race: dict[str, Any] | None = None
    horse: dict[str, Any] | None = None
    user: dict[str, Any] | None = None
    request: dict[str, Any] = field(default_factory=dict)
    # Conversation History（短期 · Prompt 用。永続しない）
    history: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def message(self) -> str:
        return str((self.request or {}).get("message") or "").strip()

    @property
    def race_id(self) -> str | None:
        rid = (self.request or {}).get("race_id")
        if rid:
            return str(rid)
        if isinstance(self.race, dict) and self.race.get("race_id"):
            return str(self.race["race_id"])
        if isinstance(self.prediction, dict) and self.prediction.get("race_id"):
            return str(self.prediction["race_id"])
        return None
