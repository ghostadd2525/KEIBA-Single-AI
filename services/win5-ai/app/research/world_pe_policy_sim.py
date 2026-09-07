# -*- coding: utf-8 -*-
"""Version37 — World→PE Policy Simulation (research only).

Virtual PE Policy Layer on frozen Production rankings.
Does NOT mutate Prediction / PE / CE / AI / World / Production / Signal Service.
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "expect-world-pe-policy-sim/1.0"
WEIGHTS = (0.0, 0.25, 0.50, 0.75, 1.0)
EXISTING_WORLDS = (
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
    "bug_world",
    "mixed_world",
)

# Design-aligned rank preference kernels (baseline model_rank → affinity in [0,1])
# Peak indicates where that World "wants" candidates relative to PE baseline order.
WORLD_RANK_KERNEL: dict[str, dict[str, Any]] = {
    "core_world": {"peaks": [1, 2], "sigma": 1.2, "desc": "favor top favorites"},
    "midupper_world": {"peaks": [2, 3, 4, 5], "sigma": 1.5, "desc": "favor mid-upper"},
    "midhole_world": {"peaks": [5, 6, 7, 8], "sigma": 1.6, "desc": "favor mid-hole"},
    "rank7_world": {"peaks": [6, 7, 8, 9], "sigma": 1.4, "desc": "favor ~rank7 band"},
    "bug_world": {"peaks": [10, 11, 12, 13, 14, 15], "sigma": 2.0, "desc": "favor deep longshots"},
    "mixed_world": {"peaks": [3, 4, 5, 6, 7], "sigma": 2.2, "desc": "broad mid blend"},
}

# SubWorld soft modifiers on kernel peaks (shift preference)
SUBWORLD_SHIFT: dict[str, int] = {
    "midupper_route": 0,
    "midupper_spread": 1,
    "midupper_corelike": -1,
    "core_under": 1,
    "fallback_standard": 0,
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _f(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        x = float(v)
        if math.isnan(x):
            return None
        return x
    except (TypeError, ValueError):
        return None


def _i(v: Any) -> int | None:
    try:
        if v is None or v == "":
            return None
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _safe_div(a: float, b: float) -> float | None:
    if not b:
        return None
    return a / b


def _pct(x: float | None) -> str:
    if x is None:
        return "n/a"
    return f"{100.0 * x:.1f}%"


def _gauss(rank: int, peak: int, sigma: float) -> float:
    return math.exp(-0.5 * ((rank - peak) / max(sigma, 1e-6)) ** 2)


def world_affinity(rank: int, world: str, sub_world: str | None) -> float:
    spec = WORLD_RANK_KERNEL.get(world) or WORLD_RANK_KERNEL["mixed_world"]
    shift = SUBWORLD_SHIFT.get(str(sub_world or ""), 0)
    peaks = [max(1, p + shift) for p in spec["peaks"]]
    sigma = float(spec["sigma"])
    return max(_gauss(rank, p, sigma) for p in peaks)


def extract_runners(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    for path in (
        ("runners",),
        ("candidates",),
        ("evaluation", "runners"),
        ("evaluation", "candidates"),
    ):
        cur: Any = bundle
        ok = True
        for k in path:
            if not isinstance(cur, dict) or k not in cur:
                ok = False
                break
            cur = cur[k]
        if ok and isinstance(cur, list) and cur:
            return [r for r in cur if isinstance(r, dict)]
    return []


def extract_world(bundle: dict[str, Any], signals: dict[str, Any] | None = None) -> tuple[str | None, str | None]:
    ev = bundle.get("evaluation") if isinstance(bundle.get("evaluation"), dict) else {}
    world = ev.get("world") or bundle.get("world")
    sub = ev.get("sub_world") or bundle.get("sub_world")
    if signals:
        world = world or signals.get("world")
        sub = sub or signals.get("sub_world")
    world_s = str(world).strip() if world else None
    sub_s = str(sub).strip() if sub else None
    if world_s in ("", "None", "null", "dummy_world"):
        world_s = None
    if sub_s in ("", "None", "null", "dummy_sub"):
        sub_s = None
    return world_s, sub_s


def normalize_base_scores(runners: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for r in runners:
        hn = _i(r.get("horse_number"))
        if hn is None:
            continue
        mr = _i(r.get("model_rank")) or _i(r.get("rank"))
        wp = _f(r.get("win_prob"))
        rows.append(
            {
                "horse_number": hn,
                "model_rank": mr,
                "win_prob": wp if wp is not None else 0.0,
                "horse_name": r.get("horse_name"),
                "mark": r.get("mark"),
            }
        )
    # fill missing ranks from win_prob order
    if any(x["model_rank"] is None for x in rows):
        ordered = sorted(rows, key=lambda x: (-x["win_prob"], x["horse_number"]))
        for i, x in enumerate(ordered, 1):
            if x["model_rank"] is None:
                x["model_rank"] = i
    # if win_prob all zero, synthesize from rank
    if not any(x["win_prob"] > 0 for x in rows):
        n = len(rows)
        for x in rows:
            rk = int(x["model_rank"] or n)
            x["win_prob"] = max(1e-6, (n + 1 - rk) / float(n * (n + 1) / 2))
    return rows


def apply_policy(
    rows: list[dict[str, Any]],
    world: str,
    sub_world: str | None,
    weight: float,
) -> list[dict[str, Any]]:
    """Virtual PE policy: blend baseline win_prob with World rank-affinity.

    weight==0 is an identity map on Production model_rank (not a win_prob re-sort).
    """
    raw_base = [max(0.0, float(r["win_prob"])) for r in rows]
    sbase = sum(raw_base) or 1.0
    affinities = [world_affinity(int(r["model_rank"]), world, sub_world) for r in rows]
    saff = sum(affinities) or 1.0

    if weight <= 0.0:
        scored = []
        for r, b, a in zip(rows, raw_base, affinities):
            scored.append(
                {
                    **r,
                    "base_norm": b / sbase,
                    "affinity": a,
                    "affinity_norm": a / saff,
                    "policy_score": b / sbase,
                    "policy_rank": int(r["model_rank"]),
                }
            )
        scored.sort(key=lambda x: (int(x["policy_rank"]), x["horse_number"]))
        return scored

    scored = []
    for r, b, a in zip(rows, raw_base, affinities):
        bn = b / sbase
        an = a / saff
        policy = (1.0 - weight) * bn + weight * an
        scored.append({**r, "base_norm": bn, "affinity": a, "affinity_norm": an, "policy_score": policy})
    scored.sort(key=lambda x: (-x["policy_score"], x["horse_number"]))
    for i, r in enumerate(scored, 1):
        r["policy_rank"] = i
    return scored


def miss_bucket(hit: bool, winner_rank: int | None) -> str:
    if hit:
        return "hit"
    wr = winner_rank if winner_rank is not None else 999
    if 4 <= wr <= 6:
        return "rank46"
    if 7 <= wr <= 10:
        return "rank710"
    if 2 <= wr <= 3:
        return "other_1_3"
    if 11 <= wr <= 13:
        return "other_10_13"
    return "other"


def load_races(db_path: Path) -> list[dict[str, Any]]:
    import sqlite3

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    corpus = con.execute(
        """
        SELECT race_id, prediction_id, winner_horse_number, prediction_pick, snapshot_id
        FROM research_prediction_corpus
        WHERE has_race_result = 1
          AND winner_horse_number IS NOT NULL
          AND prediction_pick IS NOT NULL
        """
    ).fetchall()
    preds = {
        int(r["id"]): json.loads(r["bundle_json"] or "{}")
        for r in con.execute("SELECT id, bundle_json FROM predictions").fetchall()
        if r["bundle_json"]
    }
    snaps = {}
    for r in con.execute("SELECT race_id, payload_json FROM research_prediction_snapshots").fetchall():
        try:
            snaps[str(r["race_id"])] = json.loads(r["payload_json"] or "{}")
        except Exception:
            pass

    out = []
    for row in corpus:
        pid = row["prediction_id"]
        if pid is None or int(pid) not in preds:
            continue
        bundle = preds[int(pid)]
        runners = extract_runners(bundle)
        if len(runners) < 3:
            continue
        # skip sample/dummy horses
        if any(str(r.get("horse_name") or "").startswith("サンプル") for r in runners):
            continue
        snap = snaps.get(str(row["race_id"])) or {}
        signals = ((snap.get("research_world_signals") or {}).get("signals")) or {}
        world, sub = extract_world(bundle, signals if isinstance(signals, dict) else None)
        if world not in EXISTING_WORLDS:
            # fallback: midupper if unlabeled but real runners (production saturation)
            world = "midupper_world"
            world_source = "fallback_midupper"
        else:
            world_source = "bundle_or_signals"
        base_rows = normalize_base_scores(runners)
        winner = _i(row["winner_horse_number"])
        pick = _i(row["prediction_pick"])
        if winner is None or pick is None:
            continue
        out.append(
            {
                "race_id": str(row["race_id"]),
                "prediction_id": int(pid),
                "winner": winner,
                "production_pick": pick,
                "world": world,
                "sub_world": sub,
                "world_source": world_source,
                "base_rows": base_rows,
            }
        )
    con.close()
    return out


def summarize_arm(rows: list[dict[str, Any]], prefix: str = "") -> dict[str, Any]:
    n = len(rows)
    hits = sum(1 for r in rows if r["hit"])
    purch = sum(1 for r in rows if r["purchase"])
    buckets = Counter(r["miss"] for r in rows)
    return {
        "n": n,
        "hit": hits,
        "hit_rate": _safe_div(hits, n),
        "purchase": purch,
        "purchase_rate": _safe_div(purch, n),
        "rank46": buckets.get("rank46", 0),
        "rank710": buckets.get("rank710", 0),
        "other_1_3": buckets.get("other_1_3", 0),
        "other_10_13": buckets.get("other_10_13", 0),
        "other": buckets.get("other", 0),
        "other_miss": buckets.get("other_1_3", 0) + buckets.get("other_10_13", 0) + buckets.get("other", 0),
    }


def evaluate_weight(races: list[dict[str, Any]], weight: float) -> dict[str, Any]:
    race_rows = []
    pair_rank_changes = 0
    candidate_moves = []
    top1_change = 0
    top3_change = 0
    world_rank_delta = defaultdict(list)
    sub_rank_delta = defaultdict(list)
    world_top1_change = Counter()
    world_n = Counter()

    for rec in races:
        world = rec["world"]
        sub = rec["sub_world"]
        base = rec["base_rows"]
        base_by_hn = {r["horse_number"]: r for r in base}
        base_order = sorted(base, key=lambda x: (int(x["model_rank"]), x["horse_number"]))
        base_top1 = base_order[0]["horse_number"]
        base_top3 = {r["horse_number"] for r in base_order[:3]}

        pol = apply_policy(base, world, sub, weight)
        pol_by_hn = {r["horse_number"]: r for r in pol}
        pol_top1 = pol[0]["horse_number"]
        pol_top3 = {r["horse_number"] for r in pol[:3]}

        # ranking diffs
        changed_pairs = 0
        abs_moves = []
        for hn, br in base_by_hn.items():
            pr = pol_by_hn[hn]
            d = abs(int(pr["policy_rank"]) - int(br["model_rank"]))
            if d:
                changed_pairs += 1
            abs_moves.append(d)
            candidate_moves.append(d)
        pair_rank_changes += changed_pairs
        mean_move = sum(abs_moves) / len(abs_moves) if abs_moves else 0.0

        t1c = int(base_top1 != pol_top1)
        t3c = int(base_top3 != pol_top3)
        top1_change += t1c
        top3_change += t3c
        world_n[world] += 1
        world_top1_change[world] += t1c
        world_rank_delta[world].append(mean_move)
        if sub:
            sub_rank_delta[str(sub)].append(mean_move)

        winner = rec["winner"]
        # Baseline uses production frozen ranking (model_rank), NOT production_pick mismatch
        base_winner_rank = int(base_by_hn[winner]["model_rank"]) if winner in base_by_hn else None
        pol_winner_rank = int(pol_by_hn[winner]["policy_rank"]) if winner in pol_by_hn else None
        base_hit = bool(base_top1 == winner)
        pol_hit = bool(pol_top1 == winner)
        # Purchase proxy (same as V34): top1 hit
        base_purchase = base_hit
        pol_purchase = pol_hit

        race_rows.append(
            {
                "race_id": rec["race_id"],
                "world": world,
                "sub_world": sub,
                "weight": weight,
                "base_top1": base_top1,
                "policy_top1": pol_top1,
                "top1_changed": bool(t1c),
                "top3_changed": bool(t3c),
                "n_horses_rank_changed": changed_pairs,
                "mean_abs_rank_move": mean_move,
                "winner": winner,
                "base_winner_rank": base_winner_rank,
                "policy_winner_rank": pol_winner_rank,
                "hit": pol_hit,
                "purchase": pol_purchase,
                "miss": miss_bucket(pol_hit, pol_winner_rank),
                "base_hit": base_hit,
                "base_miss": miss_bucket(base_hit, base_winner_rank),
            }
        )

    arm = summarize_arm(race_rows)
    base_arm = summarize_arm(
        [
            {
                "hit": r["base_hit"],
                "purchase": r["base_hit"],
                "miss": r["base_miss"],
            }
            for r in race_rows
        ]
    )

    return {
        "weight": weight,
        "baseline": base_arm,
        "policy": arm,
        "delta": {
            "hit": arm["hit"] - base_arm["hit"],
            "purchase": arm["purchase"] - base_arm["purchase"],
            "rank46": arm["rank46"] - base_arm["rank46"],
            "rank710": arm["rank710"] - base_arm["rank710"],
            "other_1_3": arm["other_1_3"] - base_arm["other_1_3"],
            "other_10_13": arm["other_10_13"] - base_arm["other_10_13"],
            "other_miss": arm["other_miss"] - base_arm["other_miss"],
        },
        "ranking_diff": {
            "races_top1_changed": top1_change,
            "races_top1_change_rate": _safe_div(top1_change, len(races)),
            "races_top3_changed": top3_change,
            "races_top3_change_rate": _safe_div(top3_change, len(races)),
            "mean_horses_rank_changed_per_race": _safe_div(pair_rank_changes, len(races)),
            "mean_abs_candidate_rank_move": (sum(candidate_moves) / len(candidate_moves))
            if candidate_moves
            else None,
            "prediction_rank_changed_races": sum(1 for r in race_rows if r["n_horses_rank_changed"] > 0),
        },
        "world_influence": {
            w: {
                "n": world_n[w],
                "top1_changed": world_top1_change[w],
                "top1_change_rate": _safe_div(world_top1_change[w], world_n[w]),
                "mean_abs_rank_move": (sum(world_rank_delta[w]) / len(world_rank_delta[w]))
                if world_rank_delta[w]
                else None,
            }
            for w in EXISTING_WORLDS
            if world_n[w]
        },
        "subworld_influence": {
            s: {
                "n": len(vals),
                "mean_abs_rank_move": sum(vals) / len(vals),
            }
            for s, vals in sorted(sub_rank_delta.items(), key=lambda kv: -len(kv[1]))
        },
        "race_rows": race_rows,
    }


def safety_analysis(by_weight: dict[float, dict[str, Any]], races: list[dict[str, Any]]) -> dict[str, Any]:
    world_dist = Counter(r["world"] for r in races)
    n = len(races)
    design_share = {
        "core_world": 0.30,
        "midupper_world": 0.35,
        "rank7_world": 0.15,
        "mixed_world": 0.10,
        "bug_world": 0.05,
        "midhole_world": 0.05,
    }
    saturation = {
        w: {
            "observed_share": _safe_div(world_dist[w], n),
            "design_share": design_share.get(w),
            "delta_vs_design": (_safe_div(world_dist[w], n) or 0) - design_share.get(w, 0),
        }
        for w in EXISTING_WORLDS
        if world_dist[w] or w in design_share
    }
    # Bias: does increasing weight monotonically move hits only via dominant world?
    mid_share = _safe_div(world_dist.get("midupper_world", 0), n) or 0.0
    # Overfit proxy: at w=1.0, fraction of races where policy_top1 is NOT baseline top1
    # AND hit worsens vs baseline aggregate
    w1 = by_weight.get(1.0) or {}
    w0 = by_weight.get(0.0) or {}
    domination = {
        "at_weight_1_top1_change_rate": (w1.get("ranking_diff") or {}).get("races_top1_change_rate"),
        "at_weight_1_mean_abs_move": (w1.get("ranking_diff") or {}).get("mean_abs_candidate_rank_move"),
        "midupper_share": mid_share,
        "world_saturation_flag": mid_share >= 0.80,
        "policy_domination_flag": bool(
            ((w1.get("ranking_diff") or {}).get("races_top1_change_rate") or 0) >= 0.50
        ),
    }
    # sensitivity curve
    curve = []
    for w in WEIGHTS:
        arm = by_weight[w]
        curve.append(
            {
                "weight": w,
                "hit_delta": arm["delta"]["hit"],
                "rank710_delta": arm["delta"]["rank710"],
                "other_miss_delta": arm["delta"]["other_miss"],
                "top1_change_rate": arm["ranking_diff"]["races_top1_change_rate"],
            }
        )
    return {
        "world_distribution": dict(world_dist),
        "saturation_vs_design": saturation,
        "domination": domination,
        "sensitivity_curve": curve,
        "bias_notes": [
            "Kernel is design-prior (not fit on Hit labels) to reduce label overfit in this simulation.",
            "Corpus World labels are midupper-saturated; policy effect may concentrate on midupper_world.",
        ],
    }


def governance(by_weight: dict[float, dict[str, Any]]) -> dict[str, Any]:
    """PASS if some weight>0 meets non-inferiority AND meaningful PE influence AND Hit not worse.

    User PASS conditions:
    - BaselineよりHit悪化なし
    - rank710悪化なし
    - other miss悪化なし
    - WorldがPEへ意味のある影響を持つ
    """
    checks = {}
    best = None
    for w in WEIGHTS:
        if w == 0.0:
            continue
        d = by_weight[w]["delta"]
        rd = by_weight[w]["ranking_diff"]
        hit_ok = d["hit"] >= 0
        r710_ok = d["rank710"] <= 0
        other_ok = d["other_miss"] <= 0
        meaningful = bool((rd.get("races_top1_change_rate") or 0) >= 0.05) or bool(
            (rd.get("mean_abs_candidate_rank_move") or 0) >= 0.15
        )
        # ROI expectation: prefer hit>0; non-inferior alone is not ROI proof (V34 lesson)
        roi_signal = d["hit"] > 0
        passed = hit_ok and r710_ok and other_ok and meaningful
        checks[str(w)] = {
            "hit_ge_baseline": hit_ok,
            "rank710_not_worse": r710_ok,
            "other_miss_not_worse": other_ok,
            "meaningful_pe_influence": meaningful,
            "hit_improved": roi_signal,
            "pass_non_inferiority_with_influence": passed,
            "delta": d,
            "top1_change_rate": rd.get("races_top1_change_rate"),
        }
        if passed and roi_signal:
            best = w
            break
        if passed and best is None:
            best = w  # non-inferior with influence, may still FAIL final ROI gate

    any_pass_ni = any(v["pass_non_inferiority_with_influence"] for v in checks.values())
    any_hit_up = any(v["hit_improved"] for v in checks.values())
    # Final: ROI improvement expected only if Hit improves under a NI-safe weight
    final_pass = False
    final_reason = ""
    for w, v in checks.items():
        if v["pass_non_inferiority_with_influence"] and v["hit_improved"]:
            final_pass = True
            final_reason = f"weight={w} Hit+ with NI and meaningful influence"
            break
    if not final_pass:
        if any_pass_ni and not any_hit_up:
            final_reason = "Non-inferiority+influence possible but Hit never improves → ROI not proven"
        elif any_hit_up and not any_pass_ni:
            final_reason = "Some Hit gains exist but violate rank710/other_miss or lack influence thresholds"
        else:
            final_reason = "No weight satisfies Hit non-worse + rank710/other_miss non-worse + meaningful influence with Hit lift"

    return {
        "by_weight": checks,
        "any_non_inferior_with_influence": any_pass_ni,
        "any_hit_improvement": any_hit_up,
        "final_pass": final_pass,
        "final_verdict": "PASS" if final_pass else "FAIL",
        "reason": final_reason,
        "selected_weight": best,
    }


def run(db_path: Path, out_dir: Path) -> dict[str, Any]:
    races = load_races(db_path)
    by_weight = {w: evaluate_weight(races, w) for w in WEIGHTS}
    # strip heavy race_rows from non-primary weights in summary but keep w=0.5 detail
    safety = safety_analysis(by_weight, races)
    gov = governance(by_weight)

    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now(),
        "shadow_only": True,
        "product_mutation": False,
        "pe_ce_ai_world_unchanged": True,
        "method": {
            "baseline": "Frozen Production model_rank / win_prob from prediction bundles",
            "policy": "Virtual blend: (1-w)*norm(win_prob) + w*norm(WorldRankKernel affinity)",
            "weights": list(WEIGHTS),
            "purchase_proxy": "purchase == top1 hit (V34-compatible)",
            "kernels": WORLD_RANK_KERNEL,
            "note": "Kernels are design priors, not Hit-fitted",
        },
        "corpus": {
            "n_races_with_ranking": len(races),
            "world_counts": dict(Counter(r["world"] for r in races)),
            "subworld_counts": dict(Counter(r.get("sub_world") or "unknown" for r in races)),
        },
        "by_weight": {
            str(w): {
                **{k: v for k, v in arm.items() if k != "race_rows"},
            }
            for w, arm in by_weight.items()
        },
        "race_rows_weight_0_5": by_weight[0.5]["race_rows"],
        "safety": safety,
        "governance": gov,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "v37-world-pe-policy-sim.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_json_path"] = str(json_path)
    return report


def write_docs(report: dict[str, Any], docs_dir: Path) -> dict[str, str]:
    docs_dir.mkdir(parents=True, exist_ok=True)
    corp = report["corpus"]
    gov = report["governance"]
    safety = report["safety"]
    bw = report["by_weight"]

    def arm_table() -> str:
        lines = [
            "| Weight | Hit | ΔHit | Purchase | ΔPurch | rank710 | Δ710 | other_miss | Δother | Top1 change | mean |rank| move |",
            "|-------:|----:|-----:|---------:|-------:|--------:|-----:|-----------:|-------:|------------:|------------------:|",
        ]
        for w in WEIGHTS:
            a = bw[str(w)]
            p, d, r = a["policy"], a["delta"], a["ranking_diff"]
            lines.append(
                f"| {w:.0%} | {p['hit']} ({_pct(p['hit_rate'])}) | {d['hit']:+d} | "
                f"{p['purchase']} | {d['purchase']:+d} | {p['rank710']} | {d['rank710']:+d} | "
                f"{p['other_miss']} | {d['other_miss']:+d} | "
                f"{r['races_top1_changed']} ({_pct(r['races_top1_change_rate'])}) | "
                f"{(r['mean_abs_candidate_rank_move'] or 0):.3f} |"
            )
        return "\n".join(lines)

    sim = f"""# Version37 — World→PE Policy Simulation

