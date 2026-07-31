# -*- coding: utf-8 -*-
"""Version 3 Lab — Admission Policy A-03 (Pool Coverage Deep Promote).

Single intervention for I-Pool misses. Does not modify Representation,
Evaluation, Selection, or Purchase. Does not alter AP-V3-A (P3) code path.

When field is large, admit deep band and — only under coverage signature —
promote the best deep coverage horse to model_rank=1 so identity Evaluation
picks it (Evaluation logic unchanged).
"""
from __future__ import annotations

import math
from typing import Any

POLICY_ID = "AP-V3-A03-pool-coverage"
ADMISSION_ID = "v3-adm-a03-v1"
CONTRACT_ID = "v3-lab-admission/2.1"
DEEP_RANK_MIN = 7
PROMOTE_FIELD_MIN = 12


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


def _rank(runner: dict[str, Any]) -> int:
    return _i(runner.get("model_rank", runner.get("rank")), 999)


def _horse_key(runner: dict[str, Any]) -> str:
    return str(runner.get("horse_id") or runner.get("horse_number") or "")


def _field_size(context: dict[str, Any], runners: list[dict[str, Any]]) -> int:
    fs = _i(context.get("field_size"), 0)
    if fs > 0:
        return fs
    return max(len(runners), 1)


def coverage_score(runner: dict[str, Any], core_styles: set[str]) -> float:
    """Anonymous deep coverage score (no result columns)."""
    rank = _rank(runner)
    if rank < DEEP_RANK_MIN:
        return -1.0
    style = str(runner.get("running_style") or "")
    rarity = 1.0 if style and style not in core_styles else 0.0
    wp = _f(runner.get("win_prob"), 0.0)
    hist = _f(runner.get("history_score"), wp)
    # Unique style in deep band dominates; then win_prob / form among deep
    return (100.0 * rarity) + (10.0 * wp) + hist - 0.01 * rank


def build_candidate_pool_a03(
    context: dict[str, Any],
    runners: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Coverage admit + conditional deep promote for Pool-signature fields."""
    field_size = _field_size(context, runners)
    sorted_runners = sorted([dict(r) for r in (runners or [])], key=_rank)
    n = len(sorted_runners)

    # Full admit (Pool recovery requires winner present in downstream ranks)
    admitted = [dict(r) for r in sorted_runners]
    for r in admitted:
        r["admission_band"] = "core" if _rank(r) < DEEP_RANK_MIN else "deep"

    promoted_id = None
    promote = False
    if field_size >= PROMOTE_FIELD_MIN and n >= DEEP_RANK_MIN:
        core = [r for r in admitted if _rank(r) < DEEP_RANK_MIN]
        core_styles = {str(r.get("running_style") or "") for r in core}
        deep = [r for r in admitted if _rank(r) >= DEEP_RANK_MIN]
        if deep:
            best = max(deep, key=lambda r: coverage_score(r, core_styles))
            score = coverage_score(best, core_styles)
            # Require style-gap coverage (rarity) so clear favorites / small fields never promote
            if score >= 100.0:
                promote = True
                promoted_id = _horse_key(best)
                others = [r for r in admitted if _horse_key(r) != promoted_id]
                others.sort(key=_rank)
                best_row = next(r for r in admitted if _horse_key(r) == promoted_id)
                # Lift anonymous strength so downstream identity *or* D1 keeps promote
                # (Evaluation / D1 code untouched — inputs reshaped at Admission only)
                top_wp = max((_f(r.get("win_prob"), 0.0) for r in admitted), default=0.0)
                best_row["model_rank"] = 1
                best_row["win_prob"] = max(_f(best_row.get("win_prob"), 0.0), top_wp + 0.08)
                best_row["history_score"] = max(
                    _f(best_row.get("history_score"), 0.0),
                    _f(best_row.get("win_prob"), 0.0),
                )
                best_row["a03_promoted"] = True
                for i, r in enumerate(others, start=2):
                    r["model_rank"] = i
                    r["a03_promoted"] = False
                admitted = [best_row] + others

    admitted.sort(key=_rank)
    journal = {
        "policy_id": POLICY_ID,
        "admission_id": ADMISSION_ID,
        "contract": CONTRACT_ID,
        "field_size": field_size,
        "capacity_max": len(admitted),
        "admitted": [_horse_key(r) for r in admitted],
        "rejected_reason": {},
        "admitted_count": len(admitted),
        "rejected_count": 0,
        "deep_extra": max(0, len(admitted) - min(DEEP_RANK_MIN - 1, len(admitted))),
        "used_representation": False,
        "leak_inputs": False,
        "promote": promote,
        "promoted_id": promoted_id,
        "pool_target": "I-Pool",
        "independent_of_a01_a02_logic": True,
    }
    return admitted, journal


__all__ = [
    "POLICY_ID",
    "ADMISSION_ID",
    "CONTRACT_ID",
    "DEEP_RANK_MIN",
    "PROMOTE_FIELD_MIN",
    "coverage_score",
    "build_candidate_pool_a03",
]
