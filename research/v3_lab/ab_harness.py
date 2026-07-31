# -*- coding: utf-8 -*-
"""Version 3 Lab — AB Harness.

Reproduces Control Hit=218 on a synthetic 285R fixture that mirrors the
locked Control baseline. Does not modify V2 production Accuracy.

P2: F_V3_REPRESENTATION → features only, pick parity.
P3: F_V3_ADMISSION → Banded Deep pool; Evaluation still model_rank passthrough
    → Hit stays 218 on the 2-horse Control fixture (small field admits all).
P4: F_V3_SELECTION → SEL-V3-RO reorder; Evaluation still model_rank passthrough
    → Hit stays 218 (reorder does not change final pick under Evaluation stub).
"""
from __future__ import annotations

from typing import Any

from . import flags
from .metrics import MetricsSink
from .pipeline import run_lab_pipeline
from .taxonomy import CONTROL_CORPUS_SIZE, CONTROL_HIT, taxonomy_snapshot


def build_control_corpus_fixture(n: int = CONTROL_CORPUS_SIZE, hit: int = CONTROL_HIT) -> list[dict[str, Any]]:
    """Synthetic corpus: first `hit` races are Control hits, remainder misses."""
    if hit > n:
        raise ValueError("hit cannot exceed corpus size")
    races: list[dict[str, Any]] = []
    for i in range(n):
        race_id = f"fixture-285-{i+1:03d}"
        runners = [
            {
                "horse_id": f"H{i}-1",
                "horse_number": 1,
                "model_rank": 1,
                "win_prob": 0.2,
                "odds": 3.5,
                "popularity": 1,
                "history_score": 0.22,
                "history_count": 8,
                "running_style": "senko",
            },
            {
                "horse_id": f"H{i}-2",
                "horse_number": 2,
                "model_rank": 2,
                "win_prob": 0.1,
                "odds": 8.0,
                "popularity": 3,
                "history_score": 0.11,
                "history_count": 4,
                "running_style": "sashi",
            },
        ]
        winner_id = f"H{i}-1" if i < hit else f"H{i}-2"
        races.append(
            {
                "race_id": race_id,
                "context": {"race_id": race_id, "field_size": 2},
                "runners": runners,
                "control_hit": i < hit,
                "winner_id": winner_id,
            }
        )
    return races


def _pick_horse_id(bundle: dict[str, Any]) -> str:
    ranked = ((bundle.get("evaluation") or {}).get("ranked")) or []
    if not ranked:
        legs = (((bundle.get("purchase") or {}).get("purchase_plan") or {}).get("legs")) or []
        if not legs:
            return ""
        return str(legs[0].get("horse_id") or "")
    return str(ranked[0].get("horse_id") or "")


def evaluate_arm(
    corpus: list[dict[str, Any]],
    *,
    flag_overrides: dict[str, bool] | None = None,
    capacity_n: int | None = None,
) -> dict[str, Any]:
    """Run lab pipeline over corpus; score hit if top pick == winner_id."""
    flags.reset_flags_to_default()
    if flag_overrides:
        flags.apply_v3_lab_flags(read_env=False, **flag_overrides)
    else:
        flags.apply_v3_lab_flags(read_env=False)

    sink = MetricsSink()
    hits = 0
    details: list[dict[str, Any]] = []
    pool_sizes: list[int] = []
    for row in corpus:
        bundle = run_lab_pipeline(
            row["context"],
            row["runners"],
            capacity_n=capacity_n,
            metrics=sink,
        )
        pick = _pick_horse_id(bundle)
        is_hit = pick == str(row.get("winner_id") or "")
        if is_hit:
            hits += 1
        pool_size = len(((bundle.get("admission") or {}).get("candidate_pool")) or [])
        pool_sizes.append(pool_size)
        details.append(
            {
                "race_id": row["race_id"],
                "pick": pick,
                "winner_id": row.get("winner_id"),
                "hit": is_hit,
                "identity": bundle.get("identity"),
                "pool_size": pool_size,
                "admission_enabled": ((bundle.get("admission") or {}).get("pool_journal") or {}).get("enabled"),
            }
        )

    return {
        "n": len(corpus),
        "hit": hits,
        "miss": len(corpus) - hits,
        "flags": flags.snapshot_flags(),
        "metrics": sink.snapshot(),
        "pool_size_mean": (sum(pool_sizes) / len(pool_sizes)) if pool_sizes else 0.0,
        "details": details,
    }