**Status:** Research / Simulation only — **no Production / PE / CE / AI / World mutation**  
**Generated:** `{report['generated_at']}`  
**N races (ranking-evaluable):** `{corp['n_races_with_ranking']}`  
**Verdict:** **{gov['final_verdict']}**

## Method

```text
Frozen Production ranking (win_prob / model_rank)
        ↓
Virtual PE Policy Layer
  score = (1-w)·norm(win_prob) + w·norm(WorldRankKernel[world, subworld])
        ↓
Simulated Candidate Ranking → Prediction top1 / miss buckets
```

- Weights: `{list(WEIGHTS)}`
- Kernels: design priors (not Hit-fitted) — see JSON `method.kernels`
- Purchase proxy: top1 Hit（V34 同型）

## Corpus

- World counts: `{json.dumps(corp['world_counts'], ensure_ascii=False)}`
- SubWorld counts: `{json.dumps(corp['subworld_counts'], ensure_ascii=False)}`

## Aggregate by weight

{arm_table()}

## Governance (summary)

- Final: **{gov['final_verdict']}**
- Reason: {gov['reason']}
- Any NI+influence: `{gov['any_non_inferior_with_influence']}`
- Any Hit improvement: `{gov['any_hit_improvement']}`

## Index

| Doc | Content |
|-----|---------|
| `v37-world-pe-simulation.md` | 本ファイル |
| `v37-policy-impact.md` | World 別影響 |
| `v37-ranking-diff.md` | 順位変化 |
| `v37-world-weight-analysis.md` | Sensitivity |
| `v37-governance.md` | PASS/FAIL |

