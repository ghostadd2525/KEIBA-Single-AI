# -*- coding: utf-8 -*-
"""Feature missing Improvement Evidence Builder."""
from __future__ import annotations

from typing import Any

from .base import make_envelope


class FeatureMissingEvidenceBuilder:
    event_type = "feature_missing"

    def build(self, ctx: dict[str, Any]) -> dict[str, Any] | None:
        payload = {
            "race_id": ctx.get("race_id"),
            "reason": ctx.get("reason") or "feature_missing",
            "fallback_reason": ctx.get("fallback_reason"),
            "feature_source": ctx.get("feature_source"),
            "engine_source": ctx.get("engine_source"),
            "notes": ctx.get("notes"),
        }
        return make_envelope(
            event_type=self.event_type,
            race_id=ctx.get("race_id"),
            race_date=ctx["race_date"],
            payload=payload,
            model_version=ctx.get("model_version"),
            timestamp=ctx.get("timestamp"),
        )
