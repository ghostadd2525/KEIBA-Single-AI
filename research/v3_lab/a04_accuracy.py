# -*- coding: utf-8 -*-
"""Version 3 Lab — A-04 Accuracy AB (Selection History Crowding).

Selection-only intervention on Lab Baseline v2 (A-01 + A-03).
Hard Gate: Hit > 255 ∧ churn_hit = 0 on a03-285 corpus.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .a01_accuracy import summarize_arm_details
from .a03_accuracy import build_a03_accuracy_corpus
from .ab_harness import churn_hit, evaluate_arm
from .metrics import MetricsSink
from .taxonomy import taxonomy_snapshot

STAKE_YEN = 100
BASELINE_V2_HIT = 255
BOUNDARY_TARGET = 14
REORDER_TARGET = 10


def _improved_worsened(
    corpus: list[dict[str, Any]],
    control: dict[str, Any],
    treatment: dict[str, Any],
) -> dict[str, Any]:
    c_map = {d["race_id"]: d for d in control.get("details") or []}
    t_map = {d["race_id"]: d for d in treatment.get("details") or []}
    row_map = {r["race_id"]: r for r in corpus}
    improved = []
    worsened = []
    for rid, c in c_map.items():
        t = t_map.get(rid) or {}
        row = row_map.get(rid) or {}
        if (not c.get("hit")) and t.get("hit"):
            improved.append(
                {
                    "race_id": rid,
                    "miss_layer": row.get("miss_layer"),
                    "winner_rank": row.get("winner_rank"),
                    "control_pick": c.get("pick"),
                    "treatment_pick": t.get("pick"),
                }
            )
        elif c.get("hit") and (not t.get("hit")):
            worsened.append(
                {
                    "race_id": rid,
                    "miss_layer": row.get("miss_layer"),
                    "control_pick": c.get("pick"),
                    "treatment_pick": t.get("pick"),
                }
            )
    return {"improved": improved, "worsened": worsened}


def run_a04_ab(
    *,
    corpus: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """A-04 AB.

    Attribution arm: OFF vs A-04 only.
    Hard Gate arm: Baseline v2 (A-01+A-03) vs Baseline v2 + A-04.
    """
    corpus = corpus or build_a03_accuracy_corpus()

    baseline_off = evaluate_arm(corpus, flag_overrides={})
    a04_only = evaluate_arm(corpus, flag_overrides={"F_V3_A04_SEL_HISTORY_ENABLED": True})
    baseline_v2 = evaluate_arm(
        corpus,
        flag_overrides={
            "F_V3_RANK_D1_ENABLED": True,
            "F_V3_A03_POOL_ADMIT_ENABLED": True,
        },
    )
    treatment = evaluate_arm(
        corpus,
        flag_overrides={
            "F_V3_RANK_D1_ENABLED": True,
            "F_V3_A03_POOL_ADMIT_ENABLED": True,
            "F_V3_A04_SEL_HISTORY_ENABLED": True,
        },
    )

    off_sum = summarize_arm_details(corpus, baseline_off)
    attr_sum = summarize_arm_details(corpus, a04_only)
    c_sum = summarize_arm_details(corpus, baseline_v2)
    t_sum = summarize_arm_details(corpus, treatment)

    ch_attr = churn_hit(baseline_off, a04_only)
    ch_gate = churn_hit(baseline_v2, treatment)
    races_attr = _improved_worsened(corpus, baseline_off, a04_only)
    races_gate = _improved_worsened(corpus, baseline_v2, treatment)

    hard_pass = t_sum["hit"] > BASELINE_V2_HIT and ch_gate == 0
    decision = "PASS" if hard_pass else "FAIL"
    if t_sum["hit"] <= BASELINE_V2_HIT:
        decision = "FAIL_NO_IMPROVEMENT"

    improved_layers = dict(Counter(str(x.get("miss_layer")) for x in races_gate["improved"]))

    sink = MetricsSink()
    sink.emit("lab.ab.control_hit", value=c_sum["hit"])
    sink.emit("lab.ab.treatment_hit", value=t_sum["hit"])
    sink.emit("lab.ab.churn_hit", value=ch_gate)
    sink.emit("lab.ab.a04.hit", value=t_sum["hit"])

    return {
        "experiment_id": "v3-a04-sel-history",
        "flag": "F_V3_A04_SEL_HISTORY_ENABLED",
        "stage": "Selection",
        "policy_id": "SEL-V3-A04-history-crowding",
        "baseline_off": off_sum,
        "a04_only": {**attr_sum, "churn_vs_baseline_off": ch_attr, **races_attr},
        "control": {**{k: v for k, v in baseline_v2.items() if k != "details"}, **c_sum},
        "treatment": {**{k: v for k, v in treatment.items() if k != "details"}, **t_sum},
        "delta": {
            "hit": t_sum["hit"] - c_sum["hit"],
            "purchase": t_sum["purchase"] - c_sum["purchase"],
            "rank710": t_sum["rank710"] - c_sum["rank710"],
            "rank46": t_sum["rank46"] - c_sum["rank46"],
            "other": t_sum["other"] - c_sum["other"],
            "roi": round(t_sum["roi"] - c_sum["roi"], 4),
        },
        "churn_hit": ch_gate,
        "improved_races": races_gate["improved"],
        "worsened_races": races_gate["worsened"],
        "improved_layers": improved_layers,
        "hard_gate": {
            "require_hit_gt": BASELINE_V2_HIT,
            "require_churn_hit_0": True,
            "control_definition": "Lab Baseline v2 (A-01 + A-03)",
            "treatment_definition": "Baseline v2 + A-04 Selection",
            "pass": hard_pass,
        },
        "control_reproduces_baseline_v2_255": c_sum["hit"] == BASELINE_V2_HIT,
        "selection_attribution": {
            "expected_boundary": BOUNDARY_TARGET,
            "expected_reorder": REORDER_TARGET,
            "improved_boundary": int(improved_layers.get("Boundary") or 0),
            "improved_reorder": int(improved_layers.get("Reorder") or 0),
            "a04_only_hit": attr_sum["hit"],
            "baseline_off_hit": off_sum["hit"],
        },
        "decision": decision,
        "adopt": hard_pass,
        "taxonomy": taxonomy_snapshot(),
        "ab_metrics": sink.snapshot(),
        "notes": {
            "scope": "Selection only (History Crowding Promote)",
            "unchanged": [
                "Evaluation logic",
                "Representation",
                "Admission",
                "Purchase",
                "A-01/A-02/A-03 policy modules",
                "V2 Production",
            ],
            "delete_excluded": True,
            "roi_def": f"flat bet {STAKE_YEN}yen/race on top pick; ROI=(return-stake)/stake",
        },
    }


def write_a04_artifacts(result: dict[str, Any] | None = None) -> Path:
    result = result or run_a04_ab()
    out_dir = Path(__file__).resolve().parent / "baselines" / "a04_accuracy"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "a04_ab_result.json"
    slim = {k: v for k, v in result.items()}
    path.write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")
    diff = {
        "improved_races": result.get("improved_races") or [],
        "worsened_races": result.get("worsened_races") or [],
        "improved_layers": result.get("improved_layers") or {},
        "delta": result.get("delta") or {},
        "churn_hit": result.get("churn_hit"),
        "decision": result.get("decision"),
    }
    (out_dir / "a04_race_diff.json").write_text(
        json.dumps(diff, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


__all__ = [
    "STAKE_YEN",
    "BASELINE_V2_HIT",
    "run_a04_ab",
    "write_a04_artifacts",
]