## Guardrails

- Prediction / PE / CE / AI / World / Signal Service / Production — unchanged
"""

    # policy impact
    impact_lines = [
        "# Version37 — Policy Impact by World",
        "",
        f"**N:** `{corp['n_races_with_ranking']}`  ",
        f"**Verdict context:** `{gov['final_verdict']}`",
        "",
        "## World influence at selected weights",
        "",
    ]
    for w in (0.25, 0.5, 0.75, 1.0):
        wi = bw[str(w)]["world_influence"]
        impact_lines.append(f"### Weight {w:.0%}")
        impact_lines.append("")
        impact_lines.append("| World | n | Top1 changed | Top1 change rate | mean |Δrank| |")
        impact_lines.append("|-------|--:|-------------:|-----------------:|---------------:|")
        for world, rec in wi.items():
            impact_lines.append(
                f"| {world} | {rec['n']} | {rec['top1_changed']} | {_pct(rec['top1_change_rate'])} | "
                f"{(rec['mean_abs_rank_move'] or 0):.3f} |"
            )
        impact_lines.append("")
    impact_lines.append("## SubWorld mean |Δrank| (weight=50%)")
    impact_lines.append("")
    impact_lines.append("| SubWorld | n | mean |Δrank| |")
    impact_lines.append("|----------|--:|---------------:|")
    for s, rec in (bw["0.5"].get("subworld_influence") or {}).items():
        impact_lines.append(f"| {s} | {rec['n']} | {rec['mean_abs_rank_move']:.3f} |")
    impact_lines.append("")
    impact_lines.append("## Interpretation")
    impact_lines.append("")
    impact_lines.append(
        "Influence is measured as ranking displacement under the virtual World kernel, "
        "not as a claim that Production PE currently consumes World (V35 proved it does not)."
    )

    # ranking diff
    r50 = bw["0.5"]["ranking_diff"]
    d50 = bw["0.5"]["delta"]
    ranking = f"""# Version37 — Ranking Diff

