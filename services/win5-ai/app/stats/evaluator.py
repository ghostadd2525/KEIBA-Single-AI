# -*- coding: utf-8 -*-
"""Bundle vs result evaluation helpers (Production stats)."""
from __future__ import annotations

from typing import Any


def distance_bucket(distance: Any) -> str:
    try:
        d = int(distance)
    except (TypeError, ValueError):
        return "unknown"
    if d < 1400:
        return "sprint"
    if d < 1800:
        return "mile"
    if d < 2200:
        return "intermediate"
    return "long"


def evaluate_bundle_against_result(
    bundle: dict[str, Any],
    *,
    winner_horse_number: int | None,
) -> dict[str, Any]:
    runners = ((bundle.get("evaluation") or {}).get("runners")) or []
    ordered = sorted(runners, key=lambda r: int(r.get("model_rank") or 999))
    nums: list[int] = []
    for r in ordered:
        try:
            nums.append(int(r.get("horse_number")))
        except (TypeError, ValueError):
            continue
    win = winner_horse_number
    hit_at_1 = bool(win is not None and nums and nums[0] == int(win))
    hit_at_3 = bool(win is not None and int(win) in nums[:3])
    hit_at_5 = bool(win is not None and int(win) in nums[:5])
    return {
        "hit_at_1": hit_at_1,
        "hit_at_3": hit_at_3,
        "hit_at_5": hit_at_5,
        "roi": None,
    }
