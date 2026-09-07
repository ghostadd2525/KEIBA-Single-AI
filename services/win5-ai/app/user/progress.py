# -*- coding: utf-8 -*-
"""User progress: points, levels, feature unlocks (no Prediction Engine)."""
from __future__ import annotations

from typing import Any

POINTS_PER_YEN = 1000  # floor(profit / 1000)
POINTS_PER_LEVEL = 100  # Lv1: 0-99, Lv2: 100-199, ...

UNLOCKS: dict[str, int] = {
    "race_predict": 1,
    "strategy": 1,
    "user_results": 1,
    "ai_stats_detail": 10,
    "win5_intro": 20,
    "win5_history": 50,
    "win5_predict": 100,
}


def points_from_profit(profit: int) -> int:
    """Award points only from positive profit; floor(profit/1000)."""
    try:
        p = int(profit)
    except (TypeError, ValueError):
        return 0
    if p <= 0:
        return 0
    return p // POINTS_PER_YEN


def level_from_points(points: int) -> int:
    try:
        pts = max(0, int(points))
    except (TypeError, ValueError):
        pts = 0
    return (pts // POINTS_PER_LEVEL) + 1


def points_to_next_level(points: int) -> int:
    try:
        pts = max(0, int(points))
    except (TypeError, ValueError):
        pts = 0
    return POINTS_PER_LEVEL - (pts % POINTS_PER_LEVEL)


def unlocks_for_level(level: int) -> dict[str, bool]:
    try:
        lv = max(1, int(level))
    except (TypeError, ValueError):
        lv = 1
    return {key: lv >= need for key, need in UNLOCKS.items()}


def progress_payload(row: dict[str, Any] | None) -> dict[str, Any]:
    pts = int((row or {}).get("cumulative_points") or 0)
    profit = int((row or {}).get("cumulative_profit") or 0)
    level = level_from_points(pts)
    return {
        "cumulative_points": pts,
        "cumulative_profit": profit,
        "level": level,
        "points_to_next_level": points_to_next_level(pts),
        "unlocks": unlocks_for_level(level),
        "unlock_thresholds": dict(UNLOCKS),
    }
