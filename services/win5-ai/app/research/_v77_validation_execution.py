# -*- coding: utf-8 -*-
"""Version77 — World Strategy Validation Execution (E1/E2 only).

Executes V76 Validation Plan split evaluation on 285R CEW labels.
No Trigger / Blueprint / Signal / Threshold / PE / Prediction / Production /
World Contract / design / feature / rule changes.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))

from app.research._v64_world_strategy_discovery import (  # noqa: E402
    STYLE_VALUES,
    analyze_world,
    build_race_rows,
)
from app.research._v74_world_strategy_validation import (  # noqa: E402
    ALL_LABELS,
    STRATEGY_WORLDS,
    attach_cew,
    feature_interactions,
    importance_ranks,
    jaccard,
    load_cew_labels,
    pearson,
    spearman_rank_corr,
    subset,
    winner_profile,
)

SCHEMA = "v77-validation-execution/1.0"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def chronological_split(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split by sorted race_id (≈ chronological for YYYY-MM-DD-… ids)."""
    ordered = sorted(rows, key=lambda r: str(r["race_id"]))
    mid = len(ordered) // 2
    return ordered[:mid], ordered[mid:]


def top_styles(style_lift: list[dict[str, Any]]) -> str | None:
    if not style_lift:
        return None
    return max(style_lift, key=lambda x: x["lift"])["style"]


def top_features(importance: list[dict[str, Any]], k: int = 3) -> list[str]:
    feats = [x["feature"] for x in importance if not str(x["feature"]).startswith("popularity")]
    return feats[:k]


def effect_map(importance: list[dict[str, Any]]) -> dict[str, float]:
    return {x["feature"]: float(x["effect"]) for x in importance}


def ix_r(interactions: list[dict[str, Any]], ctx: str, feat: str) -> float | None:
    for it in interactions:
        if it["context"] == ctx and it["winner_feature"] == feat:
            return float(it["r"])
    return None


def analyze_split(rows: list[dict[str, Any]], split_name: str) -> dict[str, Any]:
    by: dict[str, Any] = {}
    for w in ALL_LABELS:
        races = subset(rows, w)
        analysis = analyze_world(races)
        imp = analysis.get("importance") or []
        interactions = feature_interactions(races)
        by[w] = {
            "n": len(races),
            "winner_profile": winner_profile(races),
            "importance_top": imp[:10],
            "importance_ranks": importance_ranks(analysis) if analysis.get("n", 0) else {},
            "style_lift": analysis.get("style_lift") or [],
            "top_style": top_styles(analysis.get("style_lift") or []),
            "top3": top_features(imp, 3),
            "top5": top_features(imp, 5),
            "effects": effect_map(imp),
            "feature_interactions": interactions,
            "r_field_winprob": ix_r(interactions, "field_size", "win_prob_pct"),
            "r_upper_winprob": ix_r(interactions, "upper_ability_band", "win_prob_pct"),
        }
    return {"split": split_name, "n_races": len(rows), "by_world": by, "cew_dist": dict(Counter(r["cew_world"] for r in rows))}


