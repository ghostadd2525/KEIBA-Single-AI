# -*- coding: utf-8 -*-
"""Miss Improvement Evidence Builder."""
from __future__ import annotations

from typing import Any

from ..miss_evidence import build_miss_evidence
from .base import make_envelope


class MissEvidenceBuilder:
    event_type = "miss"

    def build(self, ctx: dict[str, Any]) -> dict[str, Any] | None:
        inner = build_miss_evidence(
            race_id=ctx["race_id"],
            bundle=ctx["bundle"],
            meta=ctx.get("meta") or {},
            winner_horse_number=ctx.get("winner_horse_number"),
            winner_name=ctx.get("winner_name"),
            hit_at_1=ctx["hit_at_1"],
            hit_at_3=ctx["hit_at_3"],
            hit_at_5=ctx["hit_at_5"],
            timestamp=ctx.get("timestamp"),
        )
        if not inner:
            return None
        # payload = legacy miss body (Cursor reads envelope.payload)
        return make_envelope(
            event_type=self.event_type,
            race_id=ctx["race_id"],
            race_date=ctx["race_date"],
            payload=inner,
            model_version=inner.get("model_version"),
            timestamp=inner.get("timestamp"),
        )
