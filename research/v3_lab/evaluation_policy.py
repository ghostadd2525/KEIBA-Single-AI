# -*- coding: utf-8 -*-
"""Version 3 Lab — Evaluation Policy (A-01 / D1 Recalibrator).

Feature-invariant recalibration of ranking scores (not softmax temperature).
Uses anonymous signals only: model_rank, win_prob, odds. Optional F-V3
features if already attached by Representation (does not require Representation ON).

No result / payout / finish columns as inputs.
"""
from __future__ import annotations

import math
from typing import Any

POLICY_ID = "D1-Recalibrator"
EVALUATION_ID = "v3-eval-a01-d1"
CONTRACT_ID = "v3-lab-evaluation/2.0"
CALIBRATION_ID = "v3-d1-isotonic-proxy-v1"


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


def _feat(runner: dict[str, Any], key: str, default: float = 0.0) -> float:
    feats = runner.get("features") if isinstance(runner.get("features"), dict) else {}
    if key in feats:
        return _f(feats.get(key), default)
    return default


def d1_score(runner: dict[str, Any]) -> float:
    """Calibrated ranking score (higher = better).

    Proxy for validation-gated isotonic recalibration:
      - preserve strong favorites (high win_prob + top rank)
      - boost underpriced runners via win_prob vs implied odds
    """
    rank = max(_i(runner.get("model_rank", runner.get("rank")), 999), 1)
    win_prob = max(0.0, min(1.0, _f(runner.get("win_prob"), 0.0)))
    odds = _f(runner.get("odds", runner.get("odds_today")), 0.0)
    implied = (1.0 / odds) if odds > 1.0 else 0.0

    rank_prior = 1.0 / rank
    form = _feat(runner, "F_V3_10_decayed_form_proxy", win_prob)
    underpriced = max(0.0, win_prob - implied) if implied > 0 else 0.0

    score = (
        0.50 * win_prob
        + 0.22 * rank_prior
        + 0.18 * form
        + 0.10 * underpriced
    )
    return float(score) - 1e-6 * rank


def rank_with_d1(
    context: dict[str, Any],
    runners: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[float], dict[str, Any]]:
    rows = [dict(r) for r in (runners or [])]
    scored: list[tuple[float, dict[str, Any]]] = []
    for r in rows:
        s = d1_score(r)
        r["eval_score"] = s
        r["d1_score"] = s
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
        "rank_method": "d1_recalibrator",
        "calibration_id": CALIBRATION_ID,
        "runner_count": len(ranked),
        "leak_inputs": False,
        "feature_invariant": True,
        "temperature_knob": False,
    }
    return ranked, win_probs, journal


def rank_identity(runners: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[float], dict[str, Any]]:
    ranked = [dict(r) for r in (runners or [])]
    ranked.sort(key=lambda r: _i(r.get("model_rank"), 999))
    win_probs = [_f(r.get("win_prob"), 0.0) for r in ranked]
    journal = {
        "policy_id": "identity",
        "evaluation_id": "identity",
        "contract": CONTRACT_ID,
        "model_id": "identity",
        "rank_method": "model_rank_passthrough",
        "calibration_id": None,
        "runner_count": len(ranked),
        "leak_inputs": False,
    }
    return ranked, win_probs, journal


__all__ = [
    "POLICY_ID",
    "EVALUATION_ID",
    "CONTRACT_ID",
    "CALIBRATION_ID",
    "d1_score",
    "rank_with_d1",
    "rank_identity",
]
