# -*- coding: utf-8 -*-
"""PC-4 ConfidenceBuilder — calibrated projection from win_prob."""
from __future__ import annotations

import math
import os
from typing import Any


def _entropy(probs: list[float]) -> float:
    if not probs:
        return 0.0
    total = 0.0
    for p in probs:
        p = min(max(float(p), 1e-12), 1.0)
        total -= p * math.log(p)
    return total


def _confidence_band(overall: float) -> str:
    if overall >= 0.35:
        return "high"
    if overall >= 0.18:
        return "medium"
    return "low"


class ConfidenceBuilder:
    """Build per-horse and race-level confidence with uncertainty factors."""

    def __init__(self) -> None:
        self.temperature = float(os.environ.get("CORE_CONFIDENCE_TEMPERATURE") or "1.0")

    def build_confidence(
        self,
        score_bundle: dict[str, Any],
        race_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        meta = dict(race_meta or {})
        ids = list(score_bundle.get("candidate_ids", []))
        probs = score_bundle["win_prob"]
        frame = score_bundle["_source_frame"]
        raw_probs = [float(probs.loc[frame.index[pos]]) for pos in range(len(ids))]
        scaled = self._apply_temperature(raw_probs)
        per_horse = {candidate_id: scaled[pos] for pos, candidate_id in enumerate(ids)}

        ordered = sorted(scaled, reverse=True)
        top1 = ordered[0] if ordered else 0.0
        top2 = ordered[1] if len(ordered) > 1 else 0.0
        gap12 = top1 - top2
        top2_sum = top1 + top2
        field_size = int(meta.get("field_size") or len(ids))
        ent = _entropy(scaled)
        max_ent = math.log(max(len(scaled), 1)) or 1.0
        uncertainty = min(1.0, ent / max_ent)

        gap_factor = min(1.0, max(0.0, gap12 / max(top1, 1e-6)))
        spread_factor = 1.0 - uncertainty
        overall = top1 * (0.55 + 0.25 * gap_factor + 0.20 * spread_factor)
        overall = min(max(overall, 0.0), 1.0)

        meta.update(
            {
                "top1_prob": top1,
                "top2_prob": top2,
                "gap12": round(gap12, 6),
                "top2_sum": round(top2_sum, 6),
                "field_size": field_size,
                "entropy": round(ent, 6),
                "uncertainty": round(uncertainty, 6),
            }
        )
        factors = [
            f"gap12={meta['gap12']}",
            f"top2_sum={meta['top2_sum']}",
            f"field_size={field_size}",
            f"entropy={meta['entropy']}",
            f"uncertainty={meta['uncertainty']}",
        ]

        return {
            "race_id": str(score_bundle.get("race_id", "")),
            "overall": float(overall),
            "band": _confidence_band(overall),
            "per_horse": per_horse,
            "factors": factors,
            "meta": meta,
        }

    def _apply_temperature(self, probs: list[float]) -> list[float]:
        if self.temperature == 1.0 or not probs:
            return probs
        t = max(self.temperature, 1e-6)
        powered = [max(p, 1e-12) ** (1.0 / t) for p in probs]
        total = sum(powered) or 1.0
        return [p / total for p in powered]


__all__ = ["ConfidenceBuilder"]
