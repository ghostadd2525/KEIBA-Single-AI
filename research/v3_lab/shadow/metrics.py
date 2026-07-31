# -*- coding: utf-8 -*-
"""A-05 Shadow Metrics + Acceptance Criteria evaluation."""
from __future__ import annotations

from typing import Any

from .comparator import build_comparator_report
from .config import ShadowSettings, load_shadow_settings


def aggregate_shadow_metrics(
    records: list[dict[str, Any]],
    *,
    settings: ShadowSettings | None = None,
) -> dict[str, Any]:
    settings = settings or load_shadow_settings()
    stake = float(settings.stake_yen)
    n = len(records)
    labeled = [r for r in records if r.get("control_hit") is not None and r.get("shadow_hit") is not None]
    ok_n = sum(1 for r in records if r.get("shadow_ok"))
    err_n = n - ok_n

    control_hit = sum(1 for r in labeled if r.get("control_hit"))
    shadow_hit = sum(1 for r in labeled if r.get("shadow_hit"))
    improved = sum(1 for r in labeled if (not r.get("control_hit")) and r.get("shadow_hit"))
    worsened = sum(1 for r in labeled if r.get("control_hit") and (not r.get("shadow_hit")))
    wr1 = sum(
        1
        for r in labeled
        if r.get("control_hit")
        and (not r.get("shadow_hit"))
        and int(r.get("winner_rank") or 0) == 1
    )
    pick_churn = sum(1 for r in records if r.get("pick_changed"))
    promote_n = sum(1 for r in records if r.get("a05_promote"))
    favsafe_block_n = sum(1 for r in records if r.get("favsafe_blocked"))

    # Virtual Purchase / ROI (flat stake; no real purchase)
    c_stake = stake * len(labeled)
    s_stake = stake * len(labeled)
    c_ret = 0.0
    s_ret = 0.0
    for r in labeled:
        if r.get("control_hit"):
            c_ret += stake * float(r.get("control_odds") or 0.0)
        if r.get("shadow_hit"):
            s_ret += stake * float(r.get("shadow_odds") or 0.0)
    c_roi = ((c_ret - c_stake) / c_stake) if c_stake else 0.0
    s_roi = ((s_ret - s_stake) / s_stake) if s_stake else 0.0

    control_purchase = sum(
        1 for r in labeled if r.get("control_hit") and r.get("purchase_eligible", True)
    )
    shadow_purchase = sum(
        1 for r in labeled if r.get("shadow_hit") and r.get("purchase_eligible", True)
    )

    elapsed = [float(r.get("elapsed_ms") or 0.0) for r in records]
    elapsed_sorted = sorted(elapsed)
    p95 = elapsed_sorted[int(0.95 * (len(elapsed_sorted) - 1))] if elapsed_sorted else 0.0

    return {
        "n": n,
        "labeled_n": len(labeled),
        "shadow_ok_n": ok_n,
        "shadow_error_n": err_n,
        "shadow_error_rate": (err_n / n) if n else 0.0,
        "control_hit": control_hit,
        "shadow_hit": shadow_hit,
        "delta_hit": shadow_hit - control_hit,
        "purchase_control_virtual": control_purchase,
        "purchase_shadow_virtual": shadow_purchase,
        "delta_purchase_virtual": shadow_purchase - control_purchase,
        "roi_control_virtual": round(c_roi, 4),
        "roi_shadow_virtual": round(s_roi, 4),
        "delta_roi_virtual": round(s_roi - c_roi, 4),
        "improved": improved,
        "worsened": worsened,
        "worsened_winner_rank1": wr1,
        "churn_hit": worsened,
        "pick_churn": pick_churn,
        "promote_n": promote_n,
        "promote_rate": (promote_n / n) if n else 0.0,
        "favsafe_block_n": favsafe_block_n,
        "favsafe_block_rate": (favsafe_block_n / n) if n else 0.0,
        "elapsed_ms_p95": round(p95, 3),
        "stake_yen": stake,
        "purchase_executed_any": any(bool(r.get("purchase_executed")) for r in records),
        "phase": settings.phase,
    }


def evaluate_acceptance(
    metrics: dict[str, Any],
    *,
    settings: ShadowSettings | None = None,
    window_days: int | None = None,
    production_a05_default_off: bool = True,
    a03_co_enabled: bool = False,
    input_mismatch_rate: float = 0.0,
    control_path_healthy: bool = True,
) -> dict[str, Any]:
    """Evaluate Shadow Acceptance Criteria (measurement capability).

    Does not start a live evaluation window; callers supply aggregated metrics.
    """
    settings = settings or load_shadow_settings()
    labeled_n = int(metrics.get("labeled_n") or 0)
    days_ok = (window_days is not None and window_days >= settings.min_window_days) or (
        labeled_n >= settings.min_labeled_races
    )
    checks = {
        "H1_worsened_winner_rank1_0": int(metrics.get("worsened_winner_rank1") or 0) == 0,
        "H2_delta_hit_gt_0": int(metrics.get("delta_hit") or 0) > 0,
        "H3_churn_hit_0": int(metrics.get("churn_hit") or 0) == 0,
        "H4_window_sufficient": days_ok,
        "H5_input_match": float(input_mismatch_rate) <= settings.max_input_mismatch_rate,
        "H6_no_a03_co": not a03_co_enabled,
        "H7_production_a05_default_off": production_a05_default_off,
        "H8_control_path_healthy": control_path_healthy,
        "H9_shadow_error_rate": float(metrics.get("shadow_error_rate") or 0.0)
        <= settings.max_shadow_error_rate,
        "purchase_not_executed": not bool(metrics.get("purchase_executed_any")),
    }
    soft = {
        "S1_improved_ge_1": int(metrics.get("improved") or 0) >= 1,
        "S2_promote_rate_band": float(metrics.get("promote_rate") or 0.0)
        <= settings.promote_rate_warn_max,
        "S3_roi_shadow_ge_control": float(metrics.get("roi_shadow_virtual") or 0.0)
        >= float(metrics.get("roi_control_virtual") or 0.0),
    }
    hard_pass = all(checks.values())
    return {
        "hard_checks": checks,
        "soft_checks": soft,
        "hard_pass": hard_pass,
        "decision": "PASS" if hard_pass else "FAIL",
        "note": "Acceptance measurement only; live Shadow evaluation window not started",
    }


def build_metrics_bundle(
    records: list[dict[str, Any]],
    *,
    settings: ShadowSettings | None = None,
    **acceptance_kwargs: Any,
) -> dict[str, Any]:
    settings = settings or load_shadow_settings()
    metrics = aggregate_shadow_metrics(records, settings=settings)
    comparator = build_comparator_report(records)
    acceptance = evaluate_acceptance(metrics, settings=settings, **acceptance_kwargs)
    return {
        "metrics": metrics,
        "comparator": {
            k: v
            for k, v in comparator.items()
            if k not in {"all_diffs"}  # keep summary compact; full in race_diff artifact
        },
        "acceptance": acceptance,
        "settings": settings.to_dict(),
    }


__all__ = [
    "aggregate_shadow_metrics",
    "evaluate_acceptance",
    "build_metrics_bundle",
]