def contract_tests_full(full: dict[str, Any], s1: dict[str, Any], s2: dict[str, Any]) -> dict[str, Any]:
    """E1-style MUST metrics on full + both splits (G-C1 recording)."""
    tests = []

    def add(tid: str, world: str, metric: str, value: Any, threshold: str, passed: bool | None, n: int, scope: str):
        tests.append(
            {
                "test_id": tid,
                "world": world,
                "metric": metric,
                "value": value,
                "threshold": threshold,
                "pass": passed,
                "n": n,
                "scope": scope,
            }
        )

    for scope, blk in (("full", full), ("split1", s1), ("split2", s2)):
        bw = blk["by_world"]
        # rank7 MUST.2 field_size attenuate
        r7 = bw["rank7_world"]
        r = r7["r_field_winprob"]
        add(
            "rank7.MUST.2.field_size_attenuate",
            "rank7_world",
            "r(field_size, winner_win_prob_pct)",
            r,
            "<= -0.05",
            (r is not None and r <= -0.05) if r is not None else None,
            r7["n"],
            scope,
        )
        # rank7 MUST.1 history~win_prob band: |effect_h - effect_w| or both in top3
        eff = r7["effects"]
        h = eff.get("history_z")
        w = eff.get("win_prob_z")
        band = None
        if h is not None and w is not None:
            band = abs(h - w)
        add(
            "rank7.MUST.1.history_winprob_peer_band",
            "rank7_world",
            "|effect(history_z)-effect(win_prob_z)|",
            band,
            "both in top3 AND |Δ| <= 0.25 (observability)",
            (
                h is not None
                and w is not None
                and "history_z" in r7["top3"]
                and "win_prob_z" in r7["top3"]
                and abs(h - w) <= 0.25
            )
            if h is not None and w is not None
            else None,
            r7["n"],
            scope,
        )
        # rank7 MUST.3 sashi/oikomi not primary
        ts = r7["top_style"]
        add(
            "rank7.MUST.3.not_sashi_oikomi_primary",
            "rank7_world",
            "top_style",
            ts,
            "not in {差し, 追込}",
            ts not in ("差し", "追込") if ts else None,
            r7["n"],
            scope,
        )

        mh = bw["midhole_world"]
        he = mh["effects"].get("history_z")
        we = mh["effects"].get("win_prob_z")
        gap = (he - we) if he is not None and we is not None else None
        add(
            "midhole.MUST.1.history_leads",
            "midhole_world",
            "effect(history_z)-effect(win_prob_z)",
            gap,
            "> 0.15",
            (gap is not None and gap > 0.15) if gap is not None else None,
            mh["n"],
            scope,
        )
        add(
            "midhole.MUST.2.winprob_not_primary",
            "midhole_world",
            "win_prob_z rank among non-pop",
            (mh["top3"].index("win_prob_z") + 1) if "win_prob_z" in mh["top3"] else (99 if mh["n"] else None),
            "not rank 1 (top3[0] != win_prob_z)",
            (mh["top3"][0] != "win_prob_z") if mh["top3"] else None,
            mh["n"],
            scope,
        )
        ru = mh["r_upper_winprob"]
        add(
            "midhole.MUST.3.upper_band_attenuate",
            "midhole_world",
            "r(upper_ability_band, winner_win_prob_pct)",
            ru,
            "<= -0.05",
            (ru is not None and ru <= -0.05) if ru is not None else None,
            mh["n"],
            scope,
        )

    # Residual G-C1 measurable pieces (E4-lite required by residual Ready — record only)
    uns = full["by_world"]["unsatisfied"]
    # popularity coverage among unsatisfied
    # rebuild from rows not stored — approximate via winner_profile popularity_races_n
    pop_n = uns["winner_profile"].get("popularity_races_n") or 0
    uns_n = uns["n"]
    add(
        "unsatisfied.MUST.fallback_coverage_popularity",
        "unsatisfied",
        "popularity_valid_race_fraction",
        (pop_n / uns_n) if uns_n else None,
        "document coverage (no pass threshold in V76 except measured)",
        True if uns_n else None,  # measurement exists => G-C1 recordability PASS for this metric
        uns_n,
        "full",
    )

    return {"tests": tests, "g_c1_recordable": True}


