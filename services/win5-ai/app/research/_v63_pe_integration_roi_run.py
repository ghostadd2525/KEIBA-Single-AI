# -*- coding: utf-8 -*-
"""Version63 — PE Integration ROI Study (research runner only).

Virtual World→PE policy on frozen 285R rankings.
Does NOT mutate Production / PE / Prediction / Signal / Trigger / Threshold.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from research.world_pe_policy_sim import (
    EXISTING_WORLDS,
    WEIGHTS,
    _safe_div,
    apply_policy,
    miss_bucket,
    normalize_base_scores,
    summarize_arm,
)

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")


def build_races(corp, dual, excl, world_mode: str):
    races = []
    skipped = Counter()
    for race in corp["races"]:
        rid = race["race_id"]
        d = dual.get(rid) or {}
        runners = race.get("runners") or []
        if len(runners) < 3:
            skipped["few_runners"] += 1
            continue
        # Deterministic keys: prefer horse_number; else 1..n by runner order (no hash()).
        rows = []
        for i, u in enumerate(runners):
            hid = str(u.get("horse_id") or "")
            hn = int(u.get("horse_number") or 0)
            if hn <= 0:
                hn = i + 1
            rows.append(
                {
                    "horse_number": hn,
                    "horse_id": hid,
                    "model_rank": int(u["model_rank"]),
                    "win_prob": float(u.get("win_prob") or 0.0),
                }
            )
        used = set()
        for i, r in enumerate(rows):
            if r["horse_number"] in used:
                r["horse_number"] = 1000 + i
            used.add(r["horse_number"])
        id_by_hn = {r["horse_number"]: r["horse_id"] for r in rows}
        norm = normalize_base_scores(
            [{k: r[k] for k in ("horse_number", "model_rank", "win_prob")} for r in rows]
        )
        for r in norm:
            r["horse_id"] = id_by_hn[r["horse_number"]]
        wid = str(race.get("winner_id") or "")
        winner_hn = None
        for r in norm:
            if r["horse_id"] == wid:
                winner_hn = r["horse_number"]
                break
        if winner_hn is None:
            skipped["no_winner"] += 1
            continue

        if world_mode == "legacy":
            world = d.get("legacy_world") or d.get("decision_used")
        elif world_mode == "v44":
            world = d.get("v44_world")
            if world == "unsatisfied" or world not in EXISTING_WORLDS:
                world = None
        elif world_mode == "v44_false_release":
            world = d.get("v44_world")
            ex = excl.get(rid)
            if ex and ex.get("kind") == "false_exclusion":
                world = ex.get("primary_near_world")
            if world == "unsatisfied" or world not in EXISTING_WORLDS:
                world = None
        else:
            raise ValueError(world_mode)

        races.append(
            {
                "race_id": rid,
                "winner_hn": winner_hn,
                "world": world,
                "sub_world": None,
                "base_rows": norm,
                "identity": world is None,
            }
        )
    return races, skipped


def evaluate(races, weight: float):
    race_rows = []
    top1_change = 0
    top3_change = 0
    moves = []
    pair_changes = 0
    world_top1 = Counter()
    world_n = Counter()
    world_base_hit = Counter()
    world_pol_hit = Counter()
    world_hit_delta = Counter()

    for rec in races:
        base = rec["base_rows"]
        world = rec["world"] or "mixed_world"
        sub = rec["sub_world"]
        if rec["identity"] or weight <= 0:
            pol = apply_policy(base, world, sub, 0.0)
        else:
            pol = apply_policy(base, world, sub, weight)

        base_by = {r["horse_number"]: r for r in base}
        pol_by = {r["horse_number"]: r for r in pol}
        base_ord = sorted(base, key=lambda x: (int(x["model_rank"]), x["horse_number"]))
        base_top1 = base_ord[0]["horse_number"]
        pol_top1 = pol[0]["horse_number"]
        base_top3 = {r["horse_number"] for r in base_ord[:3]}
        pol_top3 = {r["horse_number"] for r in pol[:3]}
        t1c = int(base_top1 != pol_top1)
        top1_change += t1c
        top3_change += int(base_top3 != pol_top3)

        abs_moves = []
        for hn, br in base_by.items():
            d = abs(int(pol_by[hn]["policy_rank"]) - int(br["model_rank"]))
            if d:
                pair_changes += 1
            abs_moves.append(d)
            moves.append(d)

        wlabel = rec["world"] or "unsatisfied_identity"
        world_n[wlabel] += 1
        world_top1[wlabel] += t1c
        wh = rec["winner_hn"]
        bwr = int(base_by[wh]["model_rank"])
        pwr = int(pol_by[wh]["policy_rank"])
        bhit = base_top1 == wh
        phit = pol_top1 == wh
        world_base_hit[wlabel] += int(bhit)
        world_pol_hit[wlabel] += int(phit)
        world_hit_delta[wlabel] += int(phit) - int(bhit)
        race_rows.append(
            {
                "hit": phit,
                "purchase": phit,
                "miss": miss_bucket(phit, pwr),
                "base_hit": bhit,
                "base_miss": miss_bucket(bhit, bwr),
                "n_changed": sum(1 for m in abs_moves if m),
            }
        )

    arm = summarize_arm(race_rows)
    base_arm = summarize_arm(
        [{"hit": r["base_hit"], "purchase": r["base_hit"], "miss": r["base_miss"]} for r in race_rows]
    )
    return {
        "weight": weight,
        "baseline": base_arm,
        "policy": arm,
        "delta": {
            k: arm[k] - base_arm[k]
            for k in ["hit", "purchase", "rank46", "rank710", "other_1_3", "other_10_13", "other_miss"]
        },
        "ranking_diff": {
            "races_top1_changed": top1_change,
            "races_top1_change_rate": _safe_div(top1_change, len(races)),
            "races_top3_changed": top3_change,
            "races_top3_change_rate": _safe_div(top3_change, len(races)),
            "mean_horses_rank_changed_per_race": _safe_div(pair_changes, len(races)),
            "mean_abs_candidate_rank_move": (sum(moves) / len(moves)) if moves else None,
            "prediction_rank_changed_races": sum(1 for r in race_rows if r["n_changed"] > 0),
        },
        "world_influence": {
            w: {
                "n": world_n[w],
                "top1_changed": world_top1[w],
                "top1_change_rate": _safe_div(world_top1[w], world_n[w]),
                "base_hit": world_base_hit[w],
                "policy_hit": world_pol_hit[w],
                "hit_delta": world_hit_delta[w],
            }
            for w in sorted(world_n.keys())
        },
    }


def governance(by_weight):
    checks = {}
    for w in WEIGHTS:
        if w == 0:
            continue
        d = by_weight[w]["delta"]
        rd = by_weight[w]["ranking_diff"]
        hit_ok = d["hit"] >= 0
        r710 = d["rank710"] <= 0
        oth = d["other_miss"] <= 0
        meaningful = (rd["races_top1_change_rate"] or 0) >= 0.05 or (
            rd["mean_abs_candidate_rank_move"] or 0
        ) >= 0.15
        checks[str(w)] = {
            "hit_ge_baseline": hit_ok,
            "rank710_not_worse": r710,
            "other_miss_not_worse": oth,
            "meaningful_pe_influence": meaningful,
            "hit_improved": d["hit"] > 0,
            "ni_with_influence": hit_ok and r710 and oth and meaningful,
            "delta": d,
            "top1_change_rate": rd["races_top1_change_rate"],
        }
    any_ni = any(v["ni_with_influence"] for v in checks.values())
    any_up = any(v["hit_improved"] for v in checks.values())
    final = any(v["ni_with_influence"] and v["hit_improved"] for v in checks.values())
    max_d = max(by_weight[w]["delta"]["hit"] for w in WEIGHTS if w > 0)
    if final:
        grade = "A"
        reason = "Some weight: Hit↑ + NI(rank710/other) + meaningful Top1 influence"
    elif any_up and not any_ni:
        grade = "B"
        reason = "Hit↑ exists but NI violated (rank710/other_miss) — ROI limited/unsafe"
    elif any_ni and not any_up:
        grade = "B"
        reason = "NI+influence possible but Hit never improves"
    elif max_d < 0:
        grade = "C"
        reason = f"All weights Hit worse (max ΔHit={max_d})"
    else:
        grade = "C"
        reason = "No Hit lift with NI+influence"
    return {
        "grade": grade,
        "reason": reason,
        "final_pass_roi": final,
        "any_ni": any_ni,
        "any_hit_up": any_up,
        "max_hit_delta": max_d,
        "by_weight": checks,
    }


def main() -> None:
    corp = json.loads(
        (ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(
            encoding="utf-8"
        )
    )
    dual = {
        json.loads(l)["race_id"]: json.loads(l)
        for l in (ROOT / "docs/implementation/w-s1-dual-eval-rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if l.strip()
    }
    excl = {}
    ep = ROOT / "docs/implementation/w-s3-exclusion-104-rows.jsonl"
    if ep.exists():
        for line in ep.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                excl[row["race_id"]] = row

    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fxrows = fx.get("rows") or fx.get("evaluations")
    fixture_hit = sum(1 for x in fxrows if x.get("hit_at_1"))
    pred_eq_winner = 0
    for x in fxrows:
        race = next(r for r in corp["races"] if r["race_id"] == x["race_id"])
        top = min(race["runners"], key=lambda u: int(u.get("model_rank") or 999))
        if str(x.get("predicted_top1_horse_id")) == str(x.get("winner_id")):
            pred_eq_winner += 1
        assert str(x.get("predicted_top1_horse_id")) == str(top.get("horse_id"))

    out = {
        "schema": "v63-pe-integration-roi/1.0",
        "primary_mode": "legacy",
        "integration_point": {
            "current_v35": "Feature→Scorer→Ranker→Prediction; World is post-label only",
            "simulated": "Virtual PE Policy after frozen scores: (1-w)*norm(win_prob)+w*norm(WorldRankKernel)",
            "design_ref": "docs/architecture/v36-world-pe-integration.md (Option C)",
            "kernel_ref": "services/win5-ai/app/research/world_pe_policy_sim.py WORLD_RANK_KERNEL",
        },
        "metric_note": {
            "pe_ranking_hit": "policy/base top1 horse_id == winner_id",
            "fixture_hit_at_1": fixture_hit,
            "predicted_top1_eq_winner": pred_eq_winner,
            "note": (
                "fixture hit_at_1 is NOT identical to top1 correctness; "
                "V63 ROI uses PE ranking Hit only (no speculation on fixture label)."
            ),
            "purchase_proxy": "same as PE ranking hit (V34/V37)",
        },
        "modes": {},
    }

    for mode in ["legacy", "v44", "v44_false_release"]:
        races, skipped = build_races(corp, dual, excl, mode)
        by = {w: evaluate(races, w) for w in WEIGHTS}
        g = governance(by)
        world_dist = Counter((r["world"] or "unsatisfied_identity") for r in races)
        out["modes"][mode] = {
            "n": len(races),
            "skipped": dict(skipped),
            "world_dist": dict(world_dist),
            "baseline_hit": by[0.0]["baseline"]["hit"],
            "by_weight": {str(w): arm for w, arm in by.items()},
            "governance": g,
            "sensitivity": [
                {
                    "weight": w,
                    **by[w]["delta"],
                    "top1_change_rate": by[w]["ranking_diff"]["races_top1_change_rate"],
                    "mean_abs_rank_move": by[w]["ranking_diff"]["mean_abs_candidate_rank_move"],
                }
                for w in WEIGHTS
            ],
        }
        print(
            "MODE",
            mode,
            "n",
            len(races),
            "base_hit",
            by[0.0]["baseline"]["hit"],
            "grade",
            g["grade"],
            g["reason"].encode("ascii", "replace").decode("ascii"),
        )
        for w in WEIGHTS:
            a = by[w]
            rate = a["ranking_diff"]["races_top1_change_rate"] or 0.0
            print(
                "  w={:.0%} hit={} dH={:+d} dP={:+d} d710={:+d} dO={:+d} t1={} ({:.1%})".format(
                    w,
                    a["policy"]["hit"],
                    a["delta"]["hit"],
                    a["delta"]["purchase"],
                    a["delta"]["rank710"],
                    a["delta"]["other_miss"],
                    a["ranking_diff"]["races_top1_changed"],
                    rate,
                )
            )

    path = ROOT / "docs/research/_v63-sim.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    main()
