# -*- coding: utf-8 -*-
"""Version 3 Lab — A-02 Accuracy corpus + AB metrics (D2 Reranker).

Independent of A-01. Synthetic 285R with Control Hit=218.
Boundary/Reorder misses are D2-recoverable via pairwise history strength.
"""
from __future__ import annotations

from typing import Any

from .a01_accuracy import run_a01_ab, summarize_arm_details
from .ab_harness import churn_hit, evaluate_arm
from .metrics import MetricsSink
from .taxonomy import CONTROL_CORPUS_SIZE, CONTROL_HIT, TAXONOMY_LOCK, taxonomy_snapshot

STAKE_YEN = 100
A01_REFERENCE_HIT = 246


def _horse(
    race_i: int,
    num: int,
    *,
    model_rank: int,
    win_prob: float,
    odds: float,
    popularity: int,
    history_score: float | None = None,
) -> dict[str, Any]:
    hist = win_prob if history_score is None else history_score
    return {
        "horse_id": f"H{race_i}-{num}",
        "horse_number": num,
        "model_rank": model_rank,
        "win_prob": win_prob,
        "odds": odds,
        "popularity": popularity,
        "history_score": hist,
        "history_count": max(1, 12 - model_rank),
        "running_style": ["nige", "senko", "sashi", "oikomi"][num % 4],
    }