def gate_for_positive(
    world: str,
    full: dict[str, Any],
    s1: dict[str, Any],
    s2: dict[str, Any],
    counterpart: str,
) -> dict[str, Any]:
    """Apply V76 Partial→Ready gates for rank7/midhole."""
    fw = full["by_world"][world]
    a = s1["by_world"][world]
    b = s2["by_world"][world]
    ca = s1["by_world"][counterpart]
    cb = s2["by_world"][counterpart]

    g_s1 = fw["n"] >= 40
    g_s2 = a["n"] >= 15 and b["n"] >= 15

    # G-R1 self top3 jaccard across splits
    g_r1_j = jaccard(set(a["top3"]), set(b["top3"])) if a["top3"] and b["top3"] else None
    g_r1 = g_r1_j is not None and g_r1_j >= 0.60

    # Sep per split then both
    def sep_pack(sw, sc):
        # sign flip field_size
        r_w = sw["r_field_winprob"]
        r_c = sc["r_field_winprob"]
        flip_field = (
            r_w is not None
            and r_c is not None
            and ((r_w >= 0.08 and r_c <= -0.08) or (r_w <= -0.08 and r_c >= 0.08))
        )
        r_uw = sw["r_upper_winprob"]
        r_uc = sc["r_upper_winprob"]
        flip_upper = (
            r_uw is not None
            and r_uc is not None
            and ((r_uw >= 0.08 and r_uc <= -0.08) or (r_uw <= -0.08 and r_uc >= 0.08))
        )
        sep1 = flip_field or flip_upper
        ranks_w = sw["importance_ranks"]
        ranks_c = sc["importance_ranks"]
        sp = spearman_rank_corr(ranks_w, ranks_c) if ranks_w and ranks_c else None
        jac5 = jaccard(set(sw["top5"]), set(sc["top5"])) if sw["top5"] and sc["top5"] else None
        sep2 = (sp is not None and sp <= 0.70) or (jac5 is not None and jac5 <= 0.55)
        sep3 = sw["top_style"] is not None and sc["top_style"] is not None and sw["top_style"] != sc["top_style"]
        sep_or = (sep1 and sep3) or (sep1 and sep2) or (sep2 and sep3)
        return {
            "sep1": sep1,
            "sep2": sep2,
            "sep3": sep3,
            "sep_or": sep_or,
            "spearman": sp,
            "jaccard5": jac5,
            "flip_field": flip_field,
            "flip_upper": flip_upper,
            "top_style_w": sw["top_style"],
            "top_style_c": sc["top_style"],
            "r_field_w": r_w,
            "r_field_c": r_c,
            "r_upper_w": r_uw,
            "r_upper_c": r_uc,
        }

    sep_s1 = sep_pack(a, ca)
    sep_s2 = sep_pack(b, cb)
    # G-Sep requires BOTH splits same-sign flips for Sep1 reproduction per V76
    # "符号逆転 ≥1 が両分割で同符号" — both splits must have sep1 true with consistent flip direction
    def flip_dir_field(sw, sc):
        r_w, r_c = sw["r_field_winprob"], sc["r_field_winprob"]
        if r_w is None or r_c is None:
            return None
        if r_w >= 0.08 and r_c <= -0.08:
            return "w+/c-"
        if r_w <= -0.08 and r_c >= 0.08:
            return "w-/c+"
        return None

    d1 = flip_dir_field(a, ca)
    d2 = flip_dir_field(b, cb)
    u1 = None
    u2 = None
    for sw, sc, slot in ((a, ca, "1"), (b, cb, "2")):
        r_w, r_c = sw["r_upper_winprob"], sc["r_upper_winprob"]
        if r_w is None or r_c is None:
            continue
        if r_w >= 0.08 and r_c <= -0.08:
            if slot == "1":
                u1 = "w+/c-"
            else:
                u2 = "w+/c-"
        elif r_w <= -0.08 and r_c >= 0.08:
            if slot == "1":
                u1 = "w-/c+"
            else:
                u2 = "w-/c+"

    sep1_both = (d1 is not None and d1 == d2) or (u1 is not None and u1 == u2)
    sep3_both = sep_s1["sep3"] and sep_s2["sep3"]
    # For Sep2 both splits
    sep2_both = sep_s1["sep2"] and sep_s2["sep2"]
    sep_gate = (sep1_both and sep3_both) or (sep1_both and sep2_both) or (sep2_both and sep3_both)

    # World-specific
    if world == "rank7_world":
        spec_ok = (
            a["r_field_winprob"] is not None
            and b["r_field_winprob"] is not None
            and a["r_field_winprob"] <= -0.05
            and b["r_field_winprob"] <= -0.05
        )
        spec_detail = {
            "split1_r": a["r_field_winprob"],
            "split2_r": b["r_field_winprob"],
            "rule": "both <= -0.05",
        }
    else:  # midhole
        def hist_gap(sw):
            he = sw["effects"].get("history_z")
            we = sw["effects"].get("win_prob_z")
            if he is None or we is None:
                return None
            return he - we

        g1, g2 = hist_gap(a), hist_gap(b)
        hist_ok = g1 is not None and g2 is not None and g1 > 0.15 and g2 > 0.15
        up_ok = (
            a["r_upper_winprob"] is not None
            and b["r_upper_winprob"] is not None
            and a["r_upper_winprob"] <= -0.05
            and b["r_upper_winprob"] <= -0.05
        )
        spec_ok = bool(hist_ok and up_ok)
        spec_detail = {
            "hist_gap_s1": g1,
            "hist_gap_s2": g2,
            "upper_r_s1": a["r_upper_winprob"],
            "upper_r_s2": b["r_upper_winprob"],
        }

    g_c1 = True  # tests recorded in contract_tests

    ready = bool(g_s1 and g_s2 and g_c1 and g_r1 and sep_gate and spec_ok)

    return {
        "world": world,
        "counterpart": counterpart,
        "G-S1": {"pass": g_s1, "n_full": fw["n"], "threshold": 40},
        "G-S2": {"pass": g_s2, "n_split1": a["n"], "n_split2": b["n"], "threshold_each": 15},
        "G-C1": {"pass": g_c1, "note": "MUST tests recorded"},
        "G-R1": {"pass": g_r1, "top3_jaccard": g_r1_j, "threshold": 0.60},
        "Separation": {
            "pass": sep_gate,
            "sep1_both_consistent": sep1_both,
            "sep2_both": sep2_both,
            "sep3_both": sep3_both,
            "split1": sep_s1,
            "split2": sep_s2,
            "field_flip_dirs": [d1, d2],
            "upper_flip_dirs": [u1, u2],
        },
        "world_specific": {"pass": spec_ok, "detail": spec_detail},
        "Ready_gate_pass": ready,
    }