**Weight focus:** 50%（中間感度）  
**N:** `{corp['n_races_with_ranking']}`

## Prediction / Candidate 順位変化

| Metric | Value |
|--------|------:|
| Races with any candidate rank change | {bw['0.5']['ranking_diff']['prediction_rank_changed_races']} |
| Top1 changed | {r50['races_top1_changed']} ({_pct(r50['races_top1_change_rate'])}) |
| Top3 set changed | {r50['races_top3_changed']} ({_pct(r50['races_top3_change_rate'])}) |
| Mean horses with rank change / race | {(r50['mean_horses_rank_changed_per_race'] or 0):.2f} |
| Mean abs candidate rank move | {(r50['mean_abs_candidate_rank_move'] or 0):.3f} |

## Hit / miss layer Δ @ 50%

| Layer | Δ |
|-------|--:|
| Hit | {d50['hit']:+d} |
| Purchase | {d50['purchase']:+d} |
| rank46 | {d50['rank46']:+d} |
| rank710 | {d50['rank710']:+d} |
| other_1_3 | {d50['other_1_3']:+d} |
| other_10_13 | {d50['other_10_13']:+d} |
| other_miss | {d50['other_miss']:+d} |

## Full weight sweep

{arm_table()}

## Note

Baseline ranks are frozen Production `model_rank`. Policy ranks are simulation-only.
"""

    # weight analysis
    weight_doc = [
        "# Version37 — World Policy Weight Sensitivity",
        "",
        "## Curve",
        "",
        "| Weight | Hit Δ | rank710 Δ | other_miss Δ | Top1 change rate |",
        "|-------:|------:|----------:|-------------:|-----------------:|",
    ]
    for pt in safety["sensitivity_curve"]:
        weight_doc.append(
            f"| {pt['weight']:.0%} | {pt['hit_delta']:+d} | {pt['rank710_delta']:+d} | "
            f"{pt['other_miss_delta']:+d} | {_pct(pt['top1_change_rate'])} |"
        )
    weight_doc.extend(
        [
            "",
            "## Safety flags",
            "",
            f"- midupper_share: `{safety['domination']['midupper_share']}`",
            f"- world_saturation_flag: `{safety['domination']['world_saturation_flag']}`",
            f"- policy_domination_flag (Top1 change ≥50% at w=100%): `{safety['domination']['policy_domination_flag']}`",
            f"- Top1 change rate @100%: `{_pct(safety['domination']['at_weight_1_top1_change_rate'])}`",
            f"- mean |Δrank| @100%: `{(safety['domination']['at_weight_1_mean_abs_move'] or 0):.3f}`",
            "",
            "## Saturation vs design mix",
            "",
            "| World | observed | design | Δ |",
            "|-------|---------:|-------:|--:|",
        ]
    )
    for w, rec in safety["saturation_vs_design"].items():
        weight_doc.append(
            f"| {w} | {_pct(rec['observed_share'])} | {_pct(rec['design_share'])} | "
            f"{(rec['delta_vs_design'] or 0):+.1%} |"
        )
    weight_doc.extend(
        [
            "",
            "## Bias / Overfit notes",
            "",
        ]
        + [f"- {n}" for n in safety["bias_notes"]]
        + [
            "",
            "Overfit control: kernels are **not** optimized against Hit on this corpus.",
            "",
        ]
    )

    # governance
    gov_doc = f"""# Version37 — Governance

