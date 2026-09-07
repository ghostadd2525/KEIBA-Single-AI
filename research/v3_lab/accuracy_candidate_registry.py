# -*- coding: utf-8 -*-
"""Version 3 Lab — Accuracy Candidate Registry (Phase 1 Close).

Records Primary/Secondary Lab candidates. No algorithm changes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .taxonomy import CONTROL_HIT

LAB_ROOT = Path(__file__).resolve().parent
PHASE1_CLOSE_ID = "v3-accuracy-phase1-close/1.0"
BASELINE_ID = "v3-lab-baseline-p5-v1"
BASELINE_PATH = "research/v3_lab/baselines/lab_baseline_p5.json"
CLOSE_DATE = "2026-07-24"

# Decision (frozen at Phase 1 Close)
CANDIDATE_REGISTRY: dict[str, Any] = {
    "registry_id": "v3-accuracy-candidate-registry/1.0",
    "phase": "Accuracy Phase 1",
    "closed": True,
    "close_id": PHASE1_CLOSE_ID,
    "close_date": CLOSE_DATE,
    "baseline": {
        "id": BASELINE_ID,
        "path": BASELINE_PATH,
        "control_hit": CONTROL_HIT,
        "updated": False,
        "note": "P5 Lab Baseline unchanged at Phase 1 Close",
    },
    "decision": {
        "simultaneous_on": False,
        "production_wiring": False,
        "stack_both": False,
    },
    "primary": {
        "rank": 1,
        "candidate_id": "A-01",
        "experiment_id": "v3-a01-d1-recal",
        "alias": "v3-rank-d1-recal-285r-ab",
        "policy_id": "D1-Recalibrator",
        "evaluation_id": "v3-eval-a01-d1",
        "flag": "F_V3_RANK_D1_ENABLED",
        "flag_default": False,
        "lab_hit": 246,
        "churn_hit": 0,
        "status": "lab_primary_candidate",
        "validation": "PASS",
        "contract": "v3-lab-evaluation/2.0",
        "frozen_logic": True,
    },
    "secondary": {
        "rank": 2,
        "candidate_id": "A-02",
        "experiment_id": "v3-a02-d2-rerank",
        "alias": "v3-rank-d2-rerank-285r-ab",
        "policy_id": "D2-Reranker",
        "evaluation_id": "v3-eval-a02-d2",
        "flag": "F_V3_RANK_D2_ENABLED",
        "flag_default": False,
        "lab_hit": 242,
        "churn_hit": 0,
        "status": "lab_secondary_candidate",
        "validation": "Lab PASS only",
        "contract": "v3-lab-evaluation/2.1",
        "frozen_logic": True,
    },
    "review_ref": "docs/releases/v3-accuracy-candidate-review.md",
}


FEATURE_FLAG_INVENTORY: list[dict[str, Any]] = [
    {"flag": "F_V3_REPRESENTATION", "default": False, "role": "canonical_stage", "phase": "P2", "status": "frozen"},
    {"flag": "F_V3_ADMISSION", "default": False, "role": "canonical_stage", "phase": "P3", "status": "frozen"},
    {"flag": "F_V3_SELECTION", "default": False, "role": "canonical_stage", "phase": "P4", "status": "frozen"},
    {"flag": "F_V3_REPRESENTATION_ENABLED", "default": False, "role": "alias", "phase": "P2", "status": "frozen"},
    {"flag": "F_V3_ADMISSION_ENABLED", "default": False, "role": "alias", "phase": "P3", "status": "frozen"},
    {"flag": "F_V3_SELECTION_ENABLED", "default": False, "role": "alias", "phase": "P4", "status": "frozen"},
    {"flag": "F_V3_LAB_ENABLED", "default": False, "role": "legacy_reserved", "phase": "P1", "status": "reserved"},
    {"flag": "F_V3_EVALUATION_ENABLED", "default": False, "role": "legacy_alias", "phase": "A-01", "status": "alias_to_d1_path"},
    {"flag": "F_V3_PURCHASE_ENABLED", "default": False, "role": "reserved", "phase": "P1", "status": "reserved"},
    {
        "flag": "F_V3_RANK_D1_ENABLED",
        "default": False,
        "role": "accuracy_primary_candidate",
        "phase": "A-01",
        "status": "lab_primary_candidate",
        "env_alias": "WIN5_V3_RANK_D1_ENABLED",
        "production_wiring": False,
    },
    {
        "flag": "F_V3_RANK_D2_ENABLED",
        "default": False,
        "role": "accuracy_secondary_candidate",
        "phase": "A-02",
        "status": "lab_secondary_candidate",
        "env_alias": "WIN5_V3_RANK_D2_ENABLED",
        "production_wiring": False,
    },
    {"flag": "F_V3_AP_BANDED_ENABLED", "default": False, "role": "reserved", "phase": "P3", "status": "reserved"},
    {"flag": "F_V3_AP_COVERAGE_ENABLED", "default": False, "role": "reserved", "phase": "P3", "status": "reserved"},
    {"flag": "F_V3_SEL_REORDER_ENABLED", "default": False, "role": "reserved", "phase": "P4", "status": "reserved"},
]


EXPERIMENT_STATUS: list[dict[str, Any]] = [
    {"experiment_id": "v3-p1-lab-harness", "phase": "P1", "status": "complete", "frozen": True},
    {"experiment_id": "v3-p2-representation", "phase": "P2", "status": "complete", "frozen": True},
    {"experiment_id": "v3-p3-admission", "phase": "P3", "status": "complete", "frozen": True},
    {"experiment_id": "v3-p4-selection", "phase": "P4", "status": "complete", "frozen": True},
    {"experiment_id": "v3-p5-freeze", "phase": "P5", "status": "complete", "frozen": True},
    {
        "experiment_id": "v3-a01-d1-recal",
        "phase": "A-01",
        "status": "lab_primary_candidate",
        "frozen": True,
        "lab_hit": 246,
        "validation": "PASS",
    },
    {
        "experiment_id": "v3-a02-d2-rerank",
        "phase": "A-02",
        "status": "lab_secondary_candidate",
        "frozen": True,
        "lab_hit": 242,
        "validation": "Lab PASS only",
    },
    {
        "experiment_id": "v3-accuracy-candidate-review",
        "phase": "Accuracy Phase 1",
        "status": "complete",
        "frozen": True,
        "decision": "A-01 > A-02",
    },
    {
        "experiment_id": "v3-accuracy-phase1-close",
        "phase": "Accuracy Phase 1",
        "status": "complete",
        "frozen": True,
    },
    {"experiment_id": "v3-feat-contract-roi", "phase": "Accuracy Phase 2+", "status": "reserved", "frozen": True},
    {"experiment_id": "v3-ap-coverage-285r-ab", "phase": "P3", "status": "reserved", "frozen": True},
]


def build_phase1_close_snapshot() -> dict[str, Any]:
    return {
        "close_id": PHASE1_CLOSE_ID,
        "close_date": CLOSE_DATE,
        "phase": "Accuracy Phase 1",
        "status": "CLOSED",
        "candidate_registry": CANDIDATE_REGISTRY,
        "feature_flag_inventory": FEATURE_FLAG_INVENTORY,
        "experiment_status": EXPERIMENT_STATUS,
        "baseline": CANDIDATE_REGISTRY["baseline"],
        "next_phase": {
            "name": "Accuracy Phase 2",
            "status": "not_started",
            "note": "New algorithms require separate approval; Phase 1 Close does not start Phase 2",
        },
        "constraints": {
            "simultaneous_d1_d2_on": False,
            "production_wiring": False,
            "evaluation_logic_frozen": True,
        },
    }


def artifacts_dir() -> Path:
    return LAB_ROOT / "baselines" / "accuracy_phase1_close"


def write_phase1_close_artifacts(snapshot: dict[str, Any] | None = None) -> dict[str, Path]:
    snapshot = snapshot or build_phase1_close_snapshot()
    out = artifacts_dir()
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "close": out / "phase1_close_snapshot.json",
        "candidates": out / "accuracy_candidate_registry.json",
        "flags": out / "feature_flag_inventory.json",
        "experiments": out / "experiment_status.json",
    }
    paths["close"].write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths["candidates"].write_text(
        json.dumps(snapshot["candidate_registry"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    paths["flags"].write_text(
        json.dumps(
            {"inventory_id": "v3-feature-flag-inventory/phase1-close", "flags": snapshot["feature_flag_inventory"]},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    paths["experiments"].write_text(
        json.dumps(
            {"status_id": "v3-experiment-status/phase1-close", "experiments": snapshot["experiment_status"]},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return paths


__all__ = [
    "PHASE1_CLOSE_ID",
    "CANDIDATE_REGISTRY",
    "FEATURE_FLAG_INVENTORY",
    "EXPERIMENT_STATUS",
    "build_phase1_close_snapshot",
    "write_phase1_close_artifacts",
]


if __name__ == "__main__":
    snap = build_phase1_close_snapshot()
    paths = write_phase1_close_artifacts(snap)
    print(
        json.dumps(
            {
                "status": snap["status"],
                "primary": snap["candidate_registry"]["primary"]["candidate_id"],
                "secondary": snap["candidate_registry"]["secondary"]["candidate_id"],
                "paths": {k: str(v) for k, v in paths.items()},
            },
            indent=2,
            ensure_ascii=False,
        )
    )
