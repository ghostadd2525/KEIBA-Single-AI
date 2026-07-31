# -*- coding: utf-8 -*-
"""Version 3 Lab — Feature Generator (P2 Representation).

Generates F-V3-* tabular features + a fixed embedding from race context and
runner fields. No result / payout / finish columns.

Candidate IDs follow docs/releases/v3-accuracy-strategy.md §5 (subset for P2).
"""
from __future__ import annotations

import math
from typing import Any

FEATURE_KEYS: tuple[str, ...] = (
    "F_V3_01_field_size_norm",
    "F_V3_10_decayed_form_proxy",
    "F_V3_11_rel_rank_stability",
    "F_V3_12_style_cluster_dist",
    "F_V3_20_log_odds_residual",
    "F_V3_21_popularity_crowd",
    "F_V3_rank_inv",
    "F_V3_win_prob",
)

REPRESENTATION_ID = "v3-rep-p2-v1"
CONTRACT_ID = "v3-lab-representation/2.0"


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


def _field_size(context: dict[str, Any], runners: list[dict[str, Any]]) -> int:
    fs = _i(context.get("field_size"), 0)
    if fs > 0:
        return fs
    return max(len(runners), 1)


def _rank(runner: dict[str, Any]) -> int:
    return _i(runner.get("model_rank", runner.get("rank")), 999)


def _style_code(runner: dict[str, Any], n: int) -> float:
    style = str(runner.get("running_style") or runner.get("style") or "").strip().lower()
    mapped = {"nige": 0.0, "senko": 0.33, "sashi": 0.66, "oikomi": 1.0}.get(style)
    if mapped is not None:
        return mapped
    rk = _rank(runner)
    return min(1.0, max(0.0, (rk - 1) / max(n - 1, 1)))


def generate_runner_features(
    context: dict[str, Any],
    runner: dict[str, Any],
    *,
    field_size: int,
    ranks: list[int],
    popularities: list[float],
    style_mean: float,
) -> dict[str, float]:
    """Build F-V3 feature map for one runner (anonymous inputs only)."""
    n = max(field_size, 1)
    rk = _rank(runner)
    win_prob = _f(runner.get("win_prob"), 0.0)
    history_score = _f(runner.get("history_score"), win_prob)
    history_count = _f(runner.get("history_count"), 0.0)
    odds = _f(runner.get("odds", runner.get("odds_today")), 0.0)
    pop = _f(runner.get("popularity"), 0.0)

    f01 = min(1.0, max(0.0, (n - 8) / 10.0))

    sample = min(1.0, history_count / 10.0) if history_count > 0 else 0.35
    f10 = history_score * (0.5 + 0.5 * sample)

    if ranks:
        sorted_r = sorted(ranks)
        mid = sorted_r[len(sorted_r) // 2]
        f11 = 1.0 - min(1.0, abs(rk - mid) / max(n, 1))
    else:
        f11 = 0.5

    style_code = _style_code(runner, n)
    f12 = abs(style_code - style_mean)

    if odds > 1.0:
        implied = 1.0 / odds
        model = max(win_prob, 1e-6)
        f20 = math.log(max(implied, 1e-6)) - math.log(model)
    else:
        f20 = 0.0

    if popularities and pop > 0:
        band = sum(1 for p in popularities if abs(p - pop) <= 1.5)
        f21 = band / max(n, 1)
    else:
        f21 = 0.0

    return {
        "F_V3_01_field_size_norm": float(f01),
        "F_V3_10_decayed_form_proxy": float(f10),
        "F_V3_11_rel_rank_stability": float(f11),
        "F_V3_12_style_cluster_dist": float(f12),
        "F_V3_20_log_odds_residual": float(f20),
        "F_V3_21_popularity_crowd": float(f21),
        "F_V3_rank_inv": float(1.0 / max(rk, 1)),
        "F_V3_win_prob": float(win_prob),
    }


def features_to_embedding(features: dict[str, float]) -> list[float]:
    return [float(features.get(k, 0.0)) for k in FEATURE_KEYS]


def generate_race_features(
    context: dict[str, Any],
    runners: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Attach `features` + `embedding` to each runner copy."""
    field_size = _field_size(context, runners)
    ranks = [_rank(r) for r in runners]
    popularities = [_f(r.get("popularity"), 0.0) for r in runners]
    n = max(field_size, 1)
    style_mean = (
        sum(_style_code(r, n) for r in runners) / len(runners) if runners else 0.5
    )

    out: list[dict[str, Any]] = []
    for runner in runners:
        row = dict(runner)
        feats = generate_runner_features(
            context,
            runner,
            field_size=field_size,
            ranks=ranks,
            popularities=popularities,
            style_mean=style_mean,
        )
        prev = row.get("features") if isinstance(row.get("features"), dict) else {}
        row["features"] = {**prev, **feats}
        row["embedding"] = features_to_embedding(feats)
        out.append(row)

    journal = {
        "generator": "v3_feature_generator",
        "representation_id": REPRESENTATION_ID,
        "contract": CONTRACT_ID,
        "feature_keys": list(FEATURE_KEYS),
        "embedding_dim": len(FEATURE_KEYS),
        "field_size": field_size,
        "runner_count": len(out),
        "leak_inputs": False,
    }
    return out, journal


__all__ = [
    "FEATURE_KEYS",
    "REPRESENTATION_ID",
    "CONTRACT_ID",
    "generate_runner_features",
    "features_to_embedding",
    "generate_race_features",
]