def churn_hit(control: dict[str, Any], treatment: dict[str, Any]) -> int:
    """Count races where control hit and treatment missed."""
    c_map = {d["race_id"]: d for d in control.get("details") or []}
    t_map = {d["race_id"]: d for d in treatment.get("details") or []}
    n = 0
    for rid, c in c_map.items():
        t = t_map.get(rid)
        if not t:
            continue
        if c.get("hit") and not t.get("hit"):
            n += 1
    return n


def run_ab(
    *,
    corpus: list[dict[str, Any]] | None = None,
    treatment_flags: dict[str, bool] | None = None,
    hard_gate_hit: int = CONTROL_HIT,
) -> dict[str, Any]:
    """
    Control arm: all F_V3_* OFF (identity).
    Treatment arm: optional flags.
    """
    corpus = corpus or build_control_corpus_fixture()
    control = evaluate_arm(corpus, flag_overrides={})
    treatment = evaluate_arm(corpus, flag_overrides=treatment_flags or {})

    sink_note = MetricsSink()
    sink_note.emit("lab.ab.control_hit", value=control["hit"])
    sink_note.emit("lab.ab.treatment_hit", value=treatment["hit"])
    ch = churn_hit(control, treatment)
    sink_note.emit("lab.ab.churn_hit", value=ch)

    hard_pass = treatment["hit"] > hard_gate_hit and ch == 0
    control_repro = control["hit"] == CONTROL_HIT and control["n"] == CONTROL_CORPUS_SIZE
    treatment_flags_used = treatment_flags or {}

    def _only(flag: str) -> bool:
        if not treatment_flags_used.get(flag):
            return False
        others = {k: v for k, v in treatment_flags_used.items() if k != flag and v}
        return not others

    representation_only = _only("F_V3_REPRESENTATION")
    admission_only = _only("F_V3_ADMISSION")
    selection_only = _only("F_V3_SELECTION")

    return {
        "control": {k: v for k, v in control.items() if k != "details"},
        "treatment": {k: v for k, v in treatment.items() if k != "details"},
        "churn_hit": ch,
        "hard_gate": {
            "require_hit_gt": hard_gate_hit,
            "require_churn_hit_0": True,
            "pass": hard_pass,
        },
        "control_reproduces_218": control_repro,
        "representation_parity": {
            "expected_when_representation_only": True,
            "hit_unchanged": treatment["hit"] == control["hit"],
            "churn_hit_0": ch == 0,
            "note": "P2 Representation does not change picks (Evaluation stub)",
            "active": representation_only,
        },
        "admission_parity": {
            "expected_when_admission_only_on_control_fixture": True,
            "hit_unchanged": treatment["hit"] == control["hit"],
            "churn_hit_0": ch == 0,
            "note": "P3 Admission on 2-horse Control fixture admits all; picks unchanged",
            "active": admission_only,
            "treatment_pool_size_mean": treatment.get("pool_size_mean"),
        },
        "selection_parity": {
            "expected_when_selection_only": True,
            "hit_unchanged": treatment["hit"] == control["hit"],
            "churn_hit_0": ch == 0,
            "note": "P4 Selection reorders pool; Evaluation stub re-sorts by model_rank → pick parity",
            "active": selection_only,
        },
        "taxonomy": taxonomy_snapshot(),
        "ab_metrics": sink_note.snapshot(),
        "sample_details": {
            "control": (control.get("details") or [])[:3],
            "treatment": (treatment.get("details") or [])[:3],
        },
    }


def run_p2_representation_ab(
    *,
    corpus: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Convenience: Control OFF vs Treatment F_V3_REPRESENTATION ON."""
    result = run_ab(
        corpus=corpus,
        treatment_flags={"F_V3_REPRESENTATION": True},
    )
    result["experiment_id"] = "v3-p2-representation"
    result["flag"] = "F_V3_REPRESENTATION"
    return result


def run_p3_admission_ab(
    *,
    corpus: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Convenience: Control OFF vs Treatment F_V3_ADMISSION ON."""
    result = run_ab(
        corpus=corpus,
        treatment_flags={"F_V3_ADMISSION": True},
    )
    result["experiment_id"] = "v3-p3-admission"
    result["flag"] = "F_V3_ADMISSION"
    return result


def run_p4_selection_ab(
    *,
    corpus: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Convenience: Control OFF vs Treatment F_V3_SELECTION ON."""
    result = run_ab(
        corpus=corpus,
        treatment_flags={"F_V3_SELECTION": True},
    )
    result["experiment_id"] = "v3-p4-selection"
    result["flag"] = "F_V3_SELECTION"
    return result


__all__ = [
    "build_control_corpus_fixture",
    "evaluate_arm",
    "churn_hit",
    "run_ab",
    "run_p2_representation_ab",
    "run_p3_admission_ab",
    "run_p4_selection_ab",
]
