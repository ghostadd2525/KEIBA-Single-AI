# -*- coding: utf-8 -*-
"""Bundle vs result evaluation helpers (Production stats)."""
from __future__ import annotations

from typing import Any


def normalize_going(value: Any) -> str:
    s = str(value or "").strip()
    if not s:
        return ""
    if s in {"稍", "稍重"}:
        return "稍重"
    if s in {"良", "重", "不良"}:
        return s
    return s


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


DISTANCE_BUCKETS_UI = (1200, 1600, 2000, 2400)


def surface_ja(surface: Any) -> str:
    s = str(surface or "").lower()
    if "turf" in s or s == "芝":
        return "芝"
    if "dirt" in s or s in {"ダ", "ダート"}:
        return "ダ"
    return "芝"


def distance_bucket_ui(distance: Any) -> int:
    try:
        d = int(distance)
    except (TypeError, ValueError):
        return 1600
    if d <= 0:
        return 1600
    best = DISTANCE_BUCKETS_UI[0]
    diff = abs(d - best)
    for bucket in DISTANCE_BUCKETS_UI[1:]:
        nd = abs(d - bucket)
        if nd < diff:
            diff = nd
            best = bucket
    return best


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
