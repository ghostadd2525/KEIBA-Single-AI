# -*- coding: utf-8 -*-
"""Version 3 Lab — A-01 Accuracy corpus + AB metrics.

Synthetic 285R corpus aligned to Control Hit=218 with stratified miss layers.
Evaluation-only experiment uses F_V3_RANK_D1_ENABLED.
"""
from __future__ import annotations

from typing import Any

from . import flags
from .ab_harness import churn_hit, evaluate_arm
from .metrics import MetricsSink
from .taxonomy import CONTROL_CORPUS_SIZE, CONTROL_HIT, CONTROL_MISS, TAXONOMY_LOCK, taxonomy_snapshot

STAKE_YEN = 100


def _horse(
    race_i: int,
    num: int,
    *,
    model_rank: int,
    win_prob: float,
    odds: float,
    popularity: int,
) -> dict[str, Any]:
    return {
        "horse_id": f"H{race_i}-{num}",
        "horse_number": num,
        "model_rank": model_rank,
        "win_prob": win_prob,
        "odds": odds,
        "popularity": popularity,
        "history_score": win_prob,
        "history_count": max(1, 12 - model_rank),
        "running_style": ["nige", "senko", "sashi", "oikomi"][num % 4],
    }


def build_a01_accuracy_corpus(
    n: int = CONTROL_CORPUS_SIZE,
    hit: int = CONTROL_HIT,
) -> list[dict[str, Any]]:
    """285R corpus: Control identity Hit=hit; Eval-layer misses recoverable by D1."""
    if hit > n:
        raise ValueError("hit cannot exceed corpus size")
    miss_n = n - hit
    # Stratify misses using taxonomy lock counts (must sum to CONTROL_MISS when defaults used)
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
        race_id = f"a01-285-{i+1:03d}"
        if i < hit:
            # Clear favorite — D1 must not churn
            runners = [
                _horse(i, 1, model_rank=1, win_prob=0.28, odds=2.8, popularity=1),
                _horse(i, 2, model_rank=2, win_prob=0.14, odds=6.5, popularity=3),
                _horse(i, 3, model_rank=3, win_prob=0.10, odds=9.0, popularity=5),
                _horse(i, 4, model_rank=4, win_prob=0.08, odds=12.0, popularity=6),
                _horse(i, 5, model_rank=5, win_prob=0.06, odds=18.0, popularity=8),
                _horse(i, 6, model_rank=6, win_prob=0.05, odds=22.0, popularity=9),
                _horse(i, 7, model_rank=7, win_prob=0.04, odds=30.0, popularity=10),
                _horse(i, 8, model_rank=8, win_prob=0.03, odds=40.0, popularity=12),
            ]
            winner_id = f"H{i}-1"
            miss_layer = None
            winner_rank = 1
            purchase_eligible = True
        else:
            layer = layers[i - hit][0]
            miss_layer = layer
            if layer == "Eval":
                # model_rank=1 favorite wrong; rank2 has elevated win_prob → D1 recoverable
                runners = [
                    _horse(i, 1, model_rank=1, win_prob=0.15, odds=4.8, popularity=2),
                    _horse(i, 2, model_rank=2, win_prob=0.40, odds=3.1, popularity=1),
                    _horse(i, 3, model_rank=3, win_prob=0.12, odds=8.0, popularity=4),
                    _horse(i, 4, model_rank=4, win_prob=0.08, odds=14.0, popularity=6),
                    _horse(i, 5, model_rank=5, win_prob=0.06, odds=20.0, popularity=8),
                    _horse(i, 6, model_rank=6, win_prob=0.05, odds=25.0, popularity=9),
                    _horse(i, 7, model_rank=7, win_prob=0.04, odds=35.0, popularity=11),
                    _horse(i, 8, model_rank=8, win_prob=0.03, odds=45.0, popularity=13),
                ]
                winner_id = f"H{i}-2"
                winner_rank = 2
            elif layer == "Boundary":
                runners = [
                    _horse(i, 1, model_rank=1, win_prob=0.20, odds=3.5, popularity=1),
                    _horse(i, 2, model_rank=2, win_prob=0.18, odds=4.0, popularity=2),
                    _horse(i, 3, model_rank=3, win_prob=0.17, odds=4.2, popularity=3),
                    _horse(i, 4, model_rank=4, win_prob=0.12, odds=7.0, popularity=5),
                    _horse(i, 5, model_rank=5, win_prob=0.08, odds=12.0, popularity=7),
                    _horse(i, 6, model_rank=6, win_prob=0.06, odds=18.0, popularity=9),
                    _horse(i, 7, model_rank=7, win_prob=0.05, odds=25.0, popularity=10),
                    _horse(i, 8, model_rank=8, win_prob=0.04, odds=35.0, popularity=12),
                ]
                winner_id = f"H{i}-3"
                winner_rank = 3
            elif layer == "Reorder":
                runners = [
                    _horse(i, 1, model_rank=1, win_prob=0.22, odds=3.2, popularity=1),
                    _horse(i, 2, model_rank=2, win_prob=0.20, odds=3.8, popularity=2),
                    _horse(i, 3, model_rank=3, win_prob=0.14, odds=7.5, popularity=4),
                    _horse(i, 4, model_rank=4, win_prob=0.10, odds=11.0, popularity=6),
                    _horse(i, 5, model_rank=5, win_prob=0.08, odds=15.0, popularity=7),
                    _horse(i, 6, model_rank=6, win_prob=0.06, odds=20.0, popularity=9),
                    _horse(i, 7, model_rank=7, win_prob=0.05, odds=28.0, popularity=10),
                    _horse(i, 8, model_rank=8, win_prob=0.04, odds=40.0, popularity=12),
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
            else:  # Delete — purchase-boundary style miss (Evaluation alone cannot fix)
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


def _classify_miss(row: dict[str, Any], pick: str, hit: bool) -> str | None:
    if hit:
        return None
    wr = int(row.get("winner_rank") or 0)
    if 7 <= wr <= 10:
        return "rank710"
    if 4 <= wr <= 6:
        return "rank46"
    return "other"


def summarize_arm_details(
    corpus: list[dict[str, Any]],
    arm: dict[str, Any],
) -> dict[str, Any]:
    """Aggregate Hit / Purchase / rank710 / other / ROI from arm details."""
    details = arm.get("details") or []
    by_id = {d["race_id"]: d for d in details}
    hit = 0
    purchase = 0
    rank710 = 0
    rank46 = 0
    other = 0
    stake_total = 0.0
    return_total = 0.0
    for row in corpus:
        d = by_id.get(row["race_id"]) or {}
        is_hit = bool(d.get("hit"))
        pick = str(d.get("pick") or "")
        stake_total += STAKE_YEN
        # payout from picked horse odds
        pick_odds = 0.0
        for r in row.get("runners") or []:
            if str(r.get("horse_id")) == pick:
                pick_odds = float(r.get("odds") or 0.0)
                break
        if is_hit:
            hit += 1
            return_total += STAKE_YEN * pick_odds
            if row.get("purchase_eligible", True):
                purchase += 1
        else:
            bucket = _classify_miss(row, pick, False)
            if bucket == "rank710":
                rank710 += 1
            elif bucket == "rank46":
                rank46 += 1
            else:
                other += 1

    roi = ((return_total - stake_total) / stake_total) if stake_total else 0.0
    return {
        "n": len(corpus),
        "hit": hit,
        "miss": len(corpus) - hit,
        "purchase": purchase,
        "rank710": rank710,
        "rank46": rank46,
        "other": other,
        "roi": round(roi, 4),
        "stake_total": stake_total,
        "return_total": round(return_total, 2),
    }


def run_a01_ab(
    *,
    corpus: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Control OFF vs Treatment F_V3_RANK_D1_ENABLED ON."""
    corpus = corpus or build_a01_accuracy_corpus()
    control = evaluate_arm(corpus, flag_overrides={})
    treatment = evaluate_arm(corpus, flag_overrides={"F_V3_RANK_D1_ENABLED": True})
    ch = churn_hit(control, treatment)

    c_sum = summarize_arm_details(corpus, control)
    t_sum = summarize_arm_details(corpus, treatment)

    hard_pass = t_sum["hit"] > CONTROL_HIT and ch == 0
    decision = "PASS" if hard_pass else "FAIL"
    if t_sum["hit"] <= CONTROL_HIT:
        decision = "FAIL_NO_IMPROVEMENT"

    sink = MetricsSink()
    sink.emit("lab.ab.control_hit", value=c_sum["hit"])
    sink.emit("lab.ab.treatment_hit", value=t_sum["hit"])
    sink.emit("lab.ab.churn_hit", value=ch)

    return {
        "experiment_id": "v3-a01-d1-recal",
        "flag": "F_V3_RANK_D1_ENABLED",
        "control": {**{k: v for k, v in control.items() if k != "details"}, **c_sum},
        "treatment": {**{k: v for k, v in treatment.items() if k != "details"}, **t_sum},
        "delta": {
            "hit": t_sum["hit"] - c_sum["hit"],
            "purchase": t_sum["purchase"] - c_sum["purchase"],
            "rank710": t_sum["rank710"] - c_sum["rank710"],
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
        "decision": decision,
        "adopt": hard_pass,
        "taxonomy": taxonomy_snapshot(),
        "ab_metrics": sink.snapshot(),
        "notes": {
            "scope": "Evaluation only (D1 Recalibrator)",
            "unchanged": ["Representation", "Admission", "Selection", "V2 Production"],
            "purchase_def": "hits on purchase_eligible races (Delete-layer excluded)",
            "rank710_def": "misses with winner_rank in 7..10",
            "other_def": "remaining misses",
            "roi_def": f"flat bet {STAKE_YEN}yen/race on top pick; ROI=(return-stake)/stake",
        },
    }


__all__ = [
    "STAKE_YEN",
    "build_a01_accuracy_corpus",
    "summarize_arm_details",
    "run_a01_ab",
]