**Generated:** `{report['generated_at']}`  
**N:** `{corp['n_races_with_ranking']}`

## PASS conditions (user)

| Check | Requirement |
|-------|-------------|
| Hit | not worse than Baseline |
| rank710 | not worse |
| other miss | not worse |
| Influence | World has meaningful effect on PE ranking |

## Per-weight checks

| Weight | Hit≥base | rank710≤base | other_miss≤base | meaningful | Hit↑ | NI+influence |
|-------:|:--------:|:------------:|:---------------:|:----------:|:----:|:------------:|
"""
    for w in WEIGHTS:
        if w == 0.0:
            continue
        c = gov["by_weight"][str(w)]
        gov_doc += (
            f"| {w:.0%} | `{c['hit_ge_baseline']}` | `{c['rank710_not_worse']}` | "
            f"`{c['other_miss_not_worse']}` | `{c['meaningful_pe_influence']}` | "
            f"`{c['hit_improved']}` | `{c['pass_non_inferiority_with_influence']}` |\n"
        )

    gov_doc += f"""
## Final verdict

# **{gov['final_verdict']}**

**Reason:** {gov['reason']}

### Interpretation rule (aligned with V34 lesson)

Non-inferiority alone ≠ ROI proof.  
This phase requires **Hit improvement** under a weight that also satisfies NI + meaningful PE influence.

