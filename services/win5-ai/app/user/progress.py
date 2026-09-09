# -*- coding: utf-8 -*-
"""User progress: points, levels, feature unlocks (no Prediction Engine)."""
from __future__ import annotations

from typing import Any

POINTS_PER_YEN = 1000  # floor(profit / 1000) — legacy non-Challenge settle only
POINTS_PER_LEVEL = 100  # Lv1: 0-99, Lv2: 100-199, ...
LEVEL_MIN = 1
LEVEL_MAX = 50
LEVEL_50_THRESHOLD = 4900
CHALLENGE_POINT_THRESHOLD_YEN = 1000
CHALLENGE_POINT_AWARD = 100
CHALLENGE_POINT_RULE_VERSION = "challenge-point-v7.5"

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
    """Award points only from positive profit; floor(profit/1000). Legacy non-Challenge settle."""
    try:
        p = int(profit)
    except (TypeError, ValueError):
        return 0
    if p <= 0:
        return 0
    return p // POINTS_PER_YEN


def challenge_points_from_settled_profit(profit: int) -> int:
    """Challenge V7.5: +100 when settled profit >= ¥1,000; otherwise 0 (not proportional)."""
    try:
        p = int(profit)
    except (TypeError, ValueError):
        return 0
    if p < CHALLENGE_POINT_THRESHOLD_YEN:
        return 0
    return CHALLENGE_POINT_AWARD


def level_from_points(points: int) -> int:
    try:
        pts = max(0, int(points))
    except (TypeError, ValueError):
        pts = 0
    return min(LEVEL_MAX, (pts // POINTS_PER_LEVEL) + 1)


def points_to_next_level(points: int) -> int:
    try:
        pts = max(0, int(points))
    except (TypeError, ValueError):
        pts = 0
    if level_from_points(pts) >= LEVEL_MAX:
        return 0
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
    at_max = level >= LEVEL_MAX
    return {
        "cumulative_points": pts,
        "cumulative_profit": profit,
        "level": level,
        "points_to_next_level": points_to_next_level(pts),
        "at_max": at_max,
        "level_min": LEVEL_MIN,
        "level_max": LEVEL_MAX,
        "unlocks": unlocks_for_level(level),
        "unlock_thresholds": dict(UNLOCKS),
    }