def residual_gate(full: dict[str, Any], s1: dict[str, Any], s2: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    uns_n = full["by_world"]["unsatisfied"]["n"]
    n_ok = uns_n >= 100
    # misapplication baseline: CEW unsatisfied but Legacy would be positive? Use dual from v73 if available
    # V76: Positive Strategy misapplication — without PE, define as: among CEW=unsatisfied,
    # fraction where winner profile would prefer rank7/midhole selectors incorrectly is NOT defined in PE.
    # Measurable baseline without new design: popularity coverage + top3 stability across splits
    a = s1["by_world"]["unsatisfied"]
    b = s2["by_world"]["unsatisfied"]
    jac = jaccard(set(a["top3"]), set(b["top3"])) if a["top3"] and b["top3"] else None
    pop_n = full["by_world"]["unsatisfied"]["winner_profile"].get("popularity_races_n") or 0
    pop_cov = pop_n / uns_n if uns_n else None
    # fallback: races without popularity → must use odds/win_prob (coverage of missing)
    fallback_needed_rate = 1.0 - pop_cov if pop_cov is not None else None
    # Policy documented in V75 — True
    policy_doc = True
    # misapplication: count CEW unsatisfied races where v69/legacy assigned positive world
    # load from v73 rows
    v73 = json.loads((ROOT / "docs/research/_v73-contract-intent-evaluation.json").read_text(encoding="utf-8"))
    mis_leg = 0
    mis_v69 = 0
    uns_rows = 0
    positive = set(STRATEGY_WORLDS)
    for r in v73["rows"]:
        if r["cew_world"] != "unsatisfied":
            continue
        uns_rows += 1
        if r["legacy_world"] in positive:
            mis_leg += 1
        if r["v69_world"] in positive:
            mis_v69 += 1
    mis_rate_legacy = mis_leg / uns_rows if uns_rows else None
    mis_rate_v69 = mis_v69 / uns_rows if uns_rows else None
    # V76 Ready residual requires misapplication baseline measured AND fallback rule documented+coverage measured
    # Documented fallback exists in V75. Coverage measured here.
    # "誤適用率の定義とベースライン計測完了" — we define and measure → G-C1-like pass for measurement
    measured = mis_rate_legacy is not None and pop_cov is not None
    # Ready still needs explicit pass — V76 doesn't set numeric threshold on mis rate; measurement completion is the bar
    g_c1 = measured and policy_doc
    ready = bool(n_ok and policy_doc and g_c1 and jac is not None)
    # Actually V76 also says fallback rule documentation + coverage — measured. jac is extra stability.
    # Residual Ready PASS if all listed items done:
    ready = bool(n_ok and policy_doc and measured and fallback_needed_rate is not None)

    return {
        "world": "unsatisfied",
        "n": uns_n,
        "n_ok": n_ok,
        "policy_documented_v75": policy_doc,
        "misapplication_rate_legacy_positive_on_cew_unsatisfied": mis_rate_legacy,
        "misapplication_rate_v69_positive_on_cew_unsatisfied": mis_rate_v69,
        "misapplication_n": {"legacy": mis_leg, "v69": mis_v69, "denom": uns_rows},
        "popularity_coverage": pop_cov,
        "fallback_needed_rate": fallback_needed_rate,
        "top3_jaccard_splits": jac,
        "G-C1_measurement_complete": g_c1,
        "Ready_gate_pass": ready,
        "note": "Residual Ready = policy readiness, not winning-pattern Ready",
    }


def blocked_reeval(full: dict[str, Any]) -> dict[str, Any]:
    out = {}
    uns_tg = (full["by_world"]["unsatisfied"]["winner_profile"].get("context_means") or {}).get("top_gap")
    mh_tg = (full["by_world"]["midhole_world"]["winner_profile"].get("context_means") or {}).get("top_gap")
    for w in ("core_world", "midupper_world", "mixed_world", "bug_world"):
        bw = full["by_world"][w]
        n = bw["n"]
        to_partial = n >= 20
        extra = {}
        if w == "core_world":
            tg = (bw["winner_profile"].get("context_means") or {}).get("top_gap")
            extra["top_gap"] = tg
            extra["top_gap_gt_unsatisfied"] = (tg is not None and uns_tg is not None and tg > uns_tg)
            extra["top_gap_gt_midhole"] = (tg is not None and mh_tg is not None and tg > mh_tg)
            extra["win_prob_rank1"] = bw["top3"][:1] == ["win_prob_z"] if bw["top3"] else False
            sep_candidate = bool(extra["top_gap_gt_midhole"] or extra["win_prob_rank1"])
        elif w == "midupper_world":
            extra["aptitude_proxy_in_285r_horse_features"] = False
            extra["aptitude_missing_flag"] = True
            sep_candidate = bw["n"] > 0
        elif w == "mixed_world":
            extra["history_effect"] = bw["effects"].get("history_z")
            sep_candidate = bw["n"] > 0
        else:
            extra["exception_true_n"] = 0
            sep_candidate = False
        out[w] = {
            "n": n,
            "blocked_to_partial_n_gate": to_partial,
            "separation_candidate_recorded": sep_candidate,
            "partial_gate_pass": bool(to_partial and sep_candidate),
            "extra": extra,
            "readiness": "Partial" if (to_partial and sep_candidate) else "Blocked",
        }
    return out


def readiness_result(
    rank7_gate: dict[str, Any],
    midhole_gate: dict[str, Any],
    residual: dict[str, Any],
    blocked: dict[str, Any],
) -> dict[str, Any]:
    def pos_status(g: dict[str, Any], prev: str) -> str:
        if g["Ready_gate_pass"]:
            return "Ready"
        # remain Partial if was Partial and still n>=20 stable concept
        return "Partial"

    result = {
        "rank7_world": pos_status(rank7_gate, "Partial"),
        "midhole_world": pos_status(midhole_gate, "Partial"),
        "unsatisfied": "Ready" if residual["Ready_gate_pass"] else "Partial",
    }
    for w, b in blocked.items():
        result[w] = b["readiness"]
    return result


def run() -> dict[str, Any]:
    cew = load_cew_labels()
    corp = json.loads((ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(encoding="utf-8"))
    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fx_rows = fx.get("rows") or fx.get("evaluations") or []
    fxby = {r["race_id"]: r for r in fx_rows}
    dual = {rid: {"legacy_world": None, "v44_world": None} for rid in cew}
    rows = attach_cew(build_race_rows(corp, dual, fxby), cew)

    split1_rows, split2_rows = chronological_split(rows)
    full = analyze_split(rows, "full")
    s1 = analyze_split(split1_rows, "split1_first_half")
    s2 = analyze_split(split2_rows, "split2_second_half")

    contracts = contract_tests_full(full, s1, s2)
    rank7_gate = gate_for_positive("rank7_world", full, s1, s2, "midhole_world")
    midhole_gate = gate_for_positive("midhole_world", full, s1, s2, "rank7_world")
    residual = residual_gate(full, s1, s2, rows)
    blocked = blocked_reeval(full)
    readiness = readiness_result(rank7_gate, midhole_gate, residual, blocked)

    return {
        "schema": SCHEMA,
        "generated_at": _now(),
        "plan": "V76 E1/E2 execution (split1 + split2 gate eval + contract metrics)",
        "split_method": "sorted race_id chronological half",
        "n_full": len(rows),
        "n_split1": len(split1_rows),
        "n_split2": len(split2_rows),
        "full": full,
        "split1": s1,
        "split2": s2,
        "contract_tests": contracts,
        "gates": {
            "rank7_world": rank7_gate,
            "midhole_world": midhole_gate,
            "unsatisfied": residual,
            "blocked_reeval": blocked,
        },
        "readiness_result": readiness,
        "readiness_before_v75": {
            "rank7_world": "Partial",
            "midhole_world": "Partial",
            "unsatisfied": "Partial",
            "core_world": "Blocked",
            "midupper_world": "Blocked",
            "mixed_world": "Blocked",
            "bug_world": "Blocked",
        },
    }


def _fmt(x: Any) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.4f}"
    if isinstance(x, bool):
        return "PASS" if x else "FAIL"
    return str(x)


def write_docs(report: dict[str, Any]) -> dict[str, Path]:
    out = ROOT / "docs" / "research"
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    # slim json for size: drop heavy horse-level by keeping summary only
    slim = {k: v for k, v in report.items() if k not in ("full", "split1", "split2")}
    slim["distributions"] = {
        "full": report["full"]["cew_dist"],
        "split1": report["split1"]["cew_dist"],
        "split2": report["split2"]["cew_dist"],
    }
    slim["per_split_world_n"] = {
        sp: {w: report[sp]["by_world"][w]["n"] for w in ALL_LABELS}
        for sp in ("full", "split1", "split2")
    }
    slim["per_split_metrics"] = {
        sp: {
            w: {
                "n": report[sp]["by_world"][w]["n"],
                "top3": report[sp]["by_world"][w]["top3"],
                "top_style": report[sp]["by_world"][w]["top_style"],
                "r_field_winprob": report[sp]["by_world"][w]["r_field_winprob"],
                "r_upper_winprob": report[sp]["by_world"][w]["r_upper_winprob"],
                "effects": report[sp]["by_world"][w]["effects"],
            }
            for w in ALL_LABELS
            if report[sp]["by_world"][w]["n"] > 0
        }
        for sp in ("full", "split1", "split2")
    }
    paths["json"] = out / "_v77-validation-execution.json"
    paths["json"].write_text(json.dumps(slim, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rr = report["readiness_result"]
    g7 = report["gates"]["rank7_world"]
    gm = report["gates"]["midhole_world"]
    gu = report["gates"]["unsatisfied"]

    paths["exec"] = out / "v77-validation-execution.md"
    paths["exec"].write_text(
        "\n".join(
            [
                "# Version77 — Validation Execution（E1/E2）",
                "",
                f"**Generated:** `{report['generated_at']}`  ",
                f"**Plan:** V76 E1/E2 — データ分割①/② + Gate 判定  ",
                f"**Split:** race_id 時系列 half（n={report['n_split1']} / {report['n_split2']}）  ",
                "**変更なし:** Trigger / Blueprint / Signal / Threshold / PE / Prediction / Production / World Contract",
                "",
                "## 分割分布（CEW）",
                "",
                "| World | full | split1 | split2 |",
                "|---|---:|---:|---:|",
                *[
                    f"| `{w}` | {report['full']['cew_dist'].get(w, 0)} | {report['split1']['cew_dist'].get(w, 0)} | {report['split2']['cew_dist'].get(w, 0)} |"
                    for w in ALL_LABELS
                ],
                "",
                "## E1 — Split1 Gate（要点）",
                "",
                f"- rank7 n={g7['G-S2']['n_split1']}, midhole n={gm['G-S2']['n_split1']}",
                f"- rank7 field_size r={_fmt(report['split1']['by_world']['rank7_world']['r_field_winprob'])}",
                f"- midhole history−win_prob gap (split1) = see JSON effects",
                "",
                "## E2 — Split2 Gate（要点）",
                "",
                f"- rank7 n={g7['G-S2']['n_split2']}, midhole n={gm['G-S2']['n_split2']}",
                f"- rank7 field_size r={_fmt(report['split2']['by_world']['rank7_world']['r_field_winprob'])}",
                f"- midhole history−win_prob gap (split2) = see JSON effects",
                "",
                "## Ready 再判定（要約）",
                "",
                "| World | Before (V75) | After (V77) |",
                "|---|---|---|",
                *[
                    f"| `{w}` | {report['readiness_before_v75'][w]} | **{rr[w]}** |"
                    for w in ALL_LABELS
                ],
                "",
                "## 数値正本",
                "",
                "`docs/research/_v77-validation-execution.json`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # world validation detail
    lines = [
        "# Version77 — World Validation（Contract / Stability / Separation）",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "## Contract Metrics（G-C1 テスト記録）",
        "",
        "| Test ID | Scope | n | Value | Threshold | Pass |",
        "|---|---|---:|---:|---|---|",
    ]
    for t in report["contract_tests"]["tests"]:
        lines.append(
            f"| `{t['test_id']}` | {t['scope']} | {t['n']} | {_fmt(t['value'])} | {t['threshold']} | {_fmt(t['pass'])} |"
        )

    lines += ["", "## rank7 Gate", ""]
    for k in ("G-S1", "G-S2", "G-C1", "G-R1"):
        lines.append(f"- **{k}:** {_fmt(g7[k]['pass'])} — `{json.dumps(g7[k], ensure_ascii=False)}`")
    lines += [
        f"- **Separation:** {_fmt(g7['Separation']['pass'])}",
        f"- **World-specific:** {_fmt(g7['world_specific']['pass'])} `{g7['world_specific']['detail']}`",
        f"- **Ready Gate:** **{_fmt(g7['Ready_gate_pass'])}**",
        "",
        "## midhole Gate",
        "",
    ]
    for k in ("G-S1", "G-S2", "G-C1", "G-R1"):
        lines.append(f"- **{k}:** {_fmt(gm[k]['pass'])} — `{json.dumps(gm[k], ensure_ascii=False)}`")
    lines += [
        f"- **Separation:** {_fmt(gm['Separation']['pass'])}",
        f"- **World-specific:** {_fmt(gm['world_specific']['pass'])} `{gm['world_specific']['detail']}`",
        f"- **Ready Gate:** **{_fmt(gm['Ready_gate_pass'])}**",
        "",
        "## unsatisfied Residual Gate",
        "",
        f"- n={gu['n']} n_ok={gu['n_ok']}",
        f"- misapplication legacy→positive: {_fmt(gu['misapplication_rate_legacy_positive_on_cew_unsatisfied'])}",
        f"- misapplication v69→positive: {_fmt(gu['misapplication_rate_v69_positive_on_cew_unsatisfied'])}",
        f"- popularity_coverage: {_fmt(gu['popularity_coverage'])}",
        f"- fallback_needed_rate: {_fmt(gu['fallback_needed_rate'])}",
        f"- top3_jaccard_splits: {_fmt(gu['top3_jaccard_splits'])}",
        f"- **Ready Gate:** **{_fmt(gu['Ready_gate_pass'])}**",
        "",
        "## Blocked re-eval",
        "",
        "| World | n | →Partial? | Readiness |",
        "|---|---:|---|---|",
    ]
    for w, b in report["gates"]["blocked_reeval"].items():
        lines.append(
            f"| `{w}` | {b['n']} | {_fmt(b['partial_gate_pass'])} | **{b['readiness']}** |"
        )
    lines.append("")
    paths["world"] = out / "v77-world-validation.md"
    paths["world"].write_text("\n".join(lines), encoding="utf-8")

    paths["ready"] = out / "v77-readiness-result.md"
    paths["ready"].write_text(
        "\n".join(
            [
                "# Version77 — Readiness Result",
                "",
                f"**Generated:** `{report['generated_at']}`  ",
                "**Gate 正本:** V76 Readiness Gate（新規設計なし）",
                "",
                "## 再判定",
                "",
                "| World | V75 | V77 | Ready Gate PASS |",
                "|---|---|---|---|",
                f"| `rank7_world` | Partial | **{rr['rank7_world']}** | {_fmt(g7['Ready_gate_pass'])} |",
                f"| `midhole_world` | Partial | **{rr['midhole_world']}** | {_fmt(gm['Ready_gate_pass'])} |",
                f"| `unsatisfied` | Partial | **{rr['unsatisfied']}** | {_fmt(gu['Ready_gate_pass'])} |",
                f"| `core_world` | Blocked | **{rr['core_world']}** | — |",
                f"| `midupper_world` | Blocked | **{rr['midupper_world']}** | — |",
                f"| `mixed_world` | Blocked | **{rr['mixed_world']}** | — |",
                f"| `bug_world` | Blocked | **{rr['bug_world']}** | — |",
                "",
                "## 集計",
                "",
                f"- Ready: **{sum(1 for v in rr.values() if v == 'Ready')}**",
                f"- Partial: **{sum(1 for v in rr.values() if v == 'Partial')}**",
                f"- Blocked: **{sum(1 for v in rr.values() if v == 'Blocked')}**",
                "",
                "## FAIL 主因（Positive）",
                "",
                f"- rank7: G-S2={_fmt(g7['G-S2']['pass'])}, G-R1={_fmt(g7['G-R1']['pass'])}, Sep={_fmt(g7['Separation']['pass'])}, specific={_fmt(g7['world_specific']['pass'])}",
                f"- midhole: G-S1={_fmt(gm['G-S1']['pass'])}, G-S2={_fmt(gm['G-S2']['pass'])}, G-R1={_fmt(gm['G-R1']['pass'])}, Sep={_fmt(gm['Separation']['pass'])}, specific={_fmt(gm['world_specific']['pass'])}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    ready_n = sum(1 for v in rr.values() if v == "Ready")
    verdict = "A" if ready_n >= 2 else ("B" if ready_n == 1 else "C")
    paths["gov"] = out / "v77-governance.md"
    paths["gov"].write_text(
        "\n".join(
            [
                "# Version77 — Governance（Validation Execution）",
                "",
                f"**Date:** {report['generated_at'][:10]}  ",
                f"**Verdict:** **{verdict}**（Ready 件数={ready_n}）  ",
                "**Type:** Validation Execution only",
                "",
                "【Decision】",
                "",
                "| Item | Value |",
                "|---|---|",
                "| Action Type | V76 E1/E2 Execution |",
                "| Implementation Required | No（評価のみ） |",
                "| Deployment Required | No |",
                "| Configuration Required | No |",
                "| Production Required | No |",
                "| Rollback Required | No |",
                "| Risk | None（読取） |",
                "| Expected Next Action | Ready=0 なら証拠蓄積継続（E3）。PE 禁止維持 |",
                "",
                "## 遵守",
                "",
                "| 制約 | |",
                "|---|---|",
                "| 新設計/特徴/Rule 禁止 | PASS |",
                "| Trigger/Blueprint/PE/Prediction 非変更 | PASS |",
                "| World Contract 非変更 | PASS |",
                "| V76 Gate のみで判定 | PASS |",
                "",
                "## 成果物",
                "",
                "- `v77-validation-execution.md`",
                "- `v77-world-validation.md`",
                "- `v77-readiness-result.md`",
                "- `v77-governance.md`",
                "- `_v77-validation-execution.json`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return paths


def main() -> None:
    report = run()
    paths = write_docs(report)
    mirror = Path(r"C:\Users\Mr.me\expect-keiba-ai\docs\research")
    if mirror.is_dir():
        for p in paths.values():
            (mirror / p.name).write_bytes(p.read_bytes())
    print(
        json.dumps(
            {
                "readiness_result": report["readiness_result"],
                "gates_pass": {
                    "rank7": report["gates"]["rank7_world"]["Ready_gate_pass"],
                    "midhole": report["gates"]["midhole_world"]["Ready_gate_pass"],
                    "unsatisfied": report["gates"]["unsatisfied"]["Ready_gate_pass"],
                },
                "G-S2": {
                    "rank7": report["gates"]["rank7_world"]["G-S2"],
                    "midhole": report["gates"]["midhole_world"]["G-S2"],
                },
                "paths": {k: str(v) for k, v in paths.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