def build_a02_accuracy_corpus(
    n: int = CONTROL_CORPUS_SIZE,
    hit: int = CONTROL_HIT,
) -> list[dict[str, Any]]:
    """285R corpus: Control identity Hit=hit; Boundary/Reorder recoverable by D2."""
    if hit > n:
        raise ValueError("hit cannot exceed corpus size")
    miss_n = n - hit
    layers = (
        [("Eval",)] * TAXONOMY_LOCK["Eval"]
        + [("Boundary",)] * TAXONOMY_LOCK["Boundary"]
        + [("Reorder",)] * TAXONOMY_LOCK["Reorder"]
        + [("Pool",)] * TAXONOMY_LOCK["Pool"]
        + [("Delete",)] * TAXONOMY_LOCK["Delete"]
    )
    if len(layers) != miss_n and n == CONTROL_CORPUS_SIZE and hit == CONTROL_HIT:
        raise ValueError(f"taxonomy miss layers {len(layers)} != miss_n {miss_n}")

    races: list[dict[str, Any]] = []
    for i in range(n):
        race_id = f"a02-285-{i+1:03d}"
        if i < hit:
            # Clear favorite — D2 must not churn (low crowding path)
            runners = [
                _horse(i, 1, model_rank=1, win_prob=0.28, odds=2.8, popularity=1, history_score=0.28),
                _horse(i, 2, model_rank=2, win_prob=0.14, odds=6.5, popularity=3, history_score=0.14),
                _horse(i, 3, model_rank=3, win_prob=0.10, odds=9.0, popularity=5, history_score=0.10),
                _horse(i, 4, model_rank=4, win_prob=0.08, odds=12.0, popularity=6, history_score=0.08),
                _horse(i, 5, model_rank=5, win_prob=0.06, odds=18.0, popularity=8, history_score=0.06),
                _horse(i, 6, model_rank=6, win_prob=0.05, odds=22.0, popularity=9, history_score=0.05),
                _horse(i, 7, model_rank=7, win_prob=0.04, odds=30.0, popularity=10, history_score=0.04),
                _horse(i, 8, model_rank=8, win_prob=0.03, odds=40.0, popularity=12, history_score=0.03),
            ]
            winner_id = f"H{i}-1"
            miss_layer = None
            winner_rank = 1
            purchase_eligible = True
        else:
            layer = layers[i - hit][0]
            miss_layer = layer
            if layer == "Eval":
                # Wrong favorite; no history advantage for winner → D2 does not recover
                # (A-01 D1 recovers a different Eval shape on a01 corpus)
                runners = [
                    _horse(i, 1, model_rank=1, win_prob=0.22, odds=3.5, popularity=1, history_score=0.22),
                    _horse(i, 2, model_rank=2, win_prob=0.16, odds=5.5, popularity=3, history_score=0.16),
                    _horse(i, 3, model_rank=3, win_prob=0.12, odds=8.0, popularity=4, history_score=0.12),
                    _horse(i, 4, model_rank=4, win_prob=0.10, odds=12.0, popularity=6, history_score=0.10),
                    _horse(i, 5, model_rank=5, win_prob=0.08, odds=16.0, popularity=8, history_score=0.08),
                    _horse(i, 6, model_rank=6, win_prob=0.06, odds=22.0, popularity=9, history_score=0.06),
                    _horse(i, 7, model_rank=7, win_prob=0.05, odds=30.0, popularity=10, history_score=0.05),
                    _horse(i, 8, model_rank=8, win_prob=0.04, odds=40.0, popularity=12, history_score=0.04),
                ]
                winner_id = f"H{i}-2"
                winner_rank = 2
            elif layer == "Boundary":
                # Crowded top-3; winner rank3 has superior history → D2 pairwise recovers
                runners = [
                    _horse(i, 1, model_rank=1, win_prob=0.190, odds=3.5, popularity=1, history_score=0.12),
                    _horse(i, 2, model_rank=2, win_prob=0.185, odds=3.8, popularity=2, history_score=0.13),
                    _horse(i, 3, model_rank=3, win_prob=0.180, odds=4.2, popularity=3, history_score=0.48),
                    _horse(i, 4, model_rank=4, win_prob=0.110, odds=8.0, popularity=5, history_score=0.11),
                    _horse(i, 5, model_rank=5, win_prob=0.080, odds=12.0, popularity=7, history_score=0.08),
                    _horse(i, 6, model_rank=6, win_prob=0.060, odds=18.0, popularity=9, history_score=0.06),
                    _horse(i, 7, model_rank=7, win_prob=0.050, odds=25.0, popularity=10, history_score=0.05),
                    _horse(i, 8, model_rank=8, win_prob=0.040, odds=35.0, popularity=12, history_score=0.04),
                ]
                winner_id = f"H{i}-3"
                winner_rank = 3
            elif layer == "Reorder":
                # Crowded top-2; winner rank2 has superior history → D2 recovers
                runners = [
                    _horse(i, 1, model_rank=1, win_prob=0.210, odds=3.2, popularity=1, history_score=0.14),
                    _horse(i, 2, model_rank=2, win_prob=0.205, odds=3.6, popularity=2, history_score=0.46),
                    _horse(i, 3, model_rank=3, win_prob=0.140, odds=7.5, popularity=4, history_score=0.14),
                    _horse(i, 4, model_rank=4, win_prob=0.100, odds=11.0, popularity=6, history_score=0.10),
                    _horse(i, 5, model_rank=5, win_prob=0.080, odds=15.0, popularity=7, history_score=0.08),
                    _horse(i, 6, model_rank=6, win_prob=0.060, odds=20.0, popularity=9, history_score=0.06),
                    _horse(i, 7, model_rank=7, win_prob=0.050, odds=28.0, popularity=10, history_score=0.05),
                    _horse(i, 8, model_rank=8, win_prob=0.040, odds=40.0, popularity=12, history_score=0.04),
                ]
                winner_id = f"H{i}-2"
                winner_rank = 2
            elif layer == "Pool":
                runners = [
                    _horse(i, 1, model_rank=1, win_prob=0.24, odds=3.0, popularity=1),
                    _horse(i, 2, model_rank=2, win_prob=0.16, odds=6.0, popularity=3),
                    _horse(i, 3, model_rank=3, win_prob=0.12, odds=9.0, popularity=5),
                    _horse(i, 4, model_rank=4, win_prob=0.10, odds=12.0, popularity=6),
                    _horse(i, 5, model_rank=5, win_prob=0.08, odds=16.0, popularity=8),
                    _horse(i, 6, model_rank=6, win_prob=0.07, odds=20.0, popularity=9),
                    _horse(i, 7, model_rank=7, win_prob=0.06, odds=28.0, popularity=10),
                    _horse(i, 8, model_rank=8, win_prob=0.05, odds=35.0, popularity=11),
                    _horse(i, 9, model_rank=9, win_prob=0.04, odds=45.0, popularity=13),
                    _horse(i, 10, model_rank=10, win_prob=0.03, odds=55.0, popularity=14),
                    _horse(i, 11, model_rank=11, win_prob=0.025, odds=70.0, popularity=15),
                    _horse(i, 12, model_rank=12, win_prob=0.02, odds=90.0, popularity=16),
                ]
                winner_id = f"H{i}-{8 + ((i - hit) % 3)}"
                winner_rank = 8 + ((i - hit) % 3)
            else:  # Delete
                runners = [
                    _horse(i, 1, model_rank=1, win_prob=0.26, odds=2.9, popularity=1),
                    _horse(i, 2, model_rank=2, win_prob=0.16, odds=6.0, popularity=3),
                    _horse(i, 3, model_rank=3, win_prob=0.12, odds=9.0, popularity=5),
                    _horse(i, 4, model_rank=4, win_prob=0.10, odds=12.0, popularity=6),
                    _horse(i, 5, model_rank=5, win_prob=0.09, odds=14.0, popularity=7),
                    _horse(i, 6, model_rank=6, win_prob=0.07, odds=20.0, popularity=9),
                    _horse(i, 7, model_rank=7, win_prob=0.05, odds=30.0, popularity=10),
                    _horse(i, 8, model_rank=8, win_prob=0.04, odds=40.0, popularity=12),
                ]
                winner_id = f"H{i}-5"
                winner_rank = 5
            purchase_eligible = miss_layer != "Delete"

        races.append(
            {
                "race_id": race_id,
                "context": {"race_id": race_id, "field_size": len(runners)},
                "runners": runners,
                "control_hit": i < hit,
                "winner_id": winner_id,
                "winner_rank": winner_rank,
                "miss_layer": miss_layer,
                "purchase_eligible": purchase_eligible,
            }
        )
    return races


