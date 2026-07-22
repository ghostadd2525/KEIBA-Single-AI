# -*- coding: utf-8 -*-
"""CE-V2 Facet A — Softmax temperature calibration (Flag-gated).

Contract:
  docs/releases/v2-ce-v2-design-review.md §3.1 CE-V2-A

Rules (Must):
  - WIN5_CE_V2_ENABLED default OFF → identity
  - Facet A only (temperature). Facet C must not be implemented here.
  - No winner / G1 allowlist / result labels in trigger
  - base_model_score untouched; win_prob (+ model_rank from re-order) only
"""
from __future__ import annotations

import math
import os
from typing import Any

# Feature Flag — default OFF
WIN5_CE_V2_ENABLED = False

# CE-V2-A single AB point (sharper than T=1)
CE_V2_A_TEMP = 0.92
CE_V2_FACET = "CE-V2-A"


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def apply_win5_ce_v2_flags(enabled: bool | None = None) -> dict[str, Any]:
    """Toggle CE-V2 flag. None → read env once against current default."""
    global WIN5_CE_V2_ENABLED
    if enabled is None:
        enabled = _env_bool("WIN5_CE_V2_ENABLED", WIN5_CE_V2_ENABLED)
    WIN5_CE_V2_ENABLED = bool(enabled)
    return {
        "WIN5_CE_V2_ENABLED": WIN5_CE_V2_ENABLED,
        "facet": CE_V2_FACET,
        "temp": CE_V2_A_TEMP,
    }


def _nz(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def _empty_journal(n: int, reason: str, **extra: Any) -> dict[str, Any]:
    j: dict[str, Any] = {
        "enabled": bool(WIN5_CE_V2_ENABLED),
        "facet": CE_V2_FACET,
        "fired": False,
        "reason": reason,
        "temp": CE_V2_A_TEMP,
        "field_size": n,
        "touched_n": 0,
    }
    j.update(extra)
    return j


def temperature_rescale_probs(probs: list[float], temp: float) -> list[float]:
    """Race-level temperature rescale: softmax(log(p) / T)."""
    t = max(float(temp), 1e-6)
    n = len(probs)
    if n == 0:
        return []
    if abs(t - 1.0) < 1e-12:
        s = sum(max(0.0, float(p)) for p in probs)
        if s <= 0:
            return [1.0 / n] * n
        return [max(0.0, float(p)) / s for p in probs]

    logps: list[float] = []
    for p in probs:
        x = max(float(p), 1e-15)
        logps.append(math.log(x) / t)
    m = max(logps)
    exps = [math.exp(lp - m) for lp in logps]
    z = sum(exps) or 1.0
    return [e / z for e in exps]


def _apply_probs_to_rows(
    rows: list[dict[str, Any]],
    new_probs: list[float],
) -> None:
    """Mutate win_prob / model_rank / gap_to_top_prob in place."""
    order = sorted(range(len(rows)), key=lambda i: (-new_probs[i], i))
    rank_of = {i: r + 1 for r, i in enumerate(order)}
    top = new_probs[order[0]] if order else 0.0
    for i, row in enumerate(rows):
        p = round(float(new_probs[i]), 6)
        row["win_prob"] = p
        row["model_rank"] = int(rank_of[i])
        row["gap_to_top_prob"] = round(max(0.0, top - p), 6)


def apply_win5_ce_v2_to_race_df(race_df: Any, meta: dict[str, Any] | None = None) -> Any:
    """CE-V2-A on a race DataFrame (pre build_candidate_pool). Flag OFF → identity."""
    meta = meta if meta is not None else {}
    try:
        import pandas as pd  # noqa: F401
    except Exception:
        meta["_win5_ce_v2_journal"] = _empty_journal(0, "no_pandas")
        return race_df

    if race_df is None or getattr(race_df, "empty", True):
        meta["_win5_ce_v2_journal"] = _empty_journal(0, "empty_input")
        return race_df

    n = int(len(race_df))
    if not WIN5_CE_V2_ENABLED:
        meta["_win5_ce_v2_journal"] = _empty_journal(n, "disabled")
        return race_df

    work = race_df.copy()
    if "win_prob" not in work.columns:
        meta["_win5_ce_v2_journal"] = _empty_journal(n, "no_win_prob")
        return race_df

    probs = [_nz(v, 0.0) for v in work["win_prob"].tolist()]
    new_probs = temperature_rescale_probs(probs, CE_V2_A_TEMP)
    work["win_prob"] = [round(p, 6) for p in new_probs]

    # Re-rank by calibrated win_prob
    order = sorted(range(n), key=lambda i: (-new_probs[i], i))
    ranks = [0] * n
    for r, i in enumerate(order):
        ranks[i] = r + 1
    work["model_rank"] = ranks
    top = new_probs[order[0]] if order else 0.0
    if "gap_to_top_prob" in work.columns:
        work["gap_to_top_prob"] = [round(max(0.0, top - p), 6) for p in new_probs]

    meta["_win5_ce_v2_journal"] = {
        **_empty_journal(n, "ok"),
        "fired": True,
        "touched_n": n,
        "temp": CE_V2_A_TEMP,
    }
    return work


def apply_win5_ce_v2(
    horses: list[dict[str, Any]],
    meta: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """CE-V2-A on horse dict list. Flag OFF → identity copy."""
    meta = meta if meta is not None else {}
    horses = [dict(h) for h in (horses or [])]
    n = len(horses)
    if not WIN5_CE_V2_ENABLED:
        meta["_win5_ce_v2_journal"] = _empty_journal(n, "disabled")
        return horses
    if not horses:
        meta["_win5_ce_v2_journal"] = _empty_journal(0, "empty_input")
        return horses

    probs = [_nz(h.get("win_prob", h.get("prob", 0.0)), 0.0) for h in horses]
    new_probs = temperature_rescale_probs(probs, CE_V2_A_TEMP)
    _apply_probs_to_rows(horses, new_probs)
    meta["_win5_ce_v2_journal"] = {
        **_empty_journal(n, "ok"),
        "fired": True,
        "touched_n": n,
        "temp": CE_V2_A_TEMP,
    }
    return horses


# Env can enable without code edit (still defaults OFF when unset)
if _env_bool("WIN5_CE_V2_ENABLED", False):
    WIN5_CE_V2_ENABLED = True