| Gate | Value |
|------|-------|
| final_pass | `{gov['final_pass']}` |
| any_non_inferior_with_influence | `{gov['any_non_inferior_with_influence']}` |
| any_hit_improvement | `{gov['any_hit_improvement']}` |
| selected_weight | `{gov['selected_weight']}` |

## Guardrails

- No Prediction / PE / CE / AI / World / Signal Service / Production changes
- Simulation only (virtual policy layer)
"""

    outputs = {
        "sim": docs_dir / "v37-world-pe-simulation.md",
        "impact": docs_dir / "v37-policy-impact.md",
        "ranking": docs_dir / "v37-ranking-diff.md",
        "weight": docs_dir / "v37-world-weight-analysis.md",
        "gov": docs_dir / "v37-governance.md",
    }
    outputs["sim"].write_text(sim, encoding="utf-8")
    outputs["impact"].write_text("\n".join(impact_lines) + "\n", encoding="utf-8")
    outputs["ranking"].write_text(ranking, encoding="utf-8")
    outputs["weight"].write_text("\n".join(weight_doc), encoding="utf-8")
    outputs["gov"].write_text(gov_doc, encoding="utf-8")
    return {k: str(v) for k, v in outputs.items()}


if __name__ == "__main__":
    import os
    import sys

    db = Path(os.environ.get("EXPECT_AI_DB_PATH") or "var/expect_ai.db")
    if len(sys.argv) > 1:
        db = Path(sys.argv[1])
    out = Path(os.environ.get("V37_OUT_DIR") or "evidence/research/reports")
    docs = Path(os.environ.get("V37_DOCS_DIR") or "docs/research")
    report = run(db, out)
    paths = write_docs(report, docs)
    print(
        json.dumps(
            {
                "ok": True,
                "n": report["corpus"]["n_races_with_ranking"],
                "verdict": report["governance"]["final_verdict"],
                "reason": report["governance"]["reason"],
                "json": report.get("_json_path"),
                "docs": paths,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
