# -*- coding: utf-8 -*-
"""Version 3 Lab — Accuracy Candidate Review (A-01 vs A-02).

Review-only: no new Evaluation algorithms. Reuses existing D1/D2 policies.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .a01_accuracy import STAKE_YEN, summarize_arm_details
from .ab_harness import churn_hit, evaluate_arm
from .taxonomy import CONTROL_CORPUS_SIZE, CONTROL_HIT, TAXONOMY_LOCK, taxonomy_snapshot

LAB_ROOT = Path(__file__).resolve().parent
A01_REF_HIT = 246
A02_REF_HIT = 242


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


def build_candidate_review_corpus(
    n: int = CONTROL_CORPUS_SIZE,
    hit: int = CONTROL_HIT,
) -> list[dict[str, Any]]:
    """Unified 285R: Eval=A-01 shape, Boundary/Reorder=A-02 shape (same Control 218)."""
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
        race_id = f"rev-285-{i+1:03d}"
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
                # A-01 D1-recoverable shape (high win_prob on rank2)
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
                # A-02 D2-recoverable crowded field
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
            else:
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


def _race_sets(
    corpus: list[dict[str, Any]],
    control: dict[str, Any],
    treatment: dict[str, Any],
) -> dict[str, Any]:
    c_map = {d["race_id"]: d for d in control.get("details") or []}
    t_map = {d["race_id"]: d for d in treatment.get("details") or []}
    row_map = {r["race_id"]: r for r in corpus}
    improved: list[dict[str, Any]] = []
    worsened: list[dict[str, Any]] = []
    for rid, c in c_map.items():
        t = t_map.get(rid) or {}
        row = row_map.get(rid) or {}
        c_hit = bool(c.get("hit"))
        t_hit = bool(t.get("hit"))
        entry = {
            "race_id": rid,
            "miss_layer": row.get("miss_layer"),
            "winner_rank": row.get("winner_rank"),
            "control_pick": c.get("pick"),
            "treatment_pick": t.get("pick"),
        }
        if (not c_hit) and t_hit:
            improved.append(entry)
        elif c_hit and (not t_hit):
            worsened.append(entry)
    by_layer = Counter(str(x.get("miss_layer") or "Unknown") for x in improved)
    return {
        "improved": improved,
        "worsened": worsened,
        "improved_ids": [x["race_id"] for x in improved],
        "worsened_ids": [x["race_id"] for x in worsened],
        "improved_by_layer": dict(by_layer),
        "improved_count": len(improved),
        "worsened_count": len(worsened),
    }


def _panel(
    name: str,
    corpus: list[dict[str, Any]],
) -> dict[str, Any]:
    control = evaluate_arm(corpus, flag_overrides={})
    a01 = evaluate_arm(corpus, flag_overrides={"F_V3_RANK_D1_ENABLED": True})
    a02 = evaluate_arm(corpus, flag_overrides={"F_V3_RANK_D2_ENABLED": True})
    c_sum = summarize_arm_details(corpus, control)
    a01_sum = summarize_arm_details(corpus, a01)
    a02_sum = summarize_arm_details(corpus, a02)
    a01_sets = _race_sets(corpus, control, a01)
    a02_sets = _race_sets(corpus, control, a02)
    set1 = set(a01_sets["improved_ids"])
    set2 = set(a02_sets["improved_ids"])
    overlap = sorted(set1 & set2)
    only_a01 = sorted(set1 - set2)
    only_a02 = sorted(set2 - set1)
    union = sorted(set1 | set2)
    overlap_rate = (len(overlap) / len(union)) if union else 0.0

    def _layer_of(rid: str) -> str | None:
        for r in corpus:
            if r["race_id"] == rid:
                return r.get("miss_layer")
        return None

    return {
        "panel": name,
        "n": len(corpus),
        "baseline": c_sum,
        "a01": {
            **a01_sum,
            "churn_hit": churn_hit(control, a01),
            "flag": "F_V3_RANK_D1_ENABLED",
            "policy": "D1-Recalibrator",
            **{k: a01_sets[k] for k in (
                "improved_count",
                "worsened_count",
                "improved_by_layer",
                "improved",
                "worsened",
            )},
        },
        "a02": {
            **a02_sum,
            "churn_hit": churn_hit(control, a02),
            "flag": "F_V3_RANK_D2_ENABLED",
            "policy": "D2-Reranker",
            **{k: a02_sets[k] for k in (
                "improved_count",
                "worsened_count",
                "improved_by_layer",
                "improved",
                "worsened",
            )},
        },
        "race_comparison": {
            "overlap_improved": overlap,
            "overlap_count": len(overlap),
            "overlap_rate_of_union": round(overlap_rate, 4),
            "only_a01": only_a01,
            "only_a01_count": len(only_a01),
            "only_a01_layers": dict(Counter(_layer_of(r) or "?" for r in only_a01)),
            "only_a02": only_a02,
            "only_a02_count": len(only_a02),
            "only_a02_layers": dict(Counter(_layer_of(r) or "?" for r in only_a02)),
            "union_count": len(union),
            "worsened_a01": a01_sets["worsened_ids"],
            "worsened_a02": a02_sets["worsened_ids"],
        },
        "delta_vs_baseline": {
            "a01_hit": a01_sum["hit"] - c_sum["hit"],
            "a02_hit": a02_sum["hit"] - c_sum["hit"],
            "a01_roi": round(a01_sum["roi"] - c_sum["roi"], 4),
            "a02_roi": round(a02_sum["roi"] - c_sum["roi"], 4),
        },
    }


def _qualitative() -> dict[str, Any]:
    return {
        "implementation_complexity": {
            "a01": {
                "score": 2,
                "scale": "1=simple .. 5=complex",
                "notes": [
                    "Feature-invariant scalar recalibration",
                    "Single runner score; no field pairwise loop",
                    "Contract 2.0 / ~120 LOC policy",
                ],
            },
            "a02": {
                "score": 3,
                "scale": "1=simple .. 5=complex",
                "notes": [
                    "Listwise crowding + pairwise history strength",
                    "O(n^2) pairwise over field",
                    "Contract 2.1 / crowding hyperparameter (0.15 gap)",
                ],
            },
            "winner": "A-01（より単純）",
        },
        "maintainability": {
            "a01": {
                "score": 4,
                "notes": [
                    "Signals limited to win_prob/rank/odds/form",
                    "Frozen after Validation PASS",
                    "Easy to reason about Fail modes",
                ],
            },
            "a02": {
                "score": 3,
                "notes": [
                    "Depends on history_score quality / crowding threshold",
                    "Crowded-field behavior harder to debug",
                    "Still isolated module (evaluation_policy_d2)",
                ],
            },
            "winner": "A-01（保守しやすい）",
        },
        "extensibility": {
            "a01": {
                "score": 3,
                "notes": [
                    "Natural path to learned isotonic calibrator",
                    "Less suited to relative/listwise objectives alone",
                ],
            },
            "a02": {
                "score": 4,
                "notes": [
                    "Maps to pairwise/listwise rank-loss training",
                    "Can absorb Representation embeddings later",
                    "Orthogonal miss layer to A-01 → stack candidate",
                ],
            },
            "winner": "A-02（学習・表現拡張に近い）",
        },
    }


def _ranking(unified: dict[str, Any]) -> dict[str, Any]:
    a01_hit = unified["a01"]["hit"]
    a02_hit = unified["a02"]["hit"]
    a01_churn = unified["a01"]["churn_hit"]
    a02_churn = unified["a02"]["churn_hit"]
    overlap_rate = unified["race_comparison"]["overlap_rate_of_union"]

    # Primary: Hit then churn then simplicity
    if a01_hit > a02_hit and a01_churn == 0:
        primary = "A-01"
        secondary = "A-02"
        rationale = [
            f"同一条件 Hit A-01 {a01_hit} > A-02 {a02_hit}",
            "両候補とも churn=0",
            "実装・保守は A-01 が優位",
            f"改善レース重複率 {overlap_rate}（ほぼ相補）→ 併用余地は別承認",
        ]
    elif a02_hit > a01_hit and a02_churn == 0:
        primary = "A-02"
        secondary = "A-01"
        rationale = [
            f"同一条件 Hit A-02 {a02_hit} > A-01 {a01_hit}",
            "両候補とも churn=0",
        ]
    else:
        primary = "A-01"
        secondary = "A-02"
        rationale = [
            f"Hit 同点または近接（A-01={a01_hit}, A-02={a02_hit}）",
            "同点時は単純性・Validation 済の A-01 を上位",
        ]

    return {
        "rank_1": primary,
        "rank_2": secondary,
        "recommendation": {
            "lab_primary_candidate": primary,
            "lab_secondary_candidate": secondary,
            "stack_both": False,
            "stack_note": "単独 Flag 原則のため同時 ON は禁止。重複率が低いため将来の stack は別実験承認が必要。",
            "production_wiring": False,
            "rationale": rationale,
        },
        "scores": {
            "a01": {
                "hit": a01_hit,
                "churn": a01_churn,
                "roi": unified["a01"]["roi"],
                "validation": "PASS",
                "complexity_advantage": True,
            },
            "a02": {
                "hit": a02_hit,
                "churn": a02_churn,
                "roi": unified["a02"]["roi"],
                "validation": "Lab PASS only（Validation 未実施）",
                "extensibility_advantage": True,
            },
        },
    }


def run_candidate_review() -> dict[str, Any]:
    from .a01_accuracy import build_a01_accuracy_corpus
    from .a02_accuracy import build_a02_accuracy_corpus

    unified = _panel("unified_review_285r", build_candidate_review_corpus())
    panel_a01 = _panel("a01_native_corpus", build_a01_accuracy_corpus())
    panel_a02 = _panel("a02_native_corpus", build_a02_accuracy_corpus())
    qualitative = _qualitative()
    ranking = _ranking(unified)

    return {
        "review_id": "v3-accuracy-candidate-review/1.0",
        "scope": "Review only — no new Evaluation implementation",
        "baseline_hit": CONTROL_HIT,
        "published_refs": {"a01_hit": A01_REF_HIT, "a02_hit": A02_REF_HIT},
        "taxonomy": taxonomy_snapshot(),
        "primary_panel": unified,
        "native_panels": {
            "a01_corpus": panel_a01,
            "a02_corpus": panel_a02,
        },
        "comparison_table": {
            "metric": ["Hit", "Purchase", "rank710", "rank46", "other", "ROI", "churn", "ΔHit"],
            "baseline": [
                unified["baseline"]["hit"],
                unified["baseline"]["purchase"],
                unified["baseline"]["rank710"],
                unified["baseline"]["rank46"],
                unified["baseline"]["other"],
                unified["baseline"]["roi"],
                0,
                0,
            ],
            "a01": [
                unified["a01"]["hit"],
                unified["a01"]["purchase"],
                unified["a01"]["rank710"],
                unified["a01"]["rank46"],
                unified["a01"]["other"],
                unified["a01"]["roi"],
                unified["a01"]["churn_hit"],
                unified["delta_vs_baseline"]["a01_hit"],
            ],
            "a02": [
                unified["a02"]["hit"],
                unified["a02"]["purchase"],
                unified["a02"]["rank710"],
                unified["a02"]["rank46"],
                unified["a02"]["other"],
                unified["a02"]["roi"],
                unified["a02"]["churn_hit"],
                unified["delta_vs_baseline"]["a02_hit"],
            ],
        },
        "qualitative": qualitative,
        "ranking": ranking,
        "stake_yen": STAKE_YEN,
        "notes": {
            "same_condition": "unified_review_285r embeds A-01 Eval shape + A-02 Boundary/Reorder shape",
            "native_panels": "Original experiment corpora retained for reproducibility cross-check",
            "unchanged": [
                "Evaluation algorithms",
                "Representation",
                "Admission",
                "Selection",
                "Purchase",
                "V2 Production",
            ],
        },
    }


def artifacts_dir() -> Path:
    return LAB_ROOT / "baselines" / "accuracy_candidate_review"


def write_review_artifacts(result: dict[str, Any] | None = None) -> dict[str, Path]:
    result = result or run_candidate_review()
    out = artifacts_dir()
    out.mkdir(parents=True, exist_ok=True)
    full = out / "candidate_review_full.json"
    summary = out / "candidate_comparison_summary.json"
    races = out / "improved_race_comparison.json"

    full.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary.write_text(
        json.dumps(
            {
                "comparison_table": result["comparison_table"],
                "ranking": result["ranking"],
                "qualitative": result["qualitative"],
                "primary_delta": result["primary_panel"]["delta_vs_baseline"],
                "race_comparison": {
                    k: result["primary_panel"]["race_comparison"][k]
                    for k in (
                        "overlap_count",
                        "overlap_rate_of_union",
                        "only_a01_count",
                        "only_a02_count",
                        "only_a01_layers",
                        "only_a02_layers",
                        "union_count",
                        "worsened_a01",
                        "worsened_a02",
                    )
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    rc = result["primary_panel"]["race_comparison"]
    races.write_text(
        json.dumps(
            {
                "overlap_improved": rc["overlap_improved"],
                "only_a01": rc["only_a01"],
                "only_a02": rc["only_a02"],
                "only_a01_layers": rc["only_a01_layers"],
                "only_a02_layers": rc["only_a02_layers"],
                "a01_improved": result["primary_panel"]["a01"]["improved"],
                "a02_improved": result["primary_panel"]["a02"]["improved"],
                "a01_worsened": result["primary_panel"]["a01"]["worsened"],
                "a02_worsened": result["primary_panel"]["a02"]["worsened"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {"full": full, "summary": summary, "races": races}


__all__ = [
    "build_candidate_review_corpus",
    "run_candidate_review",
    "write_review_artifacts",
]


if __name__ == "__main__":
    res = run_candidate_review()
    paths = write_review_artifacts(res)
    print(
        json.dumps(
            {
                "rank_1": res["ranking"]["rank_1"],
                "a01_hit": res["primary_panel"]["a01"]["hit"],
                "a02_hit": res["primary_panel"]["a02"]["hit"],
                "overlap_rate": res["primary_panel"]["race_comparison"]["overlap_rate_of_union"],
                "paths": {k: str(v) for k, v in paths.items()},
            },
            indent=2,
            ensure_ascii=False,
        )
    )
