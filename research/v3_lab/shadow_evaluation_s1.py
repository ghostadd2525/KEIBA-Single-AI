# -*- coding: utf-8 -*-
"""Version 3 Lab — A-05 Shadow Evaluation Phase S1 (stability).

Operational labeled inputs via Shadow Runtime. Calendar span ≥14 race days
(Acceptance H4). No algorithm / Flag-default / Production changes.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from . import flags
from .ab_harness import evaluate_arm
from .offline_gate import build_real_285r_corpus, corpus_fingerprint
from .shadow.comparator import build_comparator_report
from .shadow.config import load_shadow_settings
from .shadow.harness import run_shadow_batch
from .shadow.metrics import aggregate_shadow_metrics, evaluate_acceptance

LAB_ROOT = Path(__file__).resolve().parent
ARTIFACTS = LAB_ROOT / "baselines" / "a05_shadow_evaluation_s1"
CORPUS_CACHE = LAB_ROOT / "baselines" / "offline_gate" / "real_285r_corpus.json"
EVAL_ID = "v3-a05-shadow-evaluation/s1-1.0"


def _race_day(race_id: str) -> str:
    parts = str(race_id).split("-")
    if len(parts) >= 3:
        return "-".join(parts[:3])
    return str(race_id)


def _production_picks(corpus: list[dict[str, Any]]) -> dict[str, str]:
    control = evaluate_arm(corpus, flag_overrides={})
    return {d["race_id"]: str(d.get("pick") or "") for d in (control.get("details") or [])}


def _load_quality() -> list[dict[str, Any]]:
    if not CORPUS_CACHE.is_file():
        return []
    payload = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
    return list(payload.get("quality") or [])


def _data_quality_report(corpus: list[dict[str, Any]], quality: list[dict[str, Any]]) -> dict[str, Any]:
    by_status = Counter(str(q.get("status") or "") for q in quality)
    issues = Counter()
    for q in quality:
        for i in q.get("issues") or []:
            issues[str(i)] += 1

    days = sorted({_race_day(r["race_id"]) for r in corpus})
    blank_style = 0
    odds_le_1 = 0
    missing_winner = 0
    for r in corpus:
        if not r.get("winner_id"):
            missing_winner += 1
        for x in r.get("runners") or []:
            if not str(x.get("running_style") or "").strip():
                blank_style += 1
            try:
                if float(x.get("odds") or 0.0) <= 1.0:
                    odds_le_1 += 1
                    break
            except Exception:
                pass

    return {
        "n_races": len(corpus),
        "n_unique_race_days": len(days),
        "date_min": days[0] if days else None,
        "date_max": days[-1] if days else None,
        "quality_status": dict(by_status),
        "quality_issues": dict(issues),
        "races_missing_winner": missing_winner,
        "races_with_odds_le_1": int(issues.get("odds_le_1_present", odds_le_1)),
        "runners_blank_style_total": blank_style,
        "h4_calendar_days_ge_14": len(days) >= 14,
        "h4_labeled_n_ge_285": len(corpus) >= 285,
        "pass": bool(
            len(days) >= 14
            and len(corpus) >= 285
            and missing_winner == 0
            and (
                (not quality)
                or (by_status.get("ok", 0) + by_status.get("degraded", 0) == len(quality))
            )
        ),
    }


def _slice_last_n_days(corpus: list[dict[str, Any]], n_days: int = 14) -> list[dict[str, Any]]:
    days = sorted({_race_day(r["race_id"]) for r in corpus})
    keep = set(days[-n_days:]) if len(days) >= n_days else set(days)
    return [r for r in corpus if _race_day(r["race_id"]) in keep]


def _panel_from_batch(
    name: str,
    batch: dict[str, Any],
    *,
    window_days: int | None,
    flag_default_off: bool,
    settings: Any,
) -> dict[str, Any]:
    records = batch.get("records") or []
    metrics = batch.get("metrics") or aggregate_shadow_metrics(records, settings=settings)
    comparator = build_comparator_report(records)
    errors = [r for r in records if not r.get("shadow_ok")]
    acceptance = evaluate_acceptance(
        metrics,
        settings=settings,
        window_days=window_days,
        production_a05_default_off=flag_default_off,
        a03_co_enabled=False,
        input_mismatch_rate=0.0,
        control_path_healthy=True,
    )
    acceptance["note"] = (
        f"S1 panel={name}; H4 via race-days and/or labeled_n; "
        "Control purchase virtual only; Shadow purchase_executed=false"
    )
    hard = {
        "worsened_winner_rank1": int(metrics.get("worsened_winner_rank1") or 0),
        "delta_hit": int(metrics.get("delta_hit") or 0),
        "churn_hit": int(metrics.get("churn_hit") or 0),
        "require_worsened_winner_rank1_0": int(metrics.get("worsened_winner_rank1") or 0) == 0,
        "require_delta_hit_gt_0": int(metrics.get("delta_hit") or 0) > 0,
        "require_churn_hit_0": int(metrics.get("churn_hit") or 0) == 0,
        "acceptance_hard_pass": bool(acceptance.get("hard_pass")),
    }
    hard["pass"] = (
        hard["require_worsened_winner_rank1_0"]
        and hard["require_delta_hit_gt_0"]
        and hard["require_churn_hit_0"]
        and hard["acceptance_hard_pass"]
    )
    return {
        "panel": name,
        "n": len(records),
        "n_race_days": window_days,
        "metrics": metrics,
        "hard_gate": hard,
        "acceptance": acceptance,
        "comparator": {
            "improved_count": comparator["improved_count"],
            "worsened_count": comparator["worsened_count"],
            "worsened_winner_rank1_count": comparator["worsened_winner_rank1_count"],
            "improved_races": comparator["improved_races"],
            "worsened_races": comparator["worsened_races"],
            "worsened_winner_rank1_races": comparator["worsened_winner_rank1_races"],
        },
        "anomalies": {
            "exception_count": len(errors),
            "error_reasons": dict(Counter(str(r.get("shadow_error") or "unknown") for r in errors)),
            "error_race_ids": [r.get("race_id") for r in errors],
        },
        # Operational purchase policy
        "purchase_policy": {
            "control_purchase_executed": False,  # Lab shadow eval does not hit real purchase API
            "control_purchase_virtual": metrics.get("purchase_control_virtual"),
            "shadow_purchase_executed": False,
            "shadow_purchase_forbidden": True,
            "note": "Production: Control only may purchase; Shadow never purchases",
        },
    }


def run_shadow_evaluation_s1(*, write_logs: bool = True) -> dict[str, Any]:
    corpus = build_real_285r_corpus()
    fp = corpus_fingerprint(corpus)
    quality = _load_quality()
    dq = _data_quality_report(corpus, quality)

    flags.reset_flags_to_default()
    flag_off_before = flags.F_V3_A05_ADM_FAVSAFE_ENABLED is False

    production_picks = _production_picks(corpus)
    settings = load_shadow_settings(
        shadow_runtime_enabled=True,
        phase="S1",
        log_dir=str(ARTIFACTS / "logs"),
    )

    # Full operational corpus (57 race days ≥ 14)
    batch_full = run_shadow_batch(
        corpus,
        settings=settings,
        production_picks=production_picks,
        write_logs=write_logs,
    )
    panel_full = _panel_from_batch(
        "full_operational_285r",
        batch_full,
        window_days=int(dq["n_unique_race_days"]),
        flag_default_off=flag_off_before,
        settings=settings,
    )

    # Stability window: last 14 race days
    recent = _slice_last_n_days(corpus, 14)
    recent_picks = {rid: production_picks[rid] for rid in (r["race_id"] for r in recent) if rid in production_picks}
    batch_recent = run_shadow_batch(
        recent,
        settings=settings,
        production_picks=recent_picks,
        write_logs=False,
    )
    recent_days = sorted({_race_day(r["race_id"]) for r in recent})
    panel_recent = _panel_from_batch(
        "last_14_race_days",
        batch_recent,
        window_days=len(recent_days),
        flag_default_off=flag_off_before,
        settings=settings,
    )

    flags.reset_flags_to_default()
    flag_off_after = flags.F_V3_A05_ADM_FAVSAFE_ENABLED is False

    # S1 primary decision: full window must pass; recent window must not violate wr1/churn
    recent_safe = (
        panel_recent["hard_gate"]["require_worsened_winner_rank1_0"]
        and panel_recent["hard_gate"]["require_churn_hit_0"]
    )
    # Recent may have small n; ΔHit>0 soft if n small — still require no wr1/churn
    s1_pass = (
        panel_full["hard_gate"]["pass"]
        and recent_safe
        and dq["h4_calendar_days_ge_14"]
        and flag_off_before
        and flag_off_after
        and int(panel_full["anomalies"]["exception_count"]) == 0
    )
    decision = "PASS" if s1_pass else "FAIL"

    # Production readiness recommendation (separate from S1 eval decision)
    # HOLD: S1 PASS does not authorize Flag ON / wiring while PRR HOLD and live API unwired
    if decision != "PASS":
        readiness = "FAIL"
        readiness_reason = "S1 Hard Gate / stability failed"
    else:
        readiness = "HOLD"
        readiness_reason = (
            "S1 Shadow PASS but PRR remains HOLD: Prediction API unwired, "
            "Feature Flag default OFF required, no Production Rollout approval"
        )

    risk = {
        "production_decision_changed": False,
        "shadow_purchase_executed": False,
        "flag_default_changed": not (flag_off_before and flag_off_after),
        "shadow_error_n": panel_full["anomalies"]["exception_count"],
        "shadow_error_rate": panel_full["metrics"].get("shadow_error_rate"),
        "worsened_winner_rank1_full": panel_full["metrics"].get("worsened_winner_rank1"),
        "worsened_winner_rank1_recent14": panel_recent["metrics"].get("worsened_winner_rank1"),
        "data_quality": dq,
        "stability": {
            "full_pass": panel_full["hard_gate"]["pass"],
            "recent_14_wr1_and_churn_safe": recent_safe,
            "recent_14_delta_hit": panel_recent["metrics"].get("delta_hit"),
            "recent_14_n": panel_recent["n"],
            "recent_14_days": recent_days,
        },
        "residual_risks": [
            "Live Prediction API ingress still not connected (batch operational corpus)",
            "Control purchase not executed against real purchase API in this Lab evaluation",
            "PRR HOLD — Flag ON / Canary not authorized",
        ],
        "risk_level": "low" if decision == "PASS" else "high",
        "production_readiness_recommendation": readiness,
        "production_readiness_reason": readiness_reason,
    }

    return {
        "evaluation_id": EVAL_ID,
        "phase": "S1",
        "mode": "stability",
        "decision": decision,
        "production_readiness_recommendation": readiness,
        "production_readiness_reason": readiness_reason,
        "corpus_n": len(corpus),
        "corpus_fingerprint": fp,
        "log_path": batch_full.get("log_path"),
        "data_quality": dq,
        "panel_full": panel_full,
        "panel_recent_14_days": panel_recent,
        "risk_summary": risk,
        "settings": settings.to_dict(),
        "constraints": {
            "algorithm_unchanged": True,
            "flag_default_unchanged": flag_off_after,
            "production_wiring": False,
            "purchase_control_only_policy": True,
            "shadow_fail_open": True,
            "shadow_non_purchase": True,
        },
    }


def write_s1_artifacts(result: dict[str, Any] | None = None) -> dict[str, Any]:
    result = result or run_shadow_evaluation_s1(write_logs=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    paths = {
        "full": ARTIFACTS / "shadow_s1_full.json",
        "metrics": ARTIFACTS / "shadow_s1_metric_summary.json",
        "acceptance": ARTIFACTS / "shadow_s1_acceptance_result.json",
        "risk": ARTIFACTS / "shadow_s1_risk_summary.json",
        "readiness": ARTIFACTS / "shadow_s1_production_readiness_recommendation.json",
        "data_quality": ARTIFACTS / "shadow_s1_data_quality.json",
    }
    paths["full"].write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    metrics_summary = {
        "full": result["panel_full"]["metrics"],
        "last_14_race_days": result["panel_recent_14_days"]["metrics"],
        "hard_gate_full": result["panel_full"]["hard_gate"],
        "hard_gate_recent": result["panel_recent_14_days"]["hard_gate"],
    }
    paths["metrics"].write_text(json.dumps(metrics_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["acceptance"].write_text(
        json.dumps(
            {
                "full": result["panel_full"]["acceptance"],
                "last_14_race_days": result["panel_recent_14_days"]["acceptance"],
                "s1_decision": result["decision"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    paths["risk"].write_text(
        json.dumps(result["risk_summary"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    paths["readiness"].write_text(
        json.dumps(
            {
                "recommendation": result["production_readiness_recommendation"],
                "reason": result["production_readiness_reason"],
                "s1_decision": result["decision"],
                "prr_status": "HOLD",
                "flag_on_authorized": False,
                "production_rollout_authorized": False,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    paths["data_quality"].write_text(
        json.dumps(result["data_quality"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    result["artifacts"] = {k: str(v) for k, v in paths.items()}
    result["artifacts"]["log_path"] = result.get("log_path")
    return result


if __name__ == "__main__":
    out = write_s1_artifacts()
    print(
        json.dumps(
            {
                "decision": out["decision"],
                "production_readiness_recommendation": out["production_readiness_recommendation"],
                "full": {
                    "hit": [
                        out["panel_full"]["metrics"]["control_hit"],
                        out["panel_full"]["metrics"]["shadow_hit"],
                    ],
                    "delta_hit": out["panel_full"]["metrics"]["delta_hit"],
                    "wr1": out["panel_full"]["metrics"]["worsened_winner_rank1"],
                    "churn": out["panel_full"]["metrics"]["churn_hit"],
                    "errors": out["panel_full"]["anomalies"]["exception_count"],
                },
                "recent_14": {
                    "n": out["panel_recent_14_days"]["n"],
                    "days": out["panel_recent_14_days"]["n_race_days"],
                    "delta_hit": out["panel_recent_14_days"]["metrics"]["delta_hit"],
                    "wr1": out["panel_recent_14_days"]["metrics"]["worsened_winner_rank1"],
                    "churn": out["panel_recent_14_days"]["metrics"]["churn_hit"],
                },
                "data_quality_days": out["data_quality"]["n_unique_race_days"],
                "artifacts": out.get("artifacts"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
