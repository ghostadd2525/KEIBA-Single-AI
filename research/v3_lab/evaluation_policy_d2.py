# -*- coding: utf-8 -*-
"""Version 3 Lab — Evaluation Policy A-02 / D2 Listwise Reranker.

Independent of A-01 D1 Recalibrator. Uses pairwise / listwise relative
strength across the field (rank-loss proxy). No softmax temperature.
No result / payout / finish columns as inputs.

Does not modify evaluation_policy.py (A-01).
"""
from __future__ import annotations

import math
from typing import Any

POLICY_ID = "D2-Reranker"
EVALUATION_ID = "v3-eval-a02-d2"
CONTRACT_ID = "v3-lab-evaluation/2.1"
CALIBRATION_ID = "v3-d2-listwise-pairwise-v1"


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        n = float(v)
        if not math.isfinite(n):
            return default
        return n
    except Exception:
        return default


def _i(v: Any, default: int = 0) -> int:
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default


def _hist(runner: dict[str, Any]) -> float:
    """Relative form proxy — history_score preferred, else win_prob."""
    if runner.get("history_score") is not None and runner.get("history_score") != "":
        return _f(runner.get("history_score"), 0.0)
    return _f(runner.get("win_prob"), 0.0)


def _pairwise_strength(runner: dict[str, Any], field: list[dict[str, Any]]) -> float:
    """Fraction of field beaten on (history, then win_prob) — pairwise rank proxy."""
    if len(field) <= 1:
        return 1.0
    h = _hist(runner)
    wp = _f(runner.get("win_prob"), 0.0)
    wins = 0
    for other in field:
        if other is runner:
            continue
        oh = _hist(other)
        owp = _f(other.get("win_prob"), 0.0)
        if h > oh + 1e-12:
            wins += 1
        elif abs(h - oh) <= 1e-12 and wp > owp + 1e-12:
            wins += 1
    return wins / float(len(field) - 1)


def _field_crowding(field: list[dict[str, Any]]) -> float:
    """1 when top win_probs are tight (boundary/reorder); 0 when clear favorite."""
    wps = sorted((_f(r.get("win_prob"), 0.0) for r in field), reverse=True)
    if not wps:
        return 0.0
    third = wps[2] if len(wps) >= 3 else wps[-1]
    top_gap = wps[0] - third
    return max(0.0, min(1.0, 1.0 - (top_gap / 0.15)))


def d2_score(runner: dict[str, Any], field: list[dict[str, Any]], crowding: float) -> float:
    """Listwise rerank score (higher = better).

    Clear fields → trust win_prob + model_rank (protect Control hits).
    Crowded fields → trust pairwise history strength (recover Boundary/Reorder).
    """
    rank = max(_i(runner.get("model_rank", runner.get("rank")), 999), 1)
    win_prob = max(0.0, min(1.0, _f(runner.get("win_prob"), 0.0)))
    odds = _f(runner.get("odds", runner.get("odds_today")), 0.0)
    implied = (1.0 / odds) if odds > 1.0 else 0.0
    rank_prior = 1.0 / rank
    hist = _hist(runner)
    pairwise = _pairwise_strength(runner, field)
    clear = 1.0 - crowding

    score = clear * (0.55 * win_prob + 0.35 * rank_prior + 0.10 * implied) + crowding * (
        0.70 * pairwise + 0.20 * hist + 0.10 * win_prob
    )
    return float(score) - 1e-6 * rank


def rank_with_d2(
    context: dict[str, Any],
    runners: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[float], dict[str, Any]]:
    rows = [dict(r) for r in (runners or [])]
    crowding = _field_crowding(rows)
    scored: list[tuple[float, dict[str, Any]]] = []
    for r in rows:
        s = d2_score(r, rows, crowding)
        r["eval_score"] = s
        r["d2_score"] = s
        r["d2_pairwise"] = _pairwise_strength(r, rows)
        scored.append((s, r))
    scored.sort(key=lambda t: (-t[0], _i(t[1].get("model_rank"), 999)))
    ranked = [r for _, r in scored]
    for i, r in enumerate(ranked):
        r["eval_rank"] = i + 1
    win_probs = [_f(r.get("win_prob"), 0.0) for r in ranked]
    journal = {
        "policy_id": POLICY_ID,
        "evaluation_id": EVALUATION_ID,
        "contract": CONTRACT_ID,
        "model_id": EVALUATION_ID,
        "rank_method": "d2_listwise_pairwise",
        "calibration_id": CALIBRATION_ID,
        "runner_count": len(ranked),
        "field_crowding": round(crowding, 4),
        "leak_inputs": False,
        "listwise": True,
        "temperature_knob": False,
        "independent_of_a01": True,
    }
    return ranked, win_probs, journal


__all__ = [
    "POLICY_ID",
    "EVALUATION_ID",
    "CONTRACT_ID",
    "CALIBRATION_ID",
    "d2_score",
    "rank_with_d2",
]
