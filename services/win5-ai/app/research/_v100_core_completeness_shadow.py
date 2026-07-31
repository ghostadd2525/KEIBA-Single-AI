# -*- coding: utf-8 -*-
"""Version100 — Core Completeness Shadow (observation only).

ADR-009: Core describes races completely — does not maximize profit.
Measures Prediction / World / Near Miss / Semantic Completeness.
Does NOT change Prediction / Trigger / CEW / Decision / Single / Win5.
実装禁止 — Shadow Observation only.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))
sys.path.insert(0, str(Path(r"C:\win5-ai")))

from app.decision.fingerprint import prediction_fingerprint  # noqa: E402
from app.research._v74_world_strategy_validation import load_cew_labels  # noqa: E402
from app.research._v96_unsatisfied_world_affinity import (  # noqa: E402
    AFFINITY_WORLDS,
    affinity_for_world,
    build_signals_for_race,
    exclusion_reasons_research,
    primary_near_world,
    structural_class,
)
from app.research._v97_affinity_decision_value_shadow import (  # noqa: E402
    load_dual,
    near_miss_meta,
)

SCHEMA = "v100-core-completeness-shadow/1.0"
STRATEGY_WORLDS = (
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
    "mixed_world",
    "bug_world",
)

# V75 Expected Strategy resolvable labels (design map — observation only)
EXPECTED_STRATEGY = {
    "rank7_world": "melee_read:history≈win_prob; no ability-monopoly",
    "midhole_world": "history_first; win_prob not primary",
    "unsatisfied": "residual_baseline; no positive winning claim",
    "core_world": "ability_settlement_provisional; n-insufficient",
    "midupper_world": "upper+aptitude_provisional",
    "mixed_world": "multi_path_compose; no single axis",
    "bug_world": "exception_only; blocked without flag",
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _rate(ok: int, n: int) -> float | None:
    return (ok / n) if n else None


def _f(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        x = float(v)
        if x != x:
            return None
        return x
    except (TypeError, ValueError):
        return None


def load_sources() -> dict[str, Any]:
    corp = json.loads(
        (ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(encoding="utf-8")
    )
    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fx_rows = fx.get("rows") or fx.get("evaluations") or []
    fxby = {str(r["race_id"]): r for r in fx_rows}
    cew = load_cew_labels()
    dual = load_dual()
    races_by = {str(r["race_id"]): r for r in corp["races"]}
    return {
        "corp": corp,
        "fxby": fxby,
        "cew": cew,
        "dual": dual,
        "races_by": races_by,
    }


def observe_race(
    rid: str,
    *,
    race: dict[str, Any],
    fx: dict[str, Any],
    cew_world: str | None,
    dual: dict[str, Any],
    thr: dict[str, float],
) -> dict[str, Any]:
    runners = list(race.get("runners") or [])
    n_run = len(runners)
    field_size = int(fx.get("field_size") or (race.get("context") or {}).get("field_size") or n_run)

    # --- Prediction ---
    missing_pred: list[str] = []
    rank_ok = 0
    score_ok = 0
    conf_ok = 0
    conf_present_any = False
    ranks = []
    scores = []
    for i, u in enumerate(runners):
        mr = u.get("model_rank")
        wp = _f(u.get("win_prob"))
        # confidence: explicit field only (not inventing from win_prob)
        conf = u.get("confidence")
        if conf is None:
            conf = u.get("conf")
        if conf is None and fx:
            # per-horse confidence rarely in fx; race-level ignored for candidate coverage
            pass
        if mr is not None and str(mr) != "" and int(mr) > 0 and int(mr) < 900:
            rank_ok += 1
            ranks.append(int(mr))
        else:
            missing_pred.append(f"rank:horse[{i}]")
        if wp is not None:
            score_ok += 1
            scores.append(wp)
        else:
            missing_pred.append(f"score:horse[{i}]")
        if conf is not None and _f(conf) is not None:
            conf_ok += 1
            conf_present_any = True
        # per-horse confidence gaps counted in aggregate, not each listed
    if n_run and conf_ok < n_run:
        missing_pred.append("confidence:candidate_missing")

    pred_top1 = str(fx.get("predicted_top1_horse_id") or "")
    ids = [str(u.get("horse_id") or "") for u in runners]
    top1_ok = bool(pred_top1) and pred_top1 in ids
    if not top1_ok:
        missing_pred.append("predicted_top1")

    # unique ranks
    unique_ranks = len(set(ranks)) == len(ranks) and len(ranks) == n_run and n_run > 0
    if n_run and not unique_ranks:
        missing_pred.append("rank_not_unique_or_incomplete")

    field_align = field_size == n_run
    if not field_align:
        missing_pred.append(f"field_mismatch:field={field_size},runners={n_run}")

    # fingerprint stability: compute twice from same projection
    horses_proj = []
    for u in runners:
        horses_proj.append(
            {
                "horse_id": str(u.get("horse_id") or ""),
                "model_rank": int(u.get("model_rank") or 999),
                "win_prob": float(_f(u.get("win_prob")) or 0.0),
            }
        )
    try:
        fp1 = prediction_fingerprint(rid, pred_top1, horses_proj)
        fp2 = prediction_fingerprint(rid, pred_top1, horses_proj)
        fp_stable = fp1 == fp2 and bool(fp1)
    except Exception as e:
        fp_stable = False
        missing_pred.append(f"fingerprint_error:{type(e).__name__}")

    # Rank/Score completeness (Confidence tracked separately per ADR-009 / V100)
    prediction_complete = bool(
        n_run > 0
        and rank_ok == n_run
        and score_ok == n_run
        and top1_ok
        and unique_ranks
        and field_align
        and fp_stable
    )
    pc = {
        "n_candidates": n_run,
        "rank_coverage": _rate(rank_ok, n_run),
        "score_coverage": _rate(score_ok, n_run),
        "confidence_coverage": _rate(conf_ok, n_run),
        "confidence_field_observed": conf_present_any,
        "top1_defined": top1_ok,
        "ranks_unique_complete": unique_ranks,
        "field_alignment": field_align,
        "fingerprint_stable": fp_stable,
        "prediction_complete": prediction_complete,
        "prediction_complete_with_confidence": bool(
            prediction_complete and conf_ok == n_run and n_run > 0
        ),
        "missing": missing_pred,
    }

    # --- World / Trace ---
    missing_world: list[str] = []
    label_ok = cew_world is not None and str(cew_world) != ""
    if not label_ok:
        missing_world.append("cew_world")

    trace = (dual or {}).get("decision_trace") or {}
    trace_ok = isinstance(trace, dict) and len(trace) > 0
    if not trace_ok:
        missing_world.append("decision_trace")

    must_trace_ok = True
    excl_trace_ok = True
    match_trace_ok = True
    match_consistent = True
    worlds_in_trace = 0
    for w in STRATEGY_WORLDS:
        tw = trace.get(w) if trace_ok else None
        if not isinstance(tw, dict):
            must_trace_ok = False
            excl_trace_ok = False
            match_trace_ok = False
            missing_world.append(f"trace_missing:{w}")
            continue
        worlds_in_trace += 1
        if "must" not in tw:
            must_trace_ok = False
            missing_world.append(f"must_missing:{w}")
        if "must_gaps" not in tw:
            must_trace_ok = False
            missing_world.append(f"must_gaps_missing:{w}")
        if "exclude" not in tw:
            excl_trace_ok = False
            missing_world.append(f"exclude_missing:{w}")
        if "match" not in tw:
            match_trace_ok = False
            missing_world.append(f"match_missing:{w}")
        else:
            must = bool(tw.get("must"))
            excl = bool(tw.get("exclude"))
            match = bool(tw.get("match"))
            expected = must and not excl
            if match != expected:
                match_consistent = False
                missing_world.append(f"match_inconsistent:{w}")

    transition = (dual or {}).get("world_transition")
    trigger_path = (dual or {}).get("trigger_path")
    transition_ok = bool(transition) or bool(trigger_path)
    if not transition_ok:
        missing_world.append("transition_or_trigger_path")

    # Decision Tree Trace ≈ trigger_path + decision_trace presence
    decision_tree_ok = bool(trigger_path) and trace_ok
    if not decision_tree_ok:
        if not trigger_path:
            missing_world.append("decision_tree:trigger_path")
        if not trace_ok:
            missing_world.append("decision_tree:decision_trace")

    expected_strategy = EXPECTED_STRATEGY.get(str(cew_world)) if label_ok else None
    expected_strategy_ok = expected_strategy is not None
    if label_ok and not expected_strategy_ok:
        missing_world.append(f"expected_strategy_unmapped:{cew_world}")

    positive = bool(label_ok and cew_world != "unsatisfied")

    wc = {
        "label_present": label_ok,
        "cew_world": cew_world,
        "trace_present": trace_ok,
        "must_trace_complete": must_trace_ok and worlds_in_trace == len(STRATEGY_WORLDS),
        "exclusion_trace_complete": excl_trace_ok and worlds_in_trace == len(STRATEGY_WORLDS),
        "match_trace_complete": match_trace_ok and worlds_in_trace == len(STRATEGY_WORLDS),
        "match_consistent": match_consistent if trace_ok else False,
        "transition_present": transition_ok,
        "world_transition": transition,
        "trigger_path": trigger_path,
        "decision_tree_trace_present": decision_tree_ok,
        "expected_strategy_present": expected_strategy_ok,
        "expected_strategy": expected_strategy,
        "positive_world": positive,
        "world_complete": bool(
            label_ok
            and trace_ok
            and must_trace_ok
            and excl_trace_ok
            and match_trace_ok
            and match_consistent
            and transition_ok
            and decision_tree_ok
        ),
        "missing": missing_world,
    }

    # --- Near Miss Completeness (only meaningful for unsatisfied; else N/A) ---
    missing_nm: list[str] = []
    nm_applicable = label_ok and cew_world == "unsatisfied"
    nmc: dict[str, Any]
    if not nm_applicable:
        nmc = {
            "applicable": False,
            "near_miss_complete": None,
            "missing": [],
        }
    else:
        meta = near_miss_meta(trace)
        residual_class = structural_class(trace)
        class_ok = residual_class in ("NEAR_MISS", "PURE_RESIDUAL")
        if not class_ok:
            missing_nm.append("residual_class")

        near_world = None
        affinity = {}
        must_gaps_by = {}
        excl_reasons_by = {}
        signals = build_signals_for_race(rid, race, fx)
        excl_map = exclusion_reasons_research(signals, thr)

        for w in AFFINITY_WORLDS:
            tw = (trace or {}).get(w) or {}
            a = affinity_for_world(tw, w)
            affinity[w] = a["must_affinity"]
            must_gaps_by[w] = list(a.get("must_gaps") or [])
            excl_reasons_by[w] = list(excl_map.get(w) or [])
            if a.get("exclude") and not excl_reasons_by[w]:
                excl_reasons_by[w] = ["excl:unresolved_or_missing_signal"]
                missing_nm.append(f"exclusion_reason_weak:{w}")

        if meta:
            near_world = meta.get("near_world")
        else:
            near_world = primary_near_world(
                {w: affinity_for_world((trace or {}).get(w) or {}, w) for w in AFFINITY_WORLDS}
            )

        near_world_ok = True
        if residual_class == "NEAR_MISS":
            near_world_ok = near_world is not None
            if not near_world_ok:
                missing_nm.append("near_world")
        # PURE_RESIDUAL: near_world should be null
        if residual_class == "PURE_RESIDUAL" and near_world is not None:
            # still ok as observational; don't fail completeness hard
            pass

        affinity_ok = len(affinity) == len(AFFINITY_WORLDS) and all(
            affinity[w] is not None for w in AFFINITY_WORLDS
        )
        if not affinity_ok:
            missing_nm.append("affinity_vector")

        gaps_ok = all(isinstance(must_gaps_by[w], list) for w in AFFINITY_WORLDS)
        if not gaps_ok:
            missing_nm.append("must_gaps")

        # For NEAR_MISS: at least one exclusion reason on near_world or any near
        excl_ok = True
        if residual_class == "NEAR_MISS":
            if near_world:
                excl_ok = len(excl_reasons_by.get(near_world) or []) > 0
            else:
                excl_ok = False
            if not excl_ok:
                missing_nm.append("exclusion_reasons")

        transition_nm_ok = transition_ok
        if not transition_nm_ok:
            missing_nm.append("transition")

        nmc = {
            "applicable": True,
            "residual_class": residual_class,
            "class_present": class_ok,
            "near_world": near_world,
            "near_world_present": near_world_ok if residual_class == "NEAR_MISS" else True,
            "affinity": affinity,
            "affinity_present": affinity_ok,
            "must_gaps_by_world": must_gaps_by,
            "must_gaps_present": gaps_ok,
            "exclusion_reasons_by_world": {
                w: excl_reasons_by[w] for w in AFFINITY_WORLDS if excl_reasons_by[w]
            },
            "exclusion_reasons_present": excl_ok if residual_class == "NEAR_MISS" else True,
            "transition_present": transition_nm_ok,
            "near_miss_complete": bool(
                class_ok
                and (near_world_ok if residual_class == "NEAR_MISS" else True)
                and affinity_ok
                and gaps_ok
                and (excl_ok if residual_class == "NEAR_MISS" else True)
                and transition_nm_ok
            ),
            "missing": missing_nm,
        }

    # --- Semantic Completeness ---
    missing_sem: list[str] = []
    # Why this world?
    why_parts = {
        "world_label": label_ok,
        "must_satisfied_known": False,
        "must_gaps_known": False,
        "exclusion_reasons_known": False,
        "near_miss_reasons_known": False,
        "expected_strategy_known": expected_strategy_ok,
        "transition_known": transition_ok,
        "trigger_path_known": bool(trigger_path),
    }

    if trace_ok and label_ok:
        if cew_world == "unsatisfied":
            why_parts["must_satisfied_known"] = True  # known that no positive match
            why_parts["must_gaps_known"] = must_trace_ok
            if nmc.get("applicable") and nmc.get("residual_class") == "NEAR_MISS":
                why_parts["exclusion_reasons_known"] = bool(nmc.get("exclusion_reasons_present"))
                why_parts["near_miss_reasons_known"] = bool(
                    nmc.get("near_world_present") and nmc.get("exclusion_reasons_present")
                )
            elif nmc.get("applicable") and nmc.get("residual_class") == "PURE_RESIDUAL":
                why_parts["exclusion_reasons_known"] = True  # N/A — explained as all must fail
                why_parts["near_miss_reasons_known"] = True  # explained as pure residual
            else:
                missing_sem.append("near_miss_taxonomy")
        else:
            tw = trace.get(cew_world) or {}
            why_parts["must_satisfied_known"] = bool(tw.get("must")) and "must" in tw
            why_parts["must_gaps_known"] = "must_gaps" in tw
            why_parts["exclusion_reasons_known"] = "exclude" in tw and not bool(tw.get("exclude"))
            # For positive match, exclusion should be false; reasons optional
            if bool(tw.get("match")):
                why_parts["exclusion_reasons_known"] = True
            why_parts["near_miss_reasons_known"] = True  # N/A

    for k, v in why_parts.items():
        if not v:
            missing_sem.append(f"semantic:{k}")

    semantic_score = sum(1 for v in why_parts.values() if v) / len(why_parts)
    semantic_complete = semantic_score >= 1.0

    sc = {
        "why_parts": why_parts,
        "semantic_score": semantic_score,
        "semantic_complete": semantic_complete,
        "explainable": semantic_score >= 0.8,
        "missing": missing_sem,
    }

    all_missing = list(dict.fromkeys(pc["missing"] + wc["missing"] + nmc.get("missing", []) + sc["missing"]))

    return {
        "race_id": rid,
        "prediction": pc,
        "world": wc,
        "near_miss": nmc,
        "semantic": sc,
        "missing_all": all_missing,
    }


def aggregate_reports(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    # Prediction
    pc_keys = [
        "rank_coverage",
        "score_coverage",
        "confidence_coverage",
        "top1_defined",
        "ranks_unique_complete",
        "field_alignment",
        "fingerprint_stable",
        "prediction_complete",
        "prediction_complete_with_confidence",
    ]
    pred = {}
    for k in pc_keys:
        vals = []
        for r in rows:
            v = r["prediction"].get(k)
            if isinstance(v, bool):
                vals.append(1.0 if v else 0.0)
            elif isinstance(v, (int, float)) and v is not None:
                vals.append(float(v))
        pred[k] = float(sum(vals) / len(vals)) if vals else None

    # World
    wc_bool = [
        "label_present",
        "trace_present",
        "must_trace_complete",
        "exclusion_trace_complete",
        "match_trace_complete",
        "match_consistent",
        "transition_present",
        "decision_tree_trace_present",
        "expected_strategy_present",
        "world_complete",
    ]
    world = {}
    for k in wc_bool:
        vals = [1.0 if r["world"].get(k) else 0.0 for r in rows]
        world[k] = float(sum(vals) / len(vals)) if vals else None
    world["positive_world_rate"] = float(sum(1 for r in rows if r["world"].get("positive_world")) / n)

    # Near miss (applicable only)
    nm_rows = [r for r in rows if r["near_miss"].get("applicable")]
    nn = len(nm_rows)
    near = {"n_unsatisfied": nn, "n_na": n - nn}
    if nn:
        for k in (
            "class_present",
            "near_world_present",
            "affinity_present",
            "must_gaps_present",
            "exclusion_reasons_present",
            "transition_present",
            "near_miss_complete",
        ):
            vals = [1.0 if r["near_miss"].get(k) else 0.0 for r in nm_rows]
            near[k] = float(sum(vals) / len(vals))
        near["residual_class_dist"] = dict(Counter(r["near_miss"].get("residual_class") for r in nm_rows))
    else:
        for k in (
            "class_present",
            "near_world_present",
            "affinity_present",
            "must_gaps_present",
            "exclusion_reasons_present",
            "transition_present",
            "near_miss_complete",
        ):
            near[k] = None

    # Semantic
    sem = {
        "mean_semantic_score": float(sum(r["semantic"]["semantic_score"] for r in rows) / n),
        "semantic_complete_rate": float(sum(1 for r in rows if r["semantic"]["semantic_complete"]) / n),
        "explainable_rate": float(sum(1 for r in rows if r["semantic"]["explainable"]) / n),
    }
    part_rates = {}
    keys = list(rows[0]["semantic"]["why_parts"].keys()) if rows else []
    for k in keys:
        part_rates[k] = float(sum(1 for r in rows if r["semantic"]["why_parts"].get(k)) / n)
    sem["part_rates"] = part_rates

    return {
        "n_races": n,
        "prediction": pred,
        "world": world,
        "near_miss": near,
        "semantic": sem,
    }


def missing_inventory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counter: Counter = Counter()
    by_race_examples: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        for m in r.get("missing_all") or []:
            # bucket confidence per-horse into one key
            if m.startswith("confidence:horse"):
                key = "confidence:candidate_missing"
            elif m.startswith("rank:horse"):
                key = "rank:candidate_missing"
            elif m.startswith("score:horse"):
                key = "score:candidate_missing"
            elif m.startswith("fingerprint_error"):
                key = m  # keep exception type
            else:
                key = m
            # count races once per key
            if key not in {x.split("::")[0] for x in []}:
                pass
            counter[key] += 1
            # dedupe race examples: only first occurrence per race handled by list length
            if r["race_id"] not in by_race_examples[key] and len(by_race_examples[key]) < 5:
                by_race_examples[key].append(r["race_id"])
    return {
        "missing_counts": dict(counter.most_common()),
        "examples": {k: by_race_examples[k] for k, _ in counter.most_common(30)},
        "n_races_with_any_missing": sum(1 for r in rows if r.get("missing_all")),
        "n_races_clean": sum(1 for r in rows if not r.get("missing_all")),
    }


def run() -> dict[str, Any]:
    os.environ.setdefault("W_TRIGGER_PATH", "legacy")
    from ai_platform.core.world.v44_shadow_eval import build_polarity_thresholds

    src = load_sources()
    signal_table = []
    for rid, race in src["races_by"].items():
        signal_table.append(build_signals_for_race(rid, race, src["fxby"].get(rid) or {}))
    thr = build_polarity_thresholds(signal_table)

    rows = []
    # Prefer CEW keys; also include corpus races
    rids = sorted(set(src["cew"].keys()) | set(src["races_by"].keys()))
    for rid in rids:
        race = src["races_by"].get(rid)
        if not race:
            continue
        fx = src["fxby"].get(rid) or {}
        dual = src["dual"].get(rid) or {}
        cew_world = src["cew"].get(rid)
        # dual v44_world as fallback label observation only
        if cew_world is None:
            cew_world = dual.get("v44_world")
        rows.append(
            observe_race(
                rid,
                race=race,
                fx=fx,
                cew_world=cew_world,
                dual=dual,
                thr=thr,
            )
        )

    agg = aggregate_reports(rows)
    inv = missing_inventory(rows)

    # Status rollup (observation grades — not product gates)
    def grade(rate: float | None, hi: float = 0.99, mid: float = 0.90) -> str:
        if rate is None:
            return "N/A"
        if rate >= hi:
            return "HIGH"
        if rate >= mid:
            return "MED"
        return "LOW"

    status = {
        "prediction_completeness": grade(agg["prediction"].get("prediction_complete")),
        "prediction_with_confidence": grade(agg["prediction"].get("prediction_complete_with_confidence")),
        "world_completeness": grade(agg["world"].get("world_complete")),
        "near_miss_completeness": grade(agg["near_miss"].get("near_miss_complete")),
        "semantic_completeness": grade(agg["semantic"].get("semantic_complete_rate")),
        "semantic_explainable": grade(agg["semantic"].get("explainable_rate"), hi=0.95, mid=0.80),
    }

    # Trace completeness summary
    trace = {
        "must_trace_complete_rate": agg["world"].get("must_trace_complete"),
        "exclusion_trace_complete_rate": agg["world"].get("exclusion_trace_complete"),
        "match_trace_complete_rate": agg["world"].get("match_trace_complete"),
        "match_consistent_rate": agg["world"].get("match_consistent"),
        "decision_tree_trace_rate": agg["world"].get("decision_tree_trace_present"),
        "transition_rate": agg["world"].get("transition_present"),
    }

    report = {
        "schema": SCHEMA,
        "generated_at": _now(),
        "adr": "ADR-009",
        "purpose": "Measure Core Completeness — not profit / Hit / ROI",
        "locks": [
            "Prediction Logic",
            "Ranking",
            "Score",
            "Confidence",
            "Trigger",
            "World Definition",
            "CEW",
            "Decision Layer",
            "Single AI",
            "Win5 AI",
        ],
        "n_races": len(rows),
        "aggregates": agg,
        "status": status,
        "trace_completeness": trace,
        "missing_inventory": inv,
        "semantic_coverage": agg["semantic"],
        "notes": [
            "Confidence per-candidate is often absent in corpus runners — reported as Completeness gap, not fixed here.",
            "Expected Strategy is resolved via V75 design map (observation), not PE mutation.",
            "ROI / Hit / Skip are excluded from this report.",
        ],
        # keep slim per-race: only incomplete ones in detail file section
        "incomplete_races_sample": [
            {
                "race_id": r["race_id"],
                "missing": r["missing_all"][:12],
                "semantic_score": r["semantic"]["semantic_score"],
                "world": r["world"].get("cew_world"),
            }
            for r in rows
            if r["missing_all"]
        ][:40],
    }
    # Attach full rows path separately to avoid huge print — still write json with summary+inventory
    report["_row_count"] = len(rows)
    # store rows externally in write_docs
    report["_rows"] = rows
    return report


def write_docs(report: dict[str, Any]) -> dict[str, str]:
    docs = ROOT / "docs/research"
    docs.mkdir(parents=True, exist_ok=True)
    rows = report.pop("_rows", [])

    # Full JSON without huge rows; companion rows file optional slim
    jpath = docs / "_v100-core-completeness-shadow.json"
    jpath.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # per-race missing only
    miss_rows = [
        {
            "race_id": r["race_id"],
            "cew_world": r["world"].get("cew_world"),
            "prediction_complete": r["prediction"].get("prediction_complete"),
            "world_complete": r["world"].get("world_complete"),
            "near_miss_complete": r["near_miss"].get("near_miss_complete"),
            "semantic_score": r["semantic"].get("semantic_score"),
            "missing": r["missing_all"],
        }
        for r in rows
    ]
    jrows = docs / "_v100-completeness-per-race.json"
    jrows.write_text(json.dumps({"n": len(miss_rows), "rows": miss_rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    def fmt(x: Any) -> str:
        if x is None:
            return "—"
        if isinstance(x, float):
            return f"{x:.4f}"
        return str(x)

    agg = report["aggregates"]
    st = report["status"]

    main = [
        "# Version100 — Core Completeness Report",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        f"**ADR:** {report['adr']}  ",
        f"**n_races:** {report['n_races']}  ",
        "**Mode:** Shadow Observation · **実装禁止**  ",
        "**非評価:** ROI / Hit / 券種 / Skip / 資金配分",
        "",
        "## Status",
        "",
        "| Axis | Grade |",
        "|---|---|",
    ]
    for k, v in st.items():
        main.append(f"| `{k}` | **{v}** |")

    main += [
        "",
        "## ① Prediction Completeness",
        "",
        "| Metric | Rate |",
        "|---|---:|",
        f"| rank_coverage (mean) | {fmt(agg['prediction'].get('rank_coverage'))} |",
        f"| score_coverage (mean) | {fmt(agg['prediction'].get('score_coverage'))} |",
        f"| confidence_coverage (mean) | {fmt(agg['prediction'].get('confidence_coverage'))} |",
        f"| top1_defined | {fmt(agg['prediction'].get('top1_defined'))} |",
        f"| ranks_unique_complete | {fmt(agg['prediction'].get('ranks_unique_complete'))} |",
        f"| field_alignment | {fmt(agg['prediction'].get('field_alignment'))} |",
        f"| fingerprint_stable | {fmt(agg['prediction'].get('fingerprint_stable'))} |",
        f"| prediction_complete (rank/score) | {fmt(agg['prediction'].get('prediction_complete'))} |",
        f"| prediction_complete_with_confidence | {fmt(agg['prediction'].get('prediction_complete_with_confidence'))} |",
        "",
        "## ② World Completeness",
        "",
        "| Metric | Rate |",
        "|---|---:|",
        f"| label_present | {fmt(agg['world'].get('label_present'))} |",
        f"| trace_present | {fmt(agg['world'].get('trace_present'))} |",
        f"| must_trace_complete | {fmt(agg['world'].get('must_trace_complete'))} |",
        f"| exclusion_trace_complete | {fmt(agg['world'].get('exclusion_trace_complete'))} |",
        f"| match_trace_complete | {fmt(agg['world'].get('match_trace_complete'))} |",
        f"| match_consistent | {fmt(agg['world'].get('match_consistent'))} |",
        f"| transition_present | {fmt(agg['world'].get('transition_present'))} |",
        f"| decision_tree_trace_present | {fmt(agg['world'].get('decision_tree_trace_present'))} |",
        f"| expected_strategy_present | {fmt(agg['world'].get('expected_strategy_present'))} |",
        f"| world_complete | {fmt(agg['world'].get('world_complete'))} |",
        f"| positive_world_rate (obs) | {fmt(agg['world'].get('positive_world_rate'))} |",
        "",
        "## ③ Near Miss Completeness（unsatisfied のみ）",
        "",
        f"n_unsatisfied={agg['near_miss'].get('n_unsatisfied')}",
        "",
        "| Metric | Rate |",
        "|---|---:|",
        f"| class_present | {fmt(agg['near_miss'].get('class_present'))} |",
        f"| near_world_present | {fmt(agg['near_miss'].get('near_world_present'))} |",
        f"| affinity_present | {fmt(agg['near_miss'].get('affinity_present'))} |",
        f"| must_gaps_present | {fmt(agg['near_miss'].get('must_gaps_present'))} |",
        f"| exclusion_reasons_present | {fmt(agg['near_miss'].get('exclusion_reasons_present'))} |",
        f"| transition_present | {fmt(agg['near_miss'].get('transition_present'))} |",
        f"| near_miss_complete | {fmt(agg['near_miss'].get('near_miss_complete'))} |",
        f"| residual_class_dist | `{agg['near_miss'].get('residual_class_dist')}` |",
        "",
        "## ④ Semantic Completeness",
        "",
        f"- mean semantic score: **{fmt(agg['semantic'].get('mean_semantic_score'))}**",
        f"- semantic_complete_rate: **{fmt(agg['semantic'].get('semantic_complete_rate'))}**",
        f"- explainable_rate (≥0.8): **{fmt(agg['semantic'].get('explainable_rate'))}**",
        "",
        "### Part coverage",
        "",
        "| Part | Rate |",
        "|---|---:|",
    ]
    for k, v in (agg["semantic"].get("part_rates") or {}).items():
        main.append(f"| `{k}` | {fmt(v)} |")

    main += [
        "",
        "## Notes",
        "",
    ]
    for n in report["notes"]:
        main.append(f"- {n}")
    main += [
        "",
        "## 関連",
        "",
        "- `v100-missing-metadata-inventory.md`",
        "- `v100-trace-completeness.md`",
        "- `v100-semantic-coverage.md`",
        "- `v100-governance.md`",
        "- ADR-009",
        "",
    ]
    rpath = docs / "v100-core-completeness-report.md"
    rpath.write_text("\n".join(main), encoding="utf-8")

    inv = report["missing_inventory"]
    inv_md = [
        "# Version100 — Missing Metadata Inventory",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        f"- races with any missing: **{inv['n_races_with_any_missing']}** / {report['n_races']}",
        f"- races clean (no missing flags): **{inv['n_races_clean']}**",
        "",
        "## Missing counts（バケット）",
        "",
        "| Missing key | n_races_touched |",
        "|---|---:|",
    ]
    for k, c in inv["missing_counts"].items():
        inv_md.append(f"| `{k}` | {c} |")
    inv_md += [
        "",
        "## Examples（最大5 race_id / key）",
        "",
        "```json",
        json.dumps(inv.get("examples") or {}, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 解釈",
        "",
        "本 Inventory は **改善実装をしない**。欠落の所在を示すのみ。",
        "最大ギャップが Confidence 候補付与であれば、それは Completeness 課題であり Hit 改善課題ではない。",
        "",
    ]
    ipath = docs / "v100-missing-metadata-inventory.md"
    ipath.write_text("\n".join(inv_md), encoding="utf-8")

    tr = report["trace_completeness"]
    tr_md = [
        "# Version100 — Trace Completeness",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "| Trace | Rate |",
        "|---|---:|",
        f"| Must Trace | {fmt(tr.get('must_trace_complete_rate'))} |",
        f"| Exclusion Trace | {fmt(tr.get('exclusion_trace_complete_rate'))} |",
        f"| Match Trace | {fmt(tr.get('match_trace_complete_rate'))} |",
        f"| Match Consistency | {fmt(tr.get('match_consistent_rate'))} |",
        f"| Decision Tree Trace (trigger_path∧decision_trace) | {fmt(tr.get('decision_tree_trace_rate'))} |",
        f"| Transition / path | {fmt(tr.get('transition_rate'))} |",
        "",
        "Decision Tree Trace は製品 Decision Layer ではなく、",
        "World 評価の `trigger_path` + `decision_trace` の保持を指す（観測）。",
        "",
    ]
    tpath = docs / "v100-trace-completeness.md"
    tpath.write_text("\n".join(tr_md), encoding="utf-8")

    sem = report["semantic_coverage"]
    sem_md = [
        "# Version100 — Semantic Coverage",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "**問い:** 各レースについて「なぜこの World になったのか」を Core が説明できるか？",
        "",
        f"- mean semantic score: **{fmt(sem.get('mean_semantic_score'))}**",
        f"- semantic_complete_rate: **{fmt(sem.get('semantic_complete_rate'))}**",
        f"- explainable_rate: **{fmt(sem.get('explainable_rate'))}**",
        "",
        "## 構成要素",
        "",
        "| Element | Coverage |",
        "|---|---:|",
    ]
    for k, v in (sem.get("part_rates") or {}).items():
        sem_md.append(f"| `{k}` | {fmt(v)} |")
    sem_md += [
        "",
        "## 要素の意味",
        "",
        "- must_satisfied_known / must_gaps_known / exclusion_reasons_known",
        "- near_miss_reasons_known（unsatisfied 時）",
        "- expected_strategy_known（V75 マップ解決）",
        "- transition_known / trigger_path_known",
        "",
        "Hit・ROI は含めない。",
        "",
    ]
    spath = docs / "v100-semantic-coverage.md"
    spath.write_text("\n".join(sem_md), encoding="utf-8")

    gov = [
        "# Version100 — Governance",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Action Type | Core Completeness Shadow Observation |",
        "| ADR | **ADR-009 正式採用** |",
        "| Implementation Required | **No** |",
        "| Deployment Required | No |",
        "| Prediction/Trigger/CEW/Decision Change | **No** |",
        "| KPI | Completeness only |",
        "| Excluded KPI | ROI / Hit / 券種 / Skip / 資金 |",
        "| Risk | Low |",
        "| Expected Next Action | Missing Inventory の優先欠落を別 Decision で設計。本 Shadow では修正しない |",
        "",
        "## Hard locks（遵守確認）",
        "",
        "- Prediction Logic / Ranking / Score / Confidence — 非変更",
        "- Trigger / World Definition / CEW — 非変更",
        "- Decision Layer / Single AI / Win5 AI — 非変更",
        "",
        "## 成果物",
        "",
        "| 成果物 | Path |",
        "|---|---|",
        "| Completeness Report | `v100-core-completeness-report.md` |",
        "| Missing Metadata Inventory | `v100-missing-metadata-inventory.md` |",
        "| Trace Completeness | `v100-trace-completeness.md` |",
        "| Semantic Coverage | `v100-semantic-coverage.md` |",
        "| Governance | `v100-governance.md` |",
        "| Data | `_v100-core-completeness-shadow.json` |",
        "",
    ]
    gpath = docs / "v100-governance.md"
    gpath.write_text("\n".join(gov), encoding="utf-8")

    return {
        "json": str(jpath),
        "per_race": str(jrows),
        "report": str(rpath),
        "inventory": str(ipath),
        "trace": str(tpath),
        "semantic": str(spath),
        "gov": str(gpath),
    }


def main() -> None:
    report = run()
    paths = write_docs(report)
    print(
        json.dumps(
            {
                "n_races": report["n_races"],
                "status": report["status"],
                "prediction_complete": report["aggregates"]["prediction"].get("prediction_complete"),
                "confidence_coverage": report["aggregates"]["prediction"].get("confidence_coverage"),
                "world_complete": report["aggregates"]["world"].get("world_complete"),
                "near_miss_complete": report["aggregates"]["near_miss"].get("near_miss_complete"),
                "semantic_complete_rate": report["aggregates"]["semantic"].get("semantic_complete_rate"),
                "missing_top10": list(report["missing_inventory"]["missing_counts"].items())[:10],
                "paths": paths,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
