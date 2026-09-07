# -*- coding: utf-8 -*-
"""Version 3 Lab — A-05 Shadow Evaluation (S0 Dry-run).

Uses Shadow Runtime on real labeled 285R operational inputs.
Does not change algorithms, Flag defaults, Production, or Purchase.
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
from .shadow.metrics import evaluate_acceptance

LAB_ROOT = Path(__file__).resolve().parent
ARTIFACTS = LAB_ROOT / "baselines" / "a05_shadow_evaluation"
EVAL_ID = "v3-a05-shadow-evaluation/s0-1.0"

# Offline Validation reference (same corpus family)
OFFLINE_REF = {
    "control_hit": 59,
    "a05_hit": 66,
    "delta_hit": 7,
    "worsened_winner_rank1": 0,
    "churn_hit": 0,
    "improved": 7,
}


def _production_picks_from_control(corpus: list[dict[str, Any]]) -> dict[str, str]:
    """Simulate Production Decision = identity top-1 (all Lab flags OFF)."""
    control = evaluate_arm(corpus, flag_overrides={})
    return {d["race_id"]: str(d.get("pick") or "") for d in (control.get("details") or [])}


def run_shadow_evaluation(*, write_logs: bool = True) -> dict[str, Any]:
    corpus = build_real_285r_corpus()
    fp = corpus_fingerprint(corpus)

    flags.reset_flags_to_default()
    flag_default_off_before = flags.F_V3_A05_ADM_FAVSAFE_ENABLED is False

    production_picks = _production_picks_from_control(corpus)

    settings = load_shadow_settings(
        shadow_runtime_enabled=True,
        phase="S0",
        log_dir=str(ARTIFACTS / "logs"),
    )

    batch = run_shadow_batch(
        corpus,
        settings=settings,
        production_picks=production_picks,
        write_logs=write_logs,
    )

    flags.reset_flags_to_default()
    flag_default_off_after = flags.F_V3_A05_ADM_FAVSAFE_ENABLED is False

    records = batch.get("records") or []
    metrics = batch.get("metrics") or {}
    comparator = build_comparator_report(records)

    # Anomaly / exception summary
    errors = [r for r in records if not r.get("shadow_ok")]
    error_reasons = Counter(str(r.get("shadow_error") or "unknown") for r in errors)

    acceptance = evaluate_acceptance(
        metrics,
        settings=settings,
        window_days=None,  # H4 via labeled_n >= 285
        production_a05_default_off=flag_default_off_before and flag_default_off_after,
        a03_co_enabled=False,
        input_mismatch_rate=0.0,
        control_path_healthy=True,
    )
    acceptance["note"] = (
        "S0 Dry-run on real labeled_test 285R via Shadow Runtime; "
        "H4 satisfied by labeled_n>=285 (calendar multi-day window not required)"
    )

    hard_gate = {
        "worsened_winner_rank1": int(metrics.get("worsened_winner_rank1") or 0),
        "delta_hit": int(metrics.get("delta_hit") or 0),
        "churn_hit": int(metrics.get("churn_hit") or 0),
        "require_worsened_winner_rank1_0": int(metrics.get("worsened_winner_rank1") or 0) == 0,
        "require_delta_hit_gt_0": int(metrics.get("delta_hit") or 0) > 0,
        "require_churn_hit_0": int(metrics.get("churn_hit") or 0) == 0,
        "acceptance_hard_pass": bool(acceptance.get("hard_pass")),
    }
    hard_gate["pass"] = (
        hard_gate["require_worsened_winner_rank1_0"]
        and hard_gate["require_delta_hit_gt_0"]
        and hard_gate["require_churn_hit_0"]
        and hard_gate["acceptance_hard_pass"]
    )

    # Parity vs Offline Validation reference
    parity = {
        "offline_ref": OFFLINE_REF,
        "shadow_control_hit": metrics.get("control_hit"),
        "shadow_hit": metrics.get("shadow_hit"),
        "shadow_delta_hit": metrics.get("delta_hit"),
        "shadow_worsened_winner_rank1": metrics.get("worsened_winner_rank1"),
        "shadow_churn_hit": metrics.get("churn_hit"),
        "shadow_improved": metrics.get("improved"),
        "matches_offline_hits": (
            metrics.get("control_hit") == OFFLINE_REF["control_hit"]
            and metrics.get("shadow_hit") == OFFLINE_REF["a05_hit"]
            and metrics.get("delta_hit") == OFFLINE_REF["delta_hit"]
            and metrics.get("worsened_winner_rank1") == OFFLINE_REF["worsened_winner_rank1"]
            and metrics.get("churn_hit") == OFFLINE_REF["churn_hit"]
        ),
    }

    decision = "PASS" if hard_gate["pass"] else "FAIL"

    risk = {
        "production_decision_changed": False,
        "purchase_executed": bool(metrics.get("purchase_executed_any")),
        "flag_default_changed": not (flag_default_off_before and flag_default_off_after),
        "shadow_error_n": int(metrics.get("shadow_error_n") or 0),
        "shadow_error_rate": metrics.get("shadow_error_rate"),
        "worsened_winner_rank1": metrics.get("worsened_winner_rank1"),
        "promote_rate": metrics.get("promote_rate"),
        "parity_with_offline_validation": parity["matches_offline_hits"],
        "residual_risks": [
            "S0 uses labeled historical operational corpus (real 285R), not a live multi-day calendar window",
            "Production Mesh / Prediction API still unwired — live ingress not exercised",
            "Virtual ROI/Purchase only — accounting path not validated",
        ],
        "risk_level": "low" if decision == "PASS" and int(metrics.get("shadow_error_n") or 0) == 0 else "elevated",
    }

    return {
        "evaluation_id": EVAL_ID,
        "phase": "S0",
        "mode": "dry-run",
        "decision": decision,
        "corpus_n": len(corpus),
        "corpus_fingerprint": fp,
        "log_path": batch.get("log_path"),
        "metrics": metrics,
        "comparator_summary": {
            k: v
            for k, v in comparator.items()
            if k
            not in {
                "all_diffs",
                "improved_races",
                "worsened_races",
                "worsened_winner_rank1_races",
            }
        },
        "comparator": {
            "improved_count": comparator["improved_count"],
            "worsened_count": comparator["worsened_count"],
            "worsened_winner_rank1_count": comparator["worsened_winner_rank1_count"],
            "improved_races": comparator["improved_races"],
            "worsened_races": comparator["worsened_races"],
            "worsened_winner_rank1_races": comparator["worsened_winner_rank1_races"],
        },
        "acceptance": acceptance,
        "hard_gate": hard_gate,
        "anomalies": {
            "exception_count": len(errors),
            "error_reasons": dict(error_reasons),
            "error_race_ids": [r.get("race_id") for r in errors],
        },
        "parity_offline": parity,
        "risk_summary": risk,
        "settings": settings.to_dict(),
        "constraints": {
            "algorithm_unchanged": True,
            "flag_default_unchanged": flag_default_off_after,
            "production_wiring": False,
            "purchase_forbidden": True,
            "fail_open": True,
        },
    }


def write_evaluation_artifacts(result: dict[str, Any] | None = None) -> dict[str, Any]:
    result = result or run_shadow_evaluation(write_logs=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    full = ARTIFACTS / "shadow_evaluation_full.json"
    metrics_path = ARTIFACTS / "shadow_metric_summary.json"
    acceptance_path = ARTIFACTS / "shadow_acceptance_result.json"
    risk_path = ARTIFACTS / "shadow_risk_summary.json"
    comparator_path = ARTIFACTS / "shadow_comparator.json"

    # Full without giant all_diffs duplication
    full.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    metrics_path.write_text(
        json.dumps(result.get("metrics") or {}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    acceptance_path.write_text(
        json.dumps(result.get("acceptance") or {}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    risk_path.write_text(
        json.dumps(result.get("risk_summary") or {}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    comparator_path.write_text(
        json.dumps(result.get("comparator") or {}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result["artifacts"] = {
        "full": str(full),
        "metrics": str(metrics_path),
        "acceptance": str(acceptance_path),
        "risk": str(risk_path),
        "comparator": str(comparator_path),
        "log_path": result.get("log_path"),
    }
    return result


if __name__ == "__main__":
    out = write_evaluation_artifacts()
    print(
        json.dumps(
            {
                "decision": out["decision"],
                "hard_gate": out["hard_gate"],
                "metrics": {
                    "control_hit": out["metrics"]["control_hit"],
                    "shadow_hit": out["metrics"]["shadow_hit"],
                    "delta_hit": out["metrics"]["delta_hit"],
                    "worsened_winner_rank1": out["metrics"]["worsened_winner_rank1"],
                    "churn_hit": out["metrics"]["churn_hit"],
                    "improved": out["metrics"]["improved"],
                    "shadow_error_n": out["metrics"]["shadow_error_n"],
                },
                "acceptance": out["acceptance"]["decision"],
                "parity_offline": out["parity_offline"]["matches_offline_hits"],
                "artifacts": out.get("artifacts"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
