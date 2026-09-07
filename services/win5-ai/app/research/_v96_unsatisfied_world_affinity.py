# -*- coding: utf-8 -*-
"""Version96 — Unsatisfied World Affinity Study (measurement only).

Purpose: measure how close each CEW=unsatisfied race is to
core / midupper / midhole / rank7 — NOT to reduce unsatisfied count.

Locks: Prediction / Trigger / CEW / World Meaning / PE / Production.
No product Decision Layer implementation.
"""
from __future__ import annotations

import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))
sys.path.insert(0, str(Path(r"C:\win5-ai")))

from app.research._v74_world_strategy_validation import load_cew_labels  # noqa: E402
from app.research.w_s1_shadow_dual_eval import (  # noqa: E402
    ranking_concepts,
    restore_trigger_signals,
    _f,
)

SCHEMA = "v96-unsatisfied-world-affinity/1.0"
AFFINITY_WORLDS = (
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
)
MUST_N = {
    "core_world": 2,
    "midupper_world": 3,
    "midhole_world": 2,
    "rank7_world": 3,
}
NEAR_PRIORITY = (
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _mean(xs: list[float]) -> float | None:
    return float(sum(xs) / len(xs)) if xs else None


def load_dual() -> dict[str, dict[str, Any]]:
    path = ROOT / "docs/implementation/w-s1-dual-eval-rows.jsonl"
    out: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            out[str(r["race_id"])] = r
    return out


def build_signals_for_race(rid: str, race: dict[str, Any], fx: dict[str, Any]) -> dict[str, float | None]:
    concepts = ranking_concepts(race) if race else {}
    field_size = fx.get("field_size") or (race.get("context") or {}).get("field_size")
    distance = fx.get("distance")
    restored = restore_trigger_signals(rid, field_size, distance)
    apt = None
    if distance is not None and field_size is not None:
        apt = min(1.0, float(distance) / 2500.0) * (1.0 if int(field_size) >= 12 else 0.4)
    dev = restored.get("phase") or restored.get("short_field_pressure") or restored.get("high_pace")
    return {
        **concepts,
        "difficulty": restored.get("difficulty"),
        "chaos": restored.get("chaos"),
        "high_pace": restored.get("high_pace"),
        "late_stop": restored.get("late_stop"),
        "sustained": restored.get("sustained"),
        "phase": restored.get("phase"),
        "short_field_pressure": restored.get("short_field_pressure"),
        "aptitude_fit": apt,
        "development_pressure": _f(dev),
        "exception_flag": None,
        "field_size": _f(field_size),
        "distance": _f(distance),
    }


def exclusion_reasons_research(signals: dict[str, float | None], thr: dict[str, float]) -> dict[str, list[str]]:
    """Research-only mirror of V44 Exclusion predicates (does not mutate platform)."""
    from ai_platform.core.world.v44_shadow_eval import _high, _low, _any_true, _all_known_true

    top_gap_hi = _high(signals, "top_gap", thr)
    sep_hi = _high(signals, "ability_separation", thr)
    upper_hi = _high(signals, "upper_ability_band", thr)
    mid_open = _high(signals, "mid_eval_band_open", thr)
    chaos_hi = _high(signals, "chaos", thr)
    high_pace_hi = _high(signals, "high_pace", thr)
    difficulty_hi = _high(signals, "difficulty", thr)
    sfp_hi = _high(signals, "short_field_pressure", thr)
    late_hi = _high(signals, "late_stop", thr)
    sust_hi = _high(signals, "sustained", thr)
    phase_hi = _high(signals, "phase", thr)
    apt_hi = _high(signals, "aptitude_fit", thr)
    if (
        _high(signals, "development_pressure", thr) is None
        and phase_hi is None
        and sfp_hi is None
        and high_pace_hi is None
    ):
        dev_axis = None
    else:
        dev_axis = bool(
            _any_true(
                [
                    _high(signals, "development_pressure", thr),
                    phase_hi,
                    sfp_hi,
                    high_pace_hi,
                ]
            )
        )

    late_and_sust = None if late_hi is None or sust_hi is None else bool(late_hi and sust_hi)
    chaos_and_diff = None if chaos_hi is None or difficulty_hi is None else bool(chaos_hi and difficulty_hi)

    core = []
    if chaos_hi is True:
        core.append("excl:chaos↑")
    if sfp_hi is True:
        core.append("excl:short_field_pressure↑")
    if late_and_sust is True:
        core.append("excl:late∧sustained")
    if mid_open is True:
        core.append("excl:mid_eval_band_open↑")

    midupper = []
    if chaos_hi is True and high_pace_hi is True:
        midupper.append("excl:chaos↑∧high_pace↑")
    if mid_open is True:
        midupper.append("excl:mid_eval_band_open↑")
    if top_gap_hi is True and dev_axis is not True and apt_hi is not True:
        midupper.append("excl:top_gap↑_without_dev/apt")

    midhole = []
    if top_gap_hi is True:
        midhole.append("excl:top_gap↑")
    if chaos_and_diff is True:
        midhole.append("excl:chaos↑∧difficulty↑")

    rank7 = []
    if top_gap_hi is True:
        rank7.append("excl:top_gap↑")
    if difficulty_hi is True and chaos_hi is not True:
        rank7.append("excl:difficulty↑_without_chaos")

    return {
        "core_world": core,
        "midupper_world": midupper,
        "midhole_world": midhole,
        "rank7_world": rank7,
    }


def affinity_for_world(trace_w: dict[str, Any], world: str) -> dict[str, Any]:
    gaps = list(trace_w.get("must_gaps") or [])
    n_must = MUST_N[world]
    n_gap = len(gaps)
    # clamp: gap list length should be <= n_must
    must_affinity = max(0.0, min(1.0, (n_must - n_gap) / n_must))
    must_ok = bool(trace_w.get("must"))
    excl = bool(trace_w.get("exclude"))
    if must_ok:
        must_affinity = 1.0
    # Decision-facing affinity: Must proximity is primary; Exclusion does not reduce
    # closeness-to-world (it explains why CEW stayed unsatisfied).
    affinity = must_affinity
    if must_ok and excl:
        mode = "NEAR_MISS"
        conf = "HIGH"
    elif must_affinity >= 0.67 and not must_ok:
        mode = "PARTIAL_MUST"
        conf = "MED"
    elif must_affinity > 0:
        mode = "WEAK_MUST"
        conf = "LOW"
    else:
        mode = "NO_MUST"
        conf = "LOW"
    if excl and not must_ok:
        # excluded even without must — still note block
        block = "exclusion_without_must"
    elif excl and must_ok:
        block = "exclusion_after_must"
    else:
        block = "must_incomplete" if not must_ok else "none"
    return {
        "must": must_ok,
        "exclude": excl,
        "must_gaps": gaps,
        "n_must": n_must,
        "n_gaps": n_gap,
        "must_affinity": round(affinity, 4),
        "mode": mode,
        "affinity_confidence": conf,
        "block": block,
    }


def structural_class(trace: dict[str, Any]) -> str:
    any_near = False
    any_must = False
    for w in AFFINITY_WORLDS:
        t = (trace or {}).get(w) or {}
        if t.get("must"):
            any_must = True
            if t.get("exclude"):
                any_near = True
    if any_near:
        return "NEAR_MISS"
    if not any_must:
        return "PURE_RESIDUAL"
    return "PURE_RESIDUAL"


def primary_near_world(aff: dict[str, dict[str, Any]]) -> str | None:
    # Near Miss: must&exclude by priority
    for w in NEAR_PRIORITY:
        a = aff[w]
        if a["must"] and a["exclude"]:
            return w
    return None


def argmax_affinity(aff: dict[str, dict[str, Any]]) -> tuple[str, float]:
    best_w = AFFINITY_WORLDS[0]
    best_v = -1.0
    for w in AFFINITY_WORLDS:
        v = float(aff[w]["must_affinity"])
        # tie-break: prefer Near Miss mode, then priority order
        if v > best_v + 1e-12:
            best_v = v
            best_w = w
        elif abs(v - best_v) <= 1e-12:
            # prefer NEAR_MISS, else earlier priority
            if aff[w]["mode"] == "NEAR_MISS" and aff[best_w]["mode"] != "NEAR_MISS":
                best_w = w
            elif aff[w]["mode"] == aff[best_w]["mode"]:
                if NEAR_PRIORITY.index(w) < NEAR_PRIORITY.index(best_w):
                    best_w = w
    return best_w, best_v


def race_affinity_confidence(aff: dict[str, dict[str, Any]], top_w: str, top_v: float) -> str:
    vals = sorted((float(aff[w]["must_affinity"]) for w in AFFINITY_WORLDS), reverse=True)
    gap = vals[0] - vals[1] if len(vals) > 1 else vals[0]
    top_mode = aff[top_w]["mode"]
    if top_mode == "NEAR_MISS" and gap >= 0.0:
        # unique near miss or shared
        near_count = sum(1 for w in AFFINITY_WORLDS if aff[w]["mode"] == "NEAR_MISS")
        if near_count == 1 and top_v >= 1.0:
            return "HIGH"
        if near_count >= 2:
            return "MED"  # multi near-miss ambiguity
        return "HIGH"
    if top_v >= 0.67 and gap >= 0.34:
        return "MED"
    if top_v >= 0.5:
        return "LOW"
    return "VERY_LOW"


def decision_impact(residual_class: str, top_w: str, conf: str, near_primary: str | None) -> dict[str, Any]:
    """Design-only: which V95 Decision template would be selected — no code change."""
    if residual_class == "NEAR_MISS" and near_primary:
        return {
            "decision_template": f"near_miss:{near_primary}",
            "ticket": "conservative",
            "risk": "high_suppress" if near_primary in ("core_world", "midupper_world") else "mid_suppress",
            "pool": "topk_annotate_only",
            "explain": f"near_miss:{near_primary}",
            "affinity_top_agrees_primary": top_w == near_primary,
            "affinity_confidence": conf,
        }
    return {
        "decision_template": "pure_residual",
        "ticket": "conservative",
        "risk": "standard_conservative",
        "pool": "topk_only",
        "explain": "pure_residual",
        "affinity_top_suggests": top_w,
        "note": "Affinity top is observational only; PURE_RESIDUAL must not adopt Positive Ticket",
        "affinity_confidence": conf,
    }


def run() -> dict[str, Any]:
    os.environ.setdefault("W_TRIGGER_PATH", "legacy")
    from ai_platform.core.world.v44_shadow_eval import (
        build_polarity_thresholds,
        evaluate_v44_logic_form,
    )

    cew = load_cew_labels()
    dual = load_dual()
    corp = json.loads(
        (ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(encoding="utf-8")
    )
    races_by = {str(r["race_id"]): r for r in corp["races"]}
    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fx_rows = fx.get("rows") or fx.get("evaluations") or []
    fxby = {str(r["race_id"]): r for r in fx_rows}

    # Build signal table once for polarity thresholds (same method as V73)
    signal_table: list[dict[str, float | None]] = []
    unsat_ids = [rid for rid, w in cew.items() if w == "unsatisfied"]
    # thresholds from full corpus signals (stable)
    all_ids = list(cew.keys())
    for rid in all_ids:
        race = races_by.get(rid) or {}
        fxr = fxby.get(rid) or {}
        signal_table.append(build_signals_for_race(rid, race, fxr))
    thr = build_polarity_thresholds(signal_table)

    rows_out: list[dict[str, Any]] = []
    matrix_sum = {w: 0.0 for w in AFFINITY_WORLDS}
    matrix_near = {w: 0 for w in AFFINITY_WORLDS}
    matrix_partial = {w: 0 for w in AFFINITY_WORLDS}
    excl_reason_counter: dict[str, Counter] = {w: Counter() for w in AFFINITY_WORLDS}
    must_gap_counter: dict[str, Counter] = {w: Counter() for w in AFFINITY_WORLDS}
    top_counter: Counter = Counter()
    class_counter: Counter = Counter()
    conf_counter: Counter = Counter()
    agree_primary = 0
    near_n = 0
    impact_templates: Counter = Counter()

    for rid in sorted(unsat_ids):
        race = races_by.get(rid) or {}
        fxr = fxby.get(rid) or {}
        drow = dual.get(rid) or {}
        # Prefer stored dual trace (CEW-aligned Shadow); re-eval for exclusion reasons
        signals = build_signals_for_race(rid, race, fxr)
        v44 = evaluate_v44_logic_form(signals, thr)
        # Consistency: use dual decision_trace when present (source of V94), else re-eval
        trace = drow.get("decision_trace") or v44.get("decision_trace") or {}
        excl_reasons = exclusion_reasons_research(signals, thr)

        aff: dict[str, dict[str, Any]] = {}
        for w in AFFINITY_WORLDS:
            tw = (trace.get(w) or {})
            a = affinity_for_world(tw, w)
            a["exclusion_reasons"] = list(excl_reasons.get(w) or [])
            # if exclude true but reasons empty (unknown signals), keep placeholder
            if a["exclude"] and not a["exclusion_reasons"]:
                a["exclusion_reasons"] = ["excl:unresolved_or_missing_signal"]
            aff[w] = a
            matrix_sum[w] += a["must_affinity"]
            if a["mode"] == "NEAR_MISS":
                matrix_near[w] += 1
            if a["mode"] == "PARTIAL_MUST":
                matrix_partial[w] += 1
            for g in a["must_gaps"]:
                must_gap_counter[w][g] += 1
            for er in a["exclusion_reasons"]:
                if a["exclude"]:
                    excl_reason_counter[w][er] += 1

        residual_class = structural_class(trace)
        class_counter[residual_class] += 1
        near_primary = primary_near_world(aff)
        top_w, top_v = argmax_affinity(aff)
        top_counter[top_w] += 1
        conf = race_affinity_confidence(aff, top_w, top_v)
        conf_counter[conf] += 1
        if residual_class == "NEAR_MISS":
            near_n += 1
            if top_w == near_primary:
                agree_primary += 1
        impact = decision_impact(residual_class, top_w, conf, near_primary)
        impact_templates[impact["decision_template"]] += 1

        rows_out.append(
            {
                "race_id": rid,
                "cew_world": "unsatisfied",
                "residual_class": residual_class,
                "near_world_primary": near_primary,
                "affinity": {w: aff[w] for w in AFFINITY_WORLDS},
                "affinity_top": top_w,
                "affinity_top_value": top_v,
                "affinity_confidence": conf,
                "decision_impact": impact,
                "restored_ok": drow.get("restored_ok"),
            }
        )

    n = len(rows_out)
    assert n == 176, f"expected 176, got {n}"

    # Soft affinity matrix: mean must_affinity; also near-miss counts
    affinity_matrix = {
        w: {
            "mean_must_affinity": matrix_sum[w] / n,
            "near_miss_count": matrix_near[w],
            "partial_must_count": matrix_partial[w],
            "share_as_affinity_top": top_counter[w] / n,
        }
        for w in AFFINITY_WORLDS
    }

    # Pairwise: among races, P(affinity_w >= t)
    thresholds = [0.34, 0.5, 0.67, 1.0]
    coverage = {}
    for t in thresholds:
        coverage[str(t)] = {
            w: sum(1 for r in rows_out if r["affinity"][w]["must_affinity"] + 1e-12 >= t) / n
            for w in AFFINITY_WORLDS
        }

    near_dist = Counter(r["near_world_primary"] for r in rows_out if r["residual_class"] == "NEAR_MISS")

    report = {
        "schema": SCHEMA,
        "generated_at": _now(),
        "purpose": "Measure World Affinity of unsatisfied — not to reduce unsatisfied count",
        "locks": ["Prediction", "Trigger", "CEW", "World Meaning", "PE", "Production", "Decision product impl"],
        "n_unsatisfied": n,
        "affinity_definition": {
            "must_affinity": "(n_must - n_gaps) / n_must; 1.0 if must=True",
            "near_miss": "must=True AND exclude=True",
            "exclusion_reasons": "research mirror of V44 Exclusion predicates",
            "affinity_confidence": "HIGH=unique Near Miss; MED=multi Near Miss or clear partial; LOW/VERY_LOW otherwise",
            "targets": list(AFFINITY_WORLDS),
        },
        "class_distribution": dict(class_counter),
        "affinity_matrix": affinity_matrix,
        "affinity_coverage_by_threshold": coverage,
        "affinity_top_distribution": dict(top_counter),
        "affinity_confidence_distribution": dict(conf_counter),
        "near_miss_distribution": dict(near_dist),
        "near_miss_affinity_agrees_primary_rate": (agree_primary / near_n) if near_n else None,
        "must_gap_attribution": {w: dict(must_gap_counter[w].most_common(12)) for w in AFFINITY_WORLDS},
        "exclusion_reason_attribution": {
            w: dict(excl_reason_counter[w].most_common(12)) for w in AFFINITY_WORLDS
        },
        "decision_impact_templates": dict(impact_templates),
        "rows": rows_out,
    }
    return report


def write_docs(report: dict[str, Any]) -> dict[str, str]:
    docs = ROOT / "docs/research"
    docs.mkdir(parents=True, exist_ok=True)

    # Full JSON may be large — write full + slim
    jfull = docs / "_v96-unsatisfied-world-affinity.json"
    jfull.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    slim = {k: v for k, v in report.items() if k != "rows"}
    slim["n_rows"] = len(report["rows"])
    # sample 5 near + 5 residual
    samples = []
    for want in ("NEAR_MISS", "PURE_RESIDUAL"):
        c = 0
        for r in report["rows"]:
            if r["residual_class"] == want and c < 3:
                samples.append(
                    {
                        "race_id": r["race_id"],
                        "residual_class": r["residual_class"],
                        "near_world_primary": r["near_world_primary"],
                        "affinity_top": r["affinity_top"],
                        "affinity_confidence": r["affinity_confidence"],
                        "affinities": {w: r["affinity"][w]["must_affinity"] for w in AFFINITY_WORLDS},
                        "excl": {
                            w: r["affinity"][w]["exclusion_reasons"]
                            for w in AFFINITY_WORLDS
                            if r["affinity"][w]["exclude"]
                        },
                        "gaps": {
                            w: r["affinity"][w]["must_gaps"]
                            for w in AFFINITY_WORLDS
                            if r["affinity"][w]["must_gaps"]
                        },
                    }
                )
                c += 1
    slim["samples"] = samples
    jslim = docs / "_v96-unsatisfied-world-affinity-summary.json"
    jslim.write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")

    am = report["affinity_matrix"]
    cov = report["affinity_coverage_by_threshold"]

    matrix_md = [
        "# Version96 — World Affinity Matrix",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        f"**Population:** unsatisfied n={report['n_unsatisfied']}  ",
        "**目的:** unsatisfied 削減ではなく、各 World への近さを測定  ",
        "**Locks:** Prediction / Trigger / CEW / World — 非変更 · **実装禁止**",
        "",
        "## Affinity 定義",
        "",
        "- `must_affinity = (n_must − n_gaps) / n_must`（must=True なら 1.0）",
        "- `NEAR_MISS` = must∧exclude（近さは最大、CEW は unsatisfied のまま）",
        "- Exclusion は近さを下げない（未 MATCH の理由として保持）",
        "",
        "## Mean Must Affinity（行=対象 World）",
        "",
        "| World | mean affinity | Near Miss n | Partial Must n | share as affinity-top |",
        "|---|---:|---:|---:|---:|",
    ]
    for w in AFFINITY_WORLDS:
        m = am[w]
        matrix_md.append(
            f"| `{w}` | {m['mean_must_affinity']:.3f} | {m['near_miss_count']} | "
            f"{m['partial_must_count']} | {m['share_as_affinity_top']:.3f} |"
        )

    matrix_md += [
        "",
        "## Coverage P(affinity ≥ t)",
        "",
        "| t | core | midupper | midhole | rank7 |",
        "|---:|---:|---:|---:|---:|",
    ]
    for t, row in cov.items():
        matrix_md.append(
            f"| {t} | {row['core_world']:.3f} | {row['midupper_world']:.3f} | "
            f"{row['midhole_world']:.3f} | {row['rank7_world']:.3f} |"
        )

    matrix_md += [
        "",
        "## Affinity-top 分布",
        "",
        "```",
        json.dumps(report["affinity_top_distribution"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## Affinity Confidence 分布",
        "",
        "```",
        json.dumps(report["affinity_confidence_distribution"], ensure_ascii=False, indent=2),
        "```",
        "",
        f"Near Miss において affinity-top ≡ primary near_world 一致率: "
        f"**{_fmt(report['near_miss_affinity_agrees_primary_rate'])}**",
        "",
        "## Decision Impact（設計マッピング・未実装）",
        "",
        "```",
        json.dumps(report["decision_impact_templates"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## 解釈（短縮）",
        "",
        "1. Affinity は CEW を書き換えない。",
        "2. 高い Affinity + Exclusion = Near Miss（V95 Metadata）。",
        "3. Pure Residual でも弱い Affinity は観測してよいが、Positive Ticket 化禁止。",
        "",
    ]
    mpath = docs / "v96-affinity-matrix.md"
    mpath.write_text("\n".join(matrix_md), encoding="utf-8")

    # Near Miss Attribution
    attr = [
        "# Version96 — Near Miss Attribution",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "## Near Miss Distribution（primary）",
        "",
        "| near_world | n |",
        "|---|---:|",
    ]
    for w, c in sorted(report["near_miss_distribution"].items(), key=lambda x: -(x[1] or 0)):
        attr.append(f"| `{w}` | {c} |")
    attr += [
        "",
        f"class_distribution: `{report['class_distribution']}`",
        "",
        "## Must Gap Attribution（unsatisfied 全体・出現レース数）",
        "",
    ]
    for w in AFFINITY_WORLDS:
        attr.append(f"### `{w}`")
        attr.append("")
        attr.append("| must_gap | n |")
        attr.append("|---|---:|")
        for g, c in report["must_gap_attribution"][w].items():
            attr.append(f"| `{g}` | {c} |")
        attr.append("")
    attr += [
        "## Exclusion Reason Attribution（exclude=True のレースで発火）",
        "",
    ]
    for w in AFFINITY_WORLDS:
        attr.append(f"### `{w}`")
        attr.append("")
        attr.append("| exclusion_reason | n |")
        attr.append("|---|---:|")
        items = report["exclusion_reason_attribution"][w]
        if not items:
            attr.append("| _(none)_ | 0 |")
        else:
            for g, c in items.items():
                attr.append(f"| `{g}` | {c} |")
        attr.append("")
    attr += [
        "## 保持契約",
        "",
        "- Near Miss レコードは **Must Gap** と **Exclusion Reason** を両方保持する。",
        "- Affinity スコアは Must 近さ。Exclusion はブロック理由であり、近さの減点ではない。",
        "",
    ]
    apath = docs / "v96-near-miss-attribution.md"
    apath.write_text("\n".join(attr), encoding="utf-8")

    # Taxonomy update
    tax = [
        "# Version96 — Residual Taxonomy Update",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "**Base:** V95 Residual Decision Taxonomy  ",
        "**Change type:** Metadata 精密化（CEW / World 非変更）",
        "",
        "## 更新内容",
        "",
        "V95 の `near_world`（priority primary）に加え、各 World の **連続 Affinity** を Meta に載せてよい（設計）。",
        "",
        "```text",
        "ResidualTaxonomyMeta (v96)",
        "  world_id: \"unsatisfied\"",
        "  residual_class: NEAR_MISS | PURE_RESIDUAL",
        "  near_world: WorldId | null          # V95 primary（Exclusion）",
        "  affinity: {",
        "    core_world: float,                # must_affinity [0,1]",
        "    midupper_world: float,",
        "    midhole_world: float,",
        "    rank7_world: float",
        "  }",
        "  affinity_top: WorldId",
        "  affinity_confidence: HIGH|MED|LOW|VERY_LOW",
        "  must_gaps_by_world: {...}",
        "  exclusion_reasons_by_world: {...}   # Near Miss で必須保持",
        "  taxonomy_version: \"v96/1.0\"",
        "```",
        "",
        "## V95 との差分",
        "",
        "| 項目 | V95 | V96 |",
        "|---|---|---|",
        "| 分類 | NEAR_MISS / PURE_RESIDUAL | **同じ（維持）** |",
        "| near_world | primary 1 ラベル | **維持** |",
        "| Affinity vector | なし | **追加（観測）** |",
        "| Must Gap / Exclusion | 構造定義のみ | **レース単位で保持** |",
        "| CEW | unsatisfied | **変更なし** |",
        "",
        "## 衝突ルール",
        "",
        "1. `residual_class` は構造（Exclusion / Must全失敗）が優先。Affinity で上書きしない。",
        "2. Decision の Explain/Risk 主キーは V95 どおり `near_world`（Near Miss）または `pure_residual`。",
        "3. `affinity_top ≠ near_world` のときは **注記のみ**（Ticket 切替禁止）。",
        f"4. 実測: Near Miss で affinity-top≡primary 一致率 = {_fmt(report['near_miss_affinity_agrees_primary_rate'])}。",
        "",
        "## 禁止（維持）",
        "",
        "- Affinity 高い → CEW 書き換え / 新 World 追加 / Positive Ticket 化",
        "- unsatisfied 件数を減らすための Threshold 変更（本スタディの目的外）",
        "",
    ]
    tpath = docs / "v96-residual-taxonomy-update.md"
    tpath.write_text("\n".join(tax), encoding="utf-8")

    gov = [
        "# Version96 — Governance",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Action Type | Unsatisfied World Affinity Study（測定） |",
        "| Implementation Required | **No**（製品 Decision / PE / Trigger 非変更） |",
        "| Deployment Required | No |",
        "| CEW / World Change | **No** |",
        "| Purpose | Affinity 測定。unsatisfied **削減ではない** |",
        "| New World | **No** |",
        "| Risk | Low（研究測定） |",
        "| Expected Next Action | Affinity を Explain 注記に載せる Shadow は別 Decision。Threshold 改変は禁止継続 |",
        "",
        "## Hard locks",
        "",
        "- Prediction / Trigger / CEW / World Meaning / PE / Production",
        "- 製品 `app/decision/*` 実装禁止（本フェーズ）",
        "- Affinity ≠ ラベル書き換え権限",
        "",
        "## 成果物",
        "",
        "| 成果物 | Path |",
        "|---|---|",
        "| Affinity Matrix | `v96-affinity-matrix.md` |",
        "| Residual Taxonomy Update | `v96-residual-taxonomy-update.md` |",
        "| Near Miss Attribution | `v96-near-miss-attribution.md` |",
        "| Governance | `v96-governance.md` |",
        "| Data | `_v96-unsatisfied-world-affinity.json` |",
        "",
    ]
    gpath = docs / "v96-governance.md"
    gpath.write_text("\n".join(gov), encoding="utf-8")

    return {
        "json": str(jfull),
        "summary": str(jslim),
        "matrix": str(mpath),
        "attribution": str(apath),
        "taxonomy": str(tpath),
        "gov": str(gpath),
    }


def _fmt(x: Any) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.3f}"
    return str(x)


def main() -> None:
    report = run()
    paths = write_docs(report)
    print(
        json.dumps(
            {
                "n": report["n_unsatisfied"],
                "class_distribution": report["class_distribution"],
                "affinity_matrix": report["affinity_matrix"],
                "near_miss_distribution": report["near_miss_distribution"],
                "affinity_confidence_distribution": report["affinity_confidence_distribution"],
                "near_miss_agree_primary": report["near_miss_affinity_agrees_primary_rate"],
                "decision_impact_templates": report["decision_impact_templates"],
                "paths": paths,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
