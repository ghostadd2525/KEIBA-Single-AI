# -*- coding: utf-8 -*-
"""Version 3 Lab — Admission Policy A-05 (Favorite-Safe Coverage).

Independent of A-03 (frozen). Conditional hard promote only when:
  - large field + deep candidate
  - composite coverage (style rarity AND relative history strength)
  - Favorite-Safe gates pass (no clear short-priced / wide-margin top)

Does not modify Representation, Evaluation, Selection, or Purchase.
Does not alter admission_policy_a03.py.
"""
from __future__ import annotations

import math
from typing import Any

POLICY_ID = "AP-V3-A05-favorite-safe-coverage"
ADMISSION_ID = "v3-adm-a05-v1"
CONTRACT_ID = "v3-lab-admission/2.2"
DEEP_RANK_MIN = 7
PROMOTE_FIELD_MIN = 12
# FavSafe / coverage thresholds (calibrated on Offline A-03 churn; Lab Hit279 not required)
MARGIN_MIN = 0.04  # ban promote when top margin >= this
TOP_ODDS_MIN = 4.5  # ban promote when top odds < this (short favorite)
CAND_RANK_MAX = 11
TOP_WP_FLOOR = 0.20  # ban promote when top win_prob >= this


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


def composite_coverage(
    runner: dict[str, Any],
    core_styles: set[str],
    deep_hist_median: float,
) -> tuple[float, dict[str, Any]]:
    """Composite coverage: rarity required; relative hist strength required."""
    rank = _rank(runner)
    if rank < DEEP_RANK_MIN:
        return -1.0, {"deep_band": False}
    style = str(runner.get("running_style") or "")
    rarity = bool(style and style not in core_styles)
    wp = _f(runner.get("win_prob"), 0.0)
    hist = _f(runner.get("history_score"), wp)
    hist_ok = hist >= deep_hist_median
    rank_ok = rank <= CAND_RANK_MAX
    components = {
        "deep_band": True,
        "style_rarity": rarity,
        "relative_strength_ok": hist_ok,
        "rank_ok": rank_ok,
        "hist": hist,
        "deep_hist_median": deep_hist_median,
        "not_only_rarity": hist_ok and rank_ok,
    }
    if not (rarity and hist_ok and rank_ok):
        return -1.0, components
    score = (100.0 * float(rarity)) + (10.0 * wp) + hist - 0.01 * rank
    return score, components


def favsafe_check(
    top: dict[str, Any],
    second: dict[str, Any] | None,
    cand: dict[str, Any],
) -> tuple[bool, str, dict[str, Any]]:
    """Return (pass, reason, diagnostics). Pass ⇒ promote allowed."""
    top_wp = _f(top.get("win_prob"), 0.0)
    second_wp = _f(second.get("win_prob"), 0.0) if second else 0.0
    margin = top_wp - second_wp
    top_odds = _f(top.get("odds"), 0.0)
    diag = {
        "top_wp": top_wp,
        "second_wp": second_wp,
        "margin": margin,
        "top_odds": top_odds,
        "cand_rank": _rank(cand),
    }
    # FS-1 Clear Favorite (wide margin)
    if margin >= MARGIN_MIN:
        return False, "fs1_clear_margin", diag
    # FS-3 strong / short favorite (odds proxy + wp floor)
    if top_odds > 0.0 and top_odds < TOP_ODDS_MIN:
        return False, "fs3_short_odds", diag
    if top_wp >= TOP_WP_FLOOR:
        return False, "fs3_strong_top_wp", diag
    # FS-4: cand must still clear composite (checked by caller); rank bound
    if _rank(cand) > CAND_RANK_MAX:
        return False, "fs4_cand_too_deep", diag
    return True, "favsafe_pass", diag


