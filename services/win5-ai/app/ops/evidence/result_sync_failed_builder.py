# -*- coding: utf-8 -*-
"""Result sync failed Improvement Evidence Builder."""
from __future__ import annotations

from typing import Any

from .base import make_envelope


class ResultSyncFailedEvidenceBuilder:
    event_type = "result_sync_failed"

    def build(self, ctx: dict[str, Any]) -> dict[str, Any] | None:
        payload = {
            "race_date": ctx["race_date"],
            "race_id": ctx.get("race_id"),
            "error": ctx.get("error") or "result_sync_failed",
            "attempt": ctx.get("attempt"),
            "provider": ctx.get("provider") or "CsvResultProvider",
        }
        return make_envelope(
            event_type=self.event_type,
            race_id=ctx.get("race_id"),
            race_date=ctx["race_date"],
            payload=payload,
            model_version=None,
            timestamp=ctx.get("timestamp"),
        )