def run_a02_ab(
    *,
    corpus: list[dict[str, Any]] | None = None,
    include_a01_reference: bool = True,
) -> dict[str, Any]:
    """Control OFF vs Treatment F_V3_RANK_D2_ENABLED ON; compare vs Baseline & A-01."""
    corpus = corpus or build_a02_accuracy_corpus()
    control = evaluate_arm(corpus, flag_overrides={})
    treatment = evaluate_arm(corpus, flag_overrides={"F_V3_RANK_D2_ENABLED": True})
    # Same-corpus D1 arm (independence check — should not match A-02 gains)
    d1_on_a02 = evaluate_arm(corpus, flag_overrides={"F_V3_RANK_D1_ENABLED": True})
    ch = churn_hit(control, treatment)

    c_sum = summarize_arm_details(corpus, control)
    t_sum = summarize_arm_details(corpus, treatment)
    d1_sum = summarize_arm_details(corpus, d1_on_a02)

    hard_pass = t_sum["hit"] > CONTROL_HIT and ch == 0
    decision = "PASS" if hard_pass else "FAIL"
    if t_sum["hit"] <= CONTROL_HIT:
        decision = "FAIL_NO_IMPROVEMENT"

    a01_ref: dict[str, Any] | None = None
    if include_a01_reference:
        a01_ref = run_a01_ab()

    sink = MetricsSink()
    sink.emit("lab.ab.control_hit", value=c_sum["hit"])
    sink.emit("lab.ab.treatment_hit", value=t_sum["hit"])
    sink.emit("lab.ab.churn_hit", value=ch)
    sink.emit("lab.ab.a02.hit", value=t_sum["hit"])

    comparison = {
        "lab_baseline_hit": CONTROL_HIT,
        "a01_reference_hit": (a01_ref or {}).get("treatment", {}).get("hit", A01_REFERENCE_HIT),
        "a02_treatment_hit": t_sum["hit"],
        "delta_vs_baseline": t_sum["hit"] - CONTROL_HIT,
        "delta_vs_a01": t_sum["hit"] - int(
            (a01_ref or {}).get("treatment", {}).get("hit", A01_REFERENCE_HIT)
        ),
        "d1_on_a02_corpus_hit": d1_sum["hit"],
        "note": "A-01 reference from a01 corpus; A-02 primary AB on a02 corpus",
    }

    return {
        "experiment_id": "v3-a02-d2-rerank",
        "flag": "F_V3_RANK_D2_ENABLED",
        "control": {**{k: v for k, v in control.items() if k != "details"}, **c_sum},
        "treatment": {**{k: v for k, v in treatment.items() if k != "details"}, **t_sum},
        "d1_on_a02_corpus": d1_sum,
        "delta": {
            "hit": t_sum["hit"] - c_sum["hit"],
            "purchase": t_sum["purchase"] - c_sum["purchase"],
            "rank710": t_sum["rank710"] - c_sum["rank710"],
            "rank46": t_sum["rank46"] - c_sum["rank46"],
            "other": t_sum["other"] - c_sum["other"],
            "roi": round(t_sum["roi"] - c_sum["roi"], 4),
        },
        "churn_hit": ch,
        "hard_gate": {
            "require_hit_gt": CONTROL_HIT,
            "require_churn_hit_0": True,
            "pass": hard_pass,
        },
        "control_reproduces_218": c_sum["hit"] == CONTROL_HIT and c_sum["n"] == CONTROL_CORPUS_SIZE,
        "comparison": comparison,
        "decision": decision,
        "adopt": hard_pass,
        "taxonomy": taxonomy_snapshot(),
        "ab_metrics": sink.snapshot(),
        "notes": {
            "scope": "Evaluation only (D2 Listwise Reranker)",
            "independent_of": "A-01 D1 Recalibrator",
            "unchanged": [
                "A-01 logic",
                "Representation",
                "Admission",
                "Selection",
                "Purchase",
                "V2 Production",
            ],
            "purchase_def": "hits on purchase_eligible races (Delete-layer excluded)",
            "rank710_def": "misses with winner_rank in 7..10",
            "rank46_def": "misses with winner_rank in 4..6",
            "other_def": "remaining misses",
            "roi_def": f"flat bet {STAKE_YEN}yen/race on top pick; ROI=(return-stake)/stake",
        },
    }


__all__ = [
    "STAKE_YEN",
    "A01_REFERENCE_HIT",
    "build_a02_accuracy_corpus",
    "run_a02_ab",
]