def build_candidate_pool_a05(
    context: dict[str, Any],
    runners: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Favorite-safe conditional deep promote."""
    field_size = _field_size(context, runners)
    sorted_runners = sorted([dict(r) for r in (runners or [])], key=_rank)
    n = len(sorted_runners)

    admitted = [dict(r) for r in sorted_runners]
    for r in admitted:
        r["admission_band"] = "core" if _rank(r) < DEEP_RANK_MIN else "deep"
        r["a05_promoted"] = False

    promoted_id = None
    promote = False
    favsafe_blocked = False
    favsafe_reason = ""
    coverage_components: dict[str, Any] = {}
    top_margin = 0.0

    if field_size >= PROMOTE_FIELD_MIN and n >= DEEP_RANK_MIN:
        core = [r for r in admitted if _rank(r) < DEEP_RANK_MIN]
        deep = [r for r in admitted if _rank(r) >= DEEP_RANK_MIN]
        core_styles = {str(r.get("running_style") or "") for r in core}
        deep_hists = [_f(r.get("history_score"), _f(r.get("win_prob"), 0.0)) for r in deep]
        deep_med = sorted(deep_hists)[len(deep_hists) // 2] if deep_hists else 0.0

        if deep:
            scored: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
            for r in deep:
                sc, comp = composite_coverage(r, core_styles, deep_med)
                scored.append((sc, r, comp))
            best_sc, best, coverage_components = max(scored, key=lambda x: x[0])
            top = next(r for r in admitted if _rank(r) == 1) if any(_rank(r) == 1 for r in admitted) else admitted[0]
            others_by_rank = sorted([r for r in admitted if _horse_key(r) != _horse_key(top)], key=_rank)
            second = others_by_rank[0] if others_by_rank else None
            top_margin = _f(top.get("win_prob"), 0.0) - (
                _f(second.get("win_prob"), 0.0) if second else 0.0
            )

            if best_sc < 100.0:
                favsafe_blocked = True
                favsafe_reason = "coverage_fail"
            else:
                ok, reason, fs_diag = favsafe_check(top, second, best)
                coverage_components = {**coverage_components, **fs_diag}
                if not ok:
                    favsafe_blocked = True
                    favsafe_reason = reason
                else:
                    # Conditional Hard Promote
                    promote = True
                    promoted_id = _horse_key(best)
                    rest = [r for r in admitted if _horse_key(r) != promoted_id]
                    rest.sort(key=_rank)
                    best_row = next(r for r in admitted if _horse_key(r) == promoted_id)
                    top_wp = max((_f(r.get("win_prob"), 0.0) for r in admitted), default=0.0)
                    best_row["model_rank"] = 1
                    best_row["win_prob"] = max(_f(best_row.get("win_prob"), 0.0), top_wp + 0.08)
                    best_row["history_score"] = max(
                        _f(best_row.get("history_score"), 0.0),
                        _f(best_row.get("win_prob"), 0.0),
                    )
                    best_row["a05_promoted"] = True
                    for i, r in enumerate(rest, start=2):
                        r["model_rank"] = i
                        r["a05_promoted"] = False
                    admitted = [best_row] + rest
                    favsafe_reason = "favsafe_pass"

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
        "favsafe_blocked": favsafe_blocked,
        "favsafe_reason": favsafe_reason,
        "coverage_components": coverage_components,
        "top_margin": top_margin,
        "pool_target": "I-Pool-favorite-safe",
        "independent_of_a03": True,
        "thresholds": {
            "PROMOTE_FIELD_MIN": PROMOTE_FIELD_MIN,
            "DEEP_RANK_MIN": DEEP_RANK_MIN,
            "MARGIN_MIN": MARGIN_MIN,
            "TOP_ODDS_MIN": TOP_ODDS_MIN,
            "CAND_RANK_MAX": CAND_RANK_MAX,
            "TOP_WP_FLOOR": TOP_WP_FLOOR,
        },
    }
    return admitted, journal


__all__ = [
    "POLICY_ID",
    "ADMISSION_ID",
    "CONTRACT_ID",
    "DEEP_RANK_MIN",
    "PROMOTE_FIELD_MIN",
    "MARGIN_MIN",
    "TOP_ODDS_MIN",
    "CAND_RANK_MAX",
    "TOP_WP_FLOOR",
    "composite_coverage",
    "favsafe_check",
    "build_candidate_pool_a05",
]
