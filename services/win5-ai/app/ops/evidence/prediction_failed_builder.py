# -*- coding: utf-8 -*-
"""Prediction failed Improvement Evidence Builder."""
from __future__ import annotations

from typing import Any

from .base import make_envelope


class PredictionFailedEvidenceBuilder:
    event_type = "prediction_failed"

    def build(self, ctx: dict[str, Any]) -> dict[str, Any] | None:
        payload = {
            "race_id": ctx.get("race_id"),
            "reason": ctx.get("reason") or "prediction_missing",
            "detail": ctx.get("detail"),
            "engine_source": ctx.get("engine_source"),
            "fallback_reason": ctx.get("fallback_reason"),
        }
        return make_envelope(
            event_type=self.event_type,
            race_id=ctx.get("race_id"),
            race_date=ctx["race_date"],
            payload=payload,
            model_version=ctx.get("model_version"),
            timestamp=ctx.get("timestamp"),
        )
