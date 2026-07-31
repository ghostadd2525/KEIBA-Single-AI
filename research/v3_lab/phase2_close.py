# -*- coding: utf-8 -*-
"""Version 3 Lab — Accuracy Phase 2 Close (Baseline v3 = A-01+A-03+A-04).

Records the official Lab stack after A-04 Lab PASS. Does not modify
A-01 / A-02 / A-03 / A-04 or other Accuracy algorithm modules.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .a01_accuracy import summarize_arm_details
from .a03_accuracy import build_a03_accuracy_corpus
from .ab_harness import churn_hit, evaluate_arm
from .contracts import CONTRACT_IDS
from .taxonomy import CONTROL_CORPUS_SIZE, CONTROL_HIT

LAB_ROOT = Path(__file__).resolve().parent
PHASE2_CLOSE_ID = "v3-accuracy-phase2-close/1.0"
BASELINE_V3_ID = "v3-lab-baseline-v3-a01-a03-a04"
BASELINE_V2_ID = "v3-lab-baseline-v2-a01-a03"
BASELINE_P5_ID = "v3-lab-baseline-p5-v1"
CLOSE_DATE = "2026-07-24"
STACK_HIT_V3 = 279
STACK_HIT_V2 = 255

LAB_CONFIGURATION_V3: dict[str, Any] = {
    "configuration_id": "v3-lab-config-a01-a03-a04/1.0",
    "close_id": PHASE2_CLOSE_ID,
    "close_date": CLOSE_DATE,
    "frozen": True,
    "phase": "Accuracy Phase 2 Close",
    "production_wiring": False,
    "name": "Lab Stack A-01 + A-03 + A-04",
    "parent_configuration_id": "v3-lab-config-a01-a03/1.0",
    "pipeline": [
        {
            "stage": "representation",
            "mode": "baseline",
            "policy_id": "identity",
            "flag": "F_V3_REPRESENTATION",
            "flag_state_in_stack": False,
            "note": "Baseline passthrough",
        },
        {
            "stage": "admission",
            "mode": "A-03",
            "policy_id": "AP-V3-A03-pool-coverage",
            "admission_id": "v3-adm-a03-v1",
            "flag": "F_V3_A03_POOL_ADMIT_ENABLED",
            "flag_state_in_stack": True,
            "contract": "v3-lab-admission/2.1",
            "validation": "PASS",
        },
        {
            "stage": "selection",
            "mode": "A-04",
            "policy_id": "SEL-V3-A04-history-crowding",
            "selection_id": "v3-sel-a04-v1",
            "flag": "F_V3_A04_SEL_HISTORY_ENABLED",
            "flag_state_in_stack": True,
            "contract": "v3-lab-selection/2.0",
            "validation": "PASS",
        },
        {
            "stage": "evaluation",
            "mode": "A-01",
            "policy_id": "D1-Recalibrator",
            "evaluation_id": "v3-eval-a01-d1",
            "flag": "F_V3_RANK_D1_ENABLED",
            "flag_state_in_stack": True,
            "contract": "v3-lab-evaluation/2.0",
            "validation": "PASS",
        },
        {
            "stage": "purchase",
            "mode": "baseline",
            "mapper": "identity",
            "flag": "F_V3_PURCHASE_ENABLED",
            "flag_state_in_stack": False,
            "note": "Baseline passthrough · Delete unchanged · out of research scope",
        },
    ],
    "stack_flags_on": [
        "F_V3_A03_POOL_ADMIT_ENABLED",
        "F_V3_A04_SEL_HISTORY_ENABLED",
        "F_V3_RANK_D1_ENABLED",
    ],
    "stack_flags_explicitly_off": [
        "F_V3_REPRESENTATION",
        "F_V3_ADMISSION",
        "F_V3_SELECTION",
        "F_V3_RANK_D2_ENABLED",
        "F_V3_PURCHASE_ENABLED",
    ],
    "diagram": {
        "ascii": (
            "Representation (Baseline)\n"
            "        ↓\n"
            "Admission (A-03)\n"
            "        ↓\n"
            "Selection (A-04)\n"
            "        ↓\n"
            "Evaluation (A-01)\n"
            "        ↓\n"
            "Purchase (Baseline)"
        ),
    },
}

CANDIDATE_REGISTRY_V3: dict[str, Any] = {
    "registry_id": "v3-accuracy-candidate-registry/3.0",
    "phase": "Accuracy Phase 2 Close",
    "close_id": PHASE2_CLOSE_ID,
    "close_date": CLOSE_DATE,
    "closed": True,
    "baseline_v3": {
        "id": BASELINE_V3_ID,
        "path": "research/v3_lab/baselines/lab_baseline_v3_a01_a03_a04.json",
        "stack_hit": STACK_HIT_V3,
        "control_hit": CONTROL_HIT,
    },
    "baseline_v2": {
        "id": BASELINE_V2_ID,
        "path": "research/v3_lab/baselines/lab_baseline_v2_a01_a03.json",
        "stack_hit": STACK_HIT_V2,
        "note": "Superseded as official Accuracy stack by Baseline v3; retained as history",
    },
    "baseline_p5": {
        "id": BASELINE_P5_ID,
        "path": "research/v3_lab/baselines/lab_baseline_p5.json",
        "note": "Foundation freeze retained",
    },
    "decision": {
        "adopted_stack": ["A-03 Admission", "A-04 Selection", "A-01 Evaluation"],
        "a02_role": "secondary_candidate_held",
        "simultaneous_d1_d2": False,
        "delete_in_research_scope": False,
        "production_wiring": False,
        "phase2_closed": True,
    },
    "stack_primary": {
        "name": "A-01 + A-03 + A-04",
        "evaluation": "A-01",
        "admission": "A-03",
        "selection": "A-04",
        "lab_hit": STACK_HIT_V3,
        "churn_hit": 0,
        "validation": "PASS",
        "status": "lab_adopted_configuration",
    },
    "evaluation_primary": {
        "candidate_id": "A-01",
        "flag": "F_V3_RANK_D1_ENABLED",
        "lab_hit_alone": 246,
        "status": "lab_primary_evaluation",
        "in_adopted_stack": True,
        "frozen_logic": True,
    },
    "admission_primary": {
        "candidate_id": "A-03",
        "flag": "F_V3_A03_POOL_ADMIT_ENABLED",
        "lab_hit_incremental_vs_a01": 255,
        "status": "lab_primary_admission",
        "in_adopted_stack": True,
        "frozen_logic": True,
    },
    "selection_primary": {
        "candidate_id": "A-04",
        "flag": "F_V3_A04_SEL_HISTORY_ENABLED",
        "lab_hit_incremental_vs_v2": STACK_HIT_V3,
        "status": "lab_primary_selection",
        "in_adopted_stack": True,
        "frozen_logic": True,
    },
    "evaluation_secondary": {
        "candidate_id": "A-02",
        "flag": "F_V3_RANK_D2_ENABLED",
        "lab_hit_alone": 242,
        "status": "lab_secondary_candidate",
        "in_adopted_stack": False,
        "note": "Held as Secondary; D1+D2 simultaneous ON forbidden",
        "frozen_logic": True,
    },
}

FEATURE_FLAG_INVENTORY_V3: list[dict[str, Any]] = [
    {"flag": "F_V3_REPRESENTATION", "default": False, "stack": "OFF", "role": "baseline_stage"},
    {"flag": "F_V3_ADMISSION", "default": False, "stack": "OFF", "role": "p3_policy_not_in_stack"},
    {"flag": "F_V3_SELECTION", "default": False, "stack": "OFF", "role": "p4_policy_not_in_stack"},
    {"flag": "F_V3_A03_POOL_ADMIT_ENABLED", "default": False, "stack": "ON", "role": "adopted_admission_a03"},
    {"flag": "F_V3_A04_SEL_HISTORY_ENABLED", "default": False, "stack": "ON", "role": "adopted_selection_a04"},
    {"flag": "F_V3_RANK_D1_ENABLED", "default": False, "stack": "ON", "role": "adopted_evaluation_a01"},
    {"flag": "F_V3_RANK_D2_ENABLED", "default": False, "stack": "OFF", "role": "secondary_candidate_a02"},
    {"flag": "F_V3_PURCHASE_ENABLED", "default": False, "stack": "OFF", "role": "baseline_stage"},
    {"flag": "F_V3_EVALUATION_ENABLED", "default": False, "stack": "OFF", "role": "legacy_alias"},
    {"flag": "F_V3_LAB_ENABLED", "default": False, "stack": "OFF", "role": "legacy_reserved"},
]

EXPERIMENT_STATUS_V3: list[dict[str, Any]] = [
    {"experiment_id": "v3-p5-freeze", "status": "complete", "note": "foundation"},
    {"experiment_id": "v3-a01-d1-recal", "status": "lab_primary_evaluation", "in_stack": True},
    {"experiment_id": "v3-a02-d2-rerank", "status": "lab_secondary_candidate", "in_stack": False},
    {"experiment_id": "v3-a03-pool-coverage", "status": "lab_primary_admission", "in_stack": True},
    {"experiment_id": "v3-lab-configuration-freeze", "status": "complete", "note": "Baseline v2 history"},
    {"experiment_id": "v3-accuracy-gap-analysis-v2", "status": "complete"},
    {"experiment_id": "v3-a04-sel-history", "status": "lab_primary_selection", "in_stack": True},
    {"experiment_id": "v3-accuracy-phase2-close", "status": "closed", "close_id": PHASE2_CLOSE_ID},
]

REMAINING_ISSUES: dict[str, Any] = {
    "issues_id": "v3-accuracy-remaining-issues/phase2-close",
    "close_id": PHASE2_CLOSE_ID,
    "close_date": CLOSE_DATE,
    "baseline_id": BASELINE_V3_ID,
    "stack_hit": STACK_HIT_V3,
    "miss_total": 6,
    "in_research_scope": [],
    "out_of_research_scope": [
        {
            "layer": "Delete",
            "n": 6,
            "race_ids": [
                "a03-285-280",
                "a03-285-281",
                "a03-285-282",
                "a03-285-283",
                "a03-285-284",
                "a03-285-285",
            ],
            "reason": "Purchase / Delete Boundary — Accuracy research excluded by product policy",
            "stage": "Delete",
            "action": "none",
        }
    ],
    "notes": [
        "Eval / Boundary / Reorder / Pool residuals are recovered under Baseline v3",
        "Phase 3 research not started",
        "Production wiring remains False",
    ],
}


def _sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def module_fingerprint() -> dict[str, str]:
    names = [
        "feature_generator.py",
        "admission_policy.py",
        "admission_policy_a03.py",
        "selection_policy.py",
        "selection_policy_a04.py",
        "evaluation_policy.py",
        "evaluation_policy_d2.py",
    ]
    return {n: _sha16(LAB_ROOT / n) for n in names if (LAB_ROOT / n).is_file()}


def build_lab_baseline_v3() -> dict[str, Any]:
    """Measure official Phase 2 stack on A-03 corpus."""
    corpus = build_a03_accuracy_corpus()
    control = evaluate_arm(corpus, flag_overrides={})
    baseline_v2 = evaluate_arm(
        corpus,
        flag_overrides={
            "F_V3_RANK_D1_ENABLED": True,
            "F_V3_A03_POOL_ADMIT_ENABLED": True,
        },
    )
    stack = evaluate_arm(
        corpus,
        flag_overrides={
            "F_V3_RANK_D1_ENABLED": True,
            "F_V3_A03_POOL_ADMIT_ENABLED": True,
            "F_V3_A04_SEL_HISTORY_ENABLED": True,
        },
    )
    a01 = evaluate_arm(corpus, flag_overrides={"F_V3_RANK_D1_ENABLED": True})
    c_sum = summarize_arm_details(corpus, control)
    v2_sum = summarize_arm_details(corpus, baseline_v2)
    s_sum = summarize_arm_details(corpus, stack)
    a01_sum = summarize_arm_details(corpus, a01)
    ch = churn_hit(control, stack)
    ch_v2 = churn_hit(baseline_v2, stack)
    ch_a01 = churn_hit(a01, stack)
    return {
        "baseline_id": BASELINE_V3_ID,
        "close_id": PHASE2_CLOSE_ID,
        "close_date": CLOSE_DATE,
        "generated_on": CLOSE_DATE,
        "parent_baseline": BASELINE_V2_ID,
        "foundation_baseline": BASELINE_P5_ID,
        "corpus": {
            "id": "a03-285-*",
            "n": CONTROL_CORPUS_SIZE,
            "builder": "build_a03_accuracy_corpus",
        },
        "control": {
            "name": "Lab Baseline OFF (identity)",
            "hit": c_sum["hit"],
            "metrics": c_sum,
        },
        "a01_reference": {
            "name": "A-01 Evaluation only",
            "hit": a01_sum["hit"],
            "metrics": a01_sum,
        },
        "baseline_v2_reference": {
            "name": "A-01 + A-03 (Baseline v2)",
            "hit": v2_sum["hit"],
            "metrics": v2_sum,
        },
        "stack": {
            "name": "A-01 Evaluation + A-03 Admission + A-04 Selection",
            "flags_on": list(LAB_CONFIGURATION_V3["stack_flags_on"]),
            "hit": s_sum["hit"],
            "metrics": s_sum,
            "churn_vs_control": ch,
            "churn_vs_baseline_v2": ch_v2,
            "churn_vs_a01": ch_a01,
        },
        "delta_stack_vs_control": {
            "hit": s_sum["hit"] - c_sum["hit"],
            "purchase": s_sum["purchase"] - c_sum["purchase"],
            "rank710": s_sum["rank710"] - c_sum["rank710"],
            "rank46": s_sum["rank46"] - c_sum["rank46"],
            "other": s_sum["other"] - c_sum["other"],
            "roi": round(s_sum["roi"] - c_sum["roi"], 4),
        },
        "delta_stack_vs_baseline_v2": {
            "hit": s_sum["hit"] - v2_sum["hit"],
            "purchase": s_sum["purchase"] - v2_sum["purchase"],
            "rank710": s_sum["rank710"] - v2_sum["rank710"],
            "rank46": s_sum["rank46"] - v2_sum["rank46"],
            "other": s_sum["other"] - v2_sum["other"],
            "roi": round(s_sum["roi"] - v2_sum["roi"], 4),
        },
        "configuration": LAB_CONFIGURATION_V3,
        "candidates": CANDIDATE_REGISTRY_V3,
        "remaining_issues": REMAINING_ISSUES,
        "contracts": dict(CONTRACT_IDS),
        "module_sha256_16": module_fingerprint(),
        "invariants": {
            "control_hit_218": c_sum["hit"] == CONTROL_HIT,
            "baseline_v2_hit_255": v2_sum["hit"] == STACK_HIT_V2,
            "stack_hit_279": s_sum["hit"] == STACK_HIT_V3,
            "churn_vs_control_0": ch == 0,
            "churn_vs_baseline_v2_0": ch_v2 == 0,
            "remaining_miss_delete_only": s_sum["miss"] == 6 and s_sum["rank46"] == 6,
            "production_wiring": False,
            "algorithms_unchanged": True,
        },
        "notes": {
            "a02": "Secondary candidate held; not in stack",
            "delete": "6 misses remain; out of Accuracy research scope",
            "defaults": "All F_V3_* remain default OFF in runtime; stack documents Lab adoption intent",
        },
    }


def artifacts_dir() -> Path:
    return LAB_ROOT / "baselines"


def write_phase2_close_artifacts(
    baseline: dict[str, Any] | None = None,
) -> dict[str, Path]:
    baseline = baseline or build_lab_baseline_v3()
    out = artifacts_dir()
    out.mkdir(parents=True, exist_ok=True)
    close_dir = out / "accuracy_phase2_close"
    close_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "baseline_v3": out / "lab_baseline_v3_a01_a03_a04.json",
        "configuration": close_dir / "lab_configuration_registry_v3.json",
        "candidates": close_dir / "accuracy_candidate_registry_v3.json",
        "flags": close_dir / "feature_flag_inventory_v3.json",
        "experiments": close_dir / "experiment_status_v3.json",
        "remaining": close_dir / "remaining_issues.json",
        "snapshot": close_dir / "phase2_close_snapshot.json",
    }
    paths["baseline_v3"].write_text(
        json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    paths["configuration"].write_text(
        json.dumps(LAB_CONFIGURATION_V3, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    paths["candidates"].write_text(
        json.dumps(CANDIDATE_REGISTRY_V3, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    paths["flags"].write_text(
        json.dumps(
            {"inventory_id": "v3-feature-flag-inventory/phase2-close", "flags": FEATURE_FLAG_INVENTORY_V3},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    paths["experiments"].write_text(
        json.dumps(
            {"status_id": "v3-experiment-status/phase2-close", "experiments": EXPERIMENT_STATUS_V3},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    paths["remaining"].write_text(
        json.dumps(REMAINING_ISSUES, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    paths["snapshot"].write_text(
        json.dumps(
            {
                "close_id": PHASE2_CLOSE_ID,
                "baseline_id": BASELINE_V3_ID,
                "configuration": LAB_CONFIGURATION_V3,
                "candidates": CANDIDATE_REGISTRY_V3,
                "remaining_issues": REMAINING_ISSUES,
                "invariants": baseline["invariants"],
                "stack_metrics": baseline["stack"]["metrics"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return paths


__all__ = [
    "PHASE2_CLOSE_ID",
    "BASELINE_V3_ID",
    "LAB_CONFIGURATION_V3",
    "CANDIDATE_REGISTRY_V3",
    "FEATURE_FLAG_INVENTORY_V3",
    "EXPERIMENT_STATUS_V3",
    "REMAINING_ISSUES",
    "build_lab_baseline_v3",
    "write_phase2_close_artifacts",
]


if __name__ == "__main__":
    base = build_lab_baseline_v3()
    paths = write_phase2_close_artifacts(base)
    print(
        json.dumps(
            {
                "close_id": PHASE2_CLOSE_ID,
                "baseline_id": BASELINE_V3_ID,
                "control_hit": base["control"]["hit"],
                "stack_hit": base["stack"]["hit"],
                "invariants": base["invariants"],
                "paths": {k: str(v) for k, v in paths.items()},
            },
            indent=2,
            ensure_ascii=False,
        )
    )
