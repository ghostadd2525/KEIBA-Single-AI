# -*- coding: utf-8 -*-
"""Version 3 Lab — A-03 Accuracy corpus + AB (Pool Coverage Admission).

Admission-only intervention. Evaluation / Selection / Purchase / Representation
logic unchanged. Hard Gate: incremental on A-01 Primary (Hit > 246, churn=0).
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from .a01_accuracy import summarize_arm_details
from .ab_harness import churn_hit, evaluate_arm
from .metrics import MetricsSink
from .taxonomy import CONTROL_CORPUS_SIZE, CONTROL_HIT, TAXONOMY_LOCK, taxonomy_snapshot

STAKE_YEN = 100
A01_PRIMARY_HIT = 246
POOL_TARGET = TAXONOMY_LOCK["Pool"]  # 9


def _horse(
    race_i: int,
    num: int,
    *,
    model_rank: int,
    win_prob: float,
    odds: float,
    popularity: int,
    history_score: float | None = None,
    running_style: str | None = None,
) -> dict[str, Any]:
    hist = win_prob if history_score is None else history_score
    style = running_style or ["nige", "senko", "sashi", "oikomi"][num % 4]
    return {
        "horse_id": f"H{race_i}-{num}",
        "horse_number": num,
        "model_rank": model_rank,
        "win_prob": win_prob,
        "odds": odds,
        "popularity": popularity,
        "history_score": hist,
        "history_count": max(1, 12 - model_rank),
        "running_style": style,
    }


def build_a03_accuracy_corpus(
    n: int = CONTROL_CORPUS_SIZE,
    hit: int = CONTROL_HIT,
) -> list[dict[str, Any]]:
    """285R: Control 218; Eval=A-01 shape; Boundary/Reorder=A-02 shape; Pool=A-03 shape."""
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
    pool_i = 0
    for i in range(n):
        race_id = f"a03-285-{i+1:03d}"
        if i < hit:
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
                runners = [
                    _horse(i, 1, model_rank=1, win_prob=0.15, odds=4.8, popularity=2, history_score=0.15),
                    _horse(i, 2, model_rank=2, win_prob=0.40, odds=3.1, popularity=1, history_score=0.40),
                    _horse(i, 3, model_rank=3, win_prob=0.12, odds=8.0, popularity=4, history_score=0.12),
                    _horse(i, 4, model_rank=4, win_prob=0.08, odds=14.0, popularity=6, history_score=0.08),
                    _horse(i, 5, model_rank=5, win_prob=0.06, odds=20.0, popularity=8, history_score=0.06),
                    _horse(i, 6, model_rank=6, win_prob=0.05, odds=25.0, popularity=9, history_score=0.05),
                    _horse(i, 7, model_rank=7, win_prob=0.04, odds=35.0, popularity=11, history_score=0.04),
                    _horse(i, 8, model_rank=8, win_prob=0.03, odds=45.0, popularity=13, history_score=0.03),
                ]
                winner_id = f"H{i}-2"
                winner_rank = 2
            elif layer == "Boundary":
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
                # Large field; core styles homogeneous; deep winner unique style (A-03 coverage)
                win_rank = 8 + (pool_i % 3)
                pool_i += 1
                runners = []
                for num in range(1, 13):
                    if num <= 6:
                        runners.append(
                            _horse(
                                i,
                                num,
                                model_rank=num,
                                win_prob=0.24 - 0.02 * (num - 1),
                                odds=3.0 + num,
                                popularity=num,
                                history_score=0.24 - 0.02 * (num - 1),
                                running_style="senko",
                            )
                        )
                    elif num == win_rank:
                        runners.append(
                            _horse(
                                i,
                                num,
                                model_rank=num,
                                win_prob=0.055,
                                odds=40.0,
                                popularity=14,
                                history_score=0.08,
                                running_style="oikomi",
                            )
                        )
                    else:
                        runners.append(
                            _horse(
                                i,
                                num,
                                model_rank=num,
                                win_prob=0.03,
                                odds=50.0 + num,
                                popularity=15 + (num % 3),
                                history_score=0.03,
                                running_style="senko",
                            )
                        )
                winner_id = f"H{i}-{win_rank}"
                winner_rank = win_rank
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


def run_a03_ab(
    *,
    corpus: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """A-03 AB.

    Attribution arm: OFF vs A-03 only (Pool recovery).
    Hard Gate arm: A-01 vs A-01+A-03 (Hit > 246, churn=0).
    """
    corpus = corpus or build_a03_accuracy_corpus()

    baseline = evaluate_arm(corpus, flag_overrides={})
    a03_only = evaluate_arm(corpus, flag_overrides={"F_V3_A03_POOL_ADMIT_ENABLED": True})
    a01_only = evaluate_arm(corpus, flag_overrides={"F_V3_RANK_D1_ENABLED": True})
    a01_a03 = evaluate_arm(
        corpus,
        flag_overrides={
            "F_V3_RANK_D1_ENABLED": True,
            "F_V3_A03_POOL_ADMIT_ENABLED": True,
        },
    )

    b_sum = summarize_arm_details(corpus, baseline)
    t_attr = summarize_arm_details(corpus, a03_only)
    c_gate = summarize_arm_details(corpus, a01_only)
    t_gate = summarize_arm_details(corpus, a01_a03)

    ch_attr = churn_hit(baseline, a03_only)
    ch_gate = churn_hit(a01_only, a01_a03)
    races_attr = _improved_worsened(corpus, baseline, a03_only)
    races_gate = _improved_worsened(corpus, a01_only, a01_a03)

    hard_pass = t_gate["hit"] > A01_PRIMARY_HIT and ch_gate == 0
    decision = "PASS" if hard_pass else "FAIL"
    if t_gate["hit"] <= A01_PRIMARY_HIT:
        decision = "FAIL_NO_IMPROVEMENT"

    sink = MetricsSink()
    sink.emit("lab.ab.control_hit", value=c_gate["hit"])
    sink.emit("lab.ab.treatment_hit", value=t_gate["hit"])
    sink.emit("lab.ab.churn_hit", value=ch_gate)
    sink.emit("lab.ab.a03.hit", value=t_gate["hit"])

    return {
        "experiment_id": "v3-a03-pool-coverage",
        "flag": "F_V3_A03_POOL_ADMIT_ENABLED",
        "stage": "Admission",
        "policy_id": "AP-V3-A03-pool-coverage",
        "baseline": b_sum,
        "a03_only": {**t_attr, "churn_vs_baseline": ch_attr, **races_attr},
        "control": {**{k: v for k, v in a01_only.items() if k != "details"}, **c_gate},
        "treatment": {**{k: v for k, v in a01_a03.items() if k != "details"}, **t_gate},
        "delta": {
            "hit": t_gate["hit"] - c_gate["hit"],
            "purchase": t_gate["purchase"] - c_gate["purchase"],
            "rank710": t_gate["rank710"] - c_gate["rank710"],
            "rank46": t_gate["rank46"] - c_gate["rank46"],
            "other": t_gate["other"] - c_gate["other"],
            "roi": round(t_gate["roi"] - c_gate["roi"], 4),
        },
        "churn_hit": ch_gate,
        "improved_races": races_gate["improved"],
        "worsened_races": races_gate["worsened"],
        "hard_gate": {
            "require_hit_gt": A01_PRIMARY_HIT,
            "require_churn_hit_0": True,
            "control_definition": "A-01 Primary ON (Hit 246 path)",
            "treatment_definition": "A-01 ON + A-03 Admission ON",
            "pass": hard_pass,
        },
        "control_reproduces_a01_246": c_gate["hit"] == A01_PRIMARY_HIT,
        "pool_attribution": {
            "a03_only_hit": t_attr["hit"],
            "baseline_hit": b_sum["hit"],
            "delta_hit": t_attr["hit"] - b_sum["hit"],
            "expected_pool": POOL_TARGET,
            "improved_layers": dict(
                Counter(str(x.get("miss_layer")) for x in races_attr["improved"])
            ),
        },
        "decision": decision,
        "adopt": hard_pass,
        "taxonomy": taxonomy_snapshot(),
        "ab_metrics": sink.snapshot(),
        "notes": {
            "scope": "Admission only (Pool Coverage Deep Promote)",
            "unchanged": [
                "Evaluation logic",
                "Representation",
                "Selection",
                "Purchase",
                "A-01/A-02 policy modules",
                "V2 Production",
            ],
            "delete_excluded": True,
            "roi_def": f"flat bet {STAKE_YEN}yen/race on top pick; ROI=(return-stake)/stake",
        },
    }


__all__ = [
    "STAKE_YEN",
    "A01_PRIMARY_HIT",
    "build_a03_accuracy_corpus",
    "run_a03_ab",
]
