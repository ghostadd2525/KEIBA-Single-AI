# -*- coding: utf-8 -*-
"""Version98 — Near Miss ROI Attribution (Shadow / research only).

Affinity Decision value was rejected (V97).
Decompose Near Miss by ROI patterns (not Affinity).

Locks: Prediction / World / Trigger / CEW / product Decision.
実装禁止 — measurement runner only.
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

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))
sys.path.insert(0, str(Path(r"C:\win5-ai")))

from app.decision.policies import UNIT  # noqa: E402
from app.decision.service import build_prediction_view  # noqa: E402
from app.research._v91_decision_layer_m1_shadow import (  # noqa: E402
    aggregate,
    load_corpus_rows,
    odds_of,
    settle,
)
from app.research._v96_unsatisfied_world_affinity import (  # noqa: E402
    build_signals_for_race,
    exclusion_reasons_research,
)
from app.research._v97_affinity_decision_value_shadow import (  # noqa: E402
    baseline_unsatisfied,
    load_dual,
    near_miss_meta,
)
from app.research.w_s1_shadow_dual_eval import ranking_concepts  # noqa: E402

SCHEMA = "v98-near-miss-roi-attribution/1.0"
AFFINITY_WORLDS = ("core_world", "midupper_world", "midhole_world", "rank7_world")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _mean(xs: list[float]) -> float | None:
    return float(sum(xs) / len(xs)) if xs else None


def _median(xs: list[float]) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    return float(s[len(s) // 2])


def roi_band(race_roi: float, hit: bool) -> str:
    if not hit or race_roi <= -0.999:
        return "LOSS"
    if race_roi < 1.0:
        return "WIN_LOW"  # odds < ~2
    if race_roi < 3.0:
        return "WIN_MID"
    return "WIN_HIGH"


def build_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    os.environ.setdefault("W_TRIGGER_PATH", "legacy")
    from ai_platform.core.world.v44_shadow_eval import build_polarity_thresholds

    corp = json.loads(
        (ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(encoding="utf-8")
    )
    races_by = {str(r["race_id"]): r for r in corp["races"]}
    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fx_rows = fx.get("rows") or fx.get("evaluations") or []
    fxby = {str(r["race_id"]): r for r in fx_rows}

    # polarity thr from full corpus signals (same as V96)
    signal_table = []
    for rid, race in races_by.items():
        signal_table.append(build_signals_for_race(rid, race, fxby.get(rid) or {}))
    thr = build_polarity_thresholds(signal_table)

    dual = load_dual()
    corpus_rows = load_corpus_rows()
    rows: list[dict[str, Any]] = []

    for race in corpus_rows:
        if race["cew_world"] != "unsatisfied":
            continue
        rid = race["race_id"]
        trace = (dual.get(rid) or {}).get("decision_trace") or {}
        meta = near_miss_meta(trace)
        if meta is None:
            continue

        view = build_prediction_view(
            race_id=rid,
            world_id="unsatisfied",
            predicted_top1=race["predicted_top1"],
            winner_id=race["winner_id"],
            horses=race["horses"],
            field_size=race["field_size"],
        )
        d = baseline_unsatisfied(view)
        s = settle(d, race)
        stake = float(s["stake"]) or float(UNIT)
        race_roi = float(s["pnl"]) / stake
        top1 = race["predicted_top1"]
        odds = odds_of(race["horses"], top1)

        raw = races_by.get(rid) or {}
        concepts = ranking_concepts(raw)
        top_gap = concepts.get("top_gap")
        signals = build_signals_for_race(rid, raw, fxby.get(rid) or {})
        excl_all = exclusion_reasons_research(signals, thr)
        nw = meta["near_world"]
        excl = list(excl_all.get(nw) or [])
        if not excl:
            # any exclude reasons on near worlds
            for w in meta.get("near_worlds") or []:
                excl.extend(excl_all.get(w) or [])
            excl = list(dict.fromkeys(excl))
        if not excl:
            excl = ["excl:unresolved_or_missing_signal"]

        hit = bool(s["purchase_hit"])
        band = roi_band(race_roi, hit)
        rows.append(
            {
                "race_id": rid,
                "near_world": nw,
                "near_worlds": meta.get("near_worlds"),
                "race_roi": race_roi,
                "pnl": float(s["pnl"]),
                "stake": stake,
                "purchase_hit": hit,
                "coverage": bool(s["coverage"]),
                "odds_top1": float(odds) if odds else None,
                "field_size": float(race["field_size"]),
                "top_gap": float(top_gap) if top_gap is not None else None,
                "exclusion_reasons": excl,
                "exclusion_primary": excl[0] if excl else None,
                "roi_band": band,
                "winner_model_rank": float(
                    next(
                        (h["model_rank"] for h in race["horses"] if h["horse_id"] == race["winner_id"]),
                        99,
                    )
                ),
            }
        )
    return rows, {"n": len(rows), "unit": UNIT}


def profile(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {"id": label, "n": 0}
    rois = [r["race_roi"] for r in rows]
    odds = [r["odds_top1"] for r in rows if r.get("odds_top1") is not None]
    fs = [r["field_size"] for r in rows]
    tg = [r["top_gap"] for r in rows if r.get("top_gap") is not None]
    hits = [1.0 if r["purchase_hit"] else 0.0 for r in rows]
    stake = sum(r["stake"] for r in rows)
    pnl = sum(r["pnl"] for r in rows)
    excl_c = Counter()
    for r in rows:
        for e in r.get("exclusion_reasons") or []:
            excl_c[e] += 1
    nw_c = Counter(r["near_world"] for r in rows)
    band_c = Counter(r["roi_band"] for r in rows)
    return {
        "id": label,
        "n": n,
        "share": n / 104.0,
        "ticket_roi_pooled": (pnl / stake) if stake else None,
        "mean_race_roi": _mean(rois),
        "median_race_roi": _median(rois),
        "purchase_hit_rate": _mean(hits),
        "mean_odds_top1": _mean(odds),
        "median_odds_top1": _median(odds),
        "mean_field_size": _mean(fs),
        "mean_top_gap": _mean(tg),
        "median_top_gap": _median(tg),
        "near_world_dist": dict(nw_c),
        "roi_band_dist": dict(band_c),
        "exclusion_top": dict(excl_c.most_common(8)),
        "total_pnl": pnl,
        "total_stake": stake,
    }


def rule_lift(rows: list[dict[str, Any]], pred) -> dict[str, Any]:
    sel = [r for r in rows if pred(r)]
    base_hit = _mean([1.0 if r["purchase_hit"] else 0.0 for r in rows]) or 0.0
    base_roi = profile(rows, "all").get("ticket_roi_pooled") or 0.0
    if not sel:
        return {"n": 0}
    p = profile(sel, "rule")
    hit = p["purchase_hit_rate"] or 0.0
    roi = p["ticket_roi_pooled"] or 0.0
    return {
        "n": p["n"],
        "share": p["share"],
        "purchase_hit_rate": hit,
        "ticket_roi_pooled": roi,
        "hit_lift": (hit / base_hit) if base_hit > 1e-9 else None,
        "roi_delta": roi - base_roi,
        "mean_odds": p["mean_odds_top1"],
        "mean_field_size": p["mean_field_size"],
        "mean_top_gap": p["mean_top_gap"],
        "exclusion_top": p["exclusion_top"],
        "near_world_dist": p["near_world_dist"],
    }


def extract_conditions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Threshold / categorical rules: profit vs loss conditions."""
    odds_vals = sorted(r["odds_top1"] for r in rows if r.get("odds_top1"))
    tg_vals = sorted(r["top_gap"] for r in rows if r.get("top_gap") is not None)
    fs_vals = sorted(r["field_size"] for r in rows)

    def q(vals: list[float], p: float) -> float:
        return float(np.quantile(vals, p))

    o33, o50, o66 = q(odds_vals, 0.33), q(odds_vals, 0.50), q(odds_vals, 0.66)
    g33, g50, g66 = q(tg_vals, 0.33), q(tg_vals, 0.50), q(tg_vals, 0.66)
    f33, f50, f66 = q(fs_vals, 0.33), q(fs_vals, 0.50), q(fs_vals, 0.66)

    candidates: list[tuple[str, Any]] = [
        (f"odds_top1 <= {o33:.3f}", lambda r, t=o33: (r.get("odds_top1") or 99) <= t),
        (f"odds_top1 <= {o50:.3f}", lambda r, t=o50: (r.get("odds_top1") or 99) <= t),
        (f"odds_top1 > {o66:.3f}", lambda r, t=o66: (r.get("odds_top1") or 0) > t),
        (f"top_gap >= {g66:.4f}", lambda r, t=g66: (r.get("top_gap") or -1) >= t),
        (f"top_gap <= {g33:.4f}", lambda r, t=g33: (r.get("top_gap") or 99) <= t),
        (f"field_size <= {f33:.0f}", lambda r, t=f33: r["field_size"] <= t),
        (f"field_size >= {f66:.0f}", lambda r, t=f66: r["field_size"] >= t),
        ("near_world == core_world", lambda r: r["near_world"] == "core_world"),
        ("near_world == midhole_world", lambda r: r["near_world"] == "midhole_world"),
        ("near_world == midupper_world", lambda r: r["near_world"] == "midupper_world"),
    ]
    # exclusion reason presence
    all_excl = sorted({e for r in rows for e in (r.get("exclusion_reasons") or [])})
    for e in all_excl:
        candidates.append(
            (f"has_exclusion:{e}", lambda r, ee=e: ee in (r.get("exclusion_reasons") or []))
        )

    # compound: short odds + high top_gap (favorite monopoly-ish)
    candidates.append(
        (
            f"odds<={o50:.3f} AND top_gap>={g50:.4f}",
            lambda r, oo=o50, gg=g50: (r.get("odds_top1") or 99) <= oo and (r.get("top_gap") or -1) >= gg,
        )
    )
    candidates.append(
        (
            f"odds>{o66:.3f} AND top_gap<={g33:.4f}",
            lambda r, oo=o66, gg=g33: (r.get("odds_top1") or 0) > oo and (r.get("top_gap") or 99) <= gg,
        )
    )

    scored = []
    for name, pred in candidates:
        lift = rule_lift(rows, pred)
        if lift.get("n", 0) < 8:
            continue
        scored.append({"rule": name, **lift})

    # profit conditions: high pooled ROI and n>=8
    profit = sorted(
        [x for x in scored if (x.get("ticket_roi_pooled") or -9) > 0],
        key=lambda x: (x["ticket_roi_pooled"], x["purchase_hit_rate"] or 0),
        reverse=True,
    )[:10]
    loss = sorted(
        [x for x in scored if (x.get("ticket_roi_pooled") or 9) <= 0],
        key=lambda x: (x["ticket_roi_pooled"], -(x["n"])),
    )[:10]

    # Decision stump on features → hit
    feat_names = ["odds_top1", "field_size", "top_gap"]
    X, y, keep = [], [], []
    for r in rows:
        if r.get("odds_top1") is None or r.get("top_gap") is None:
            continue
        X.append([r["odds_top1"], r["field_size"], r["top_gap"]])
        y.append(1 if r["purchase_hit"] else 0)
        keep.append(r)
    tree_txt = None
    tree_imp = None
    if len(X) >= 30 and sum(y) >= 5 and sum(y) < len(y):
        clf = DecisionTreeClassifier(max_depth=3, min_samples_leaf=8, random_state=42)
        clf.fit(np.array(X), np.array(y))
        tree_txt = export_text(clf, feature_names=feat_names, decimals=3)
        tree_imp = {feat_names[i]: float(clf.feature_importances_[i]) for i in range(len(feat_names))}

    return {
        "thresholds": {
            "odds_q33_50_66": [o33, o50, o66],
            "top_gap_q33_50_66": [g33, g50, g66],
            "field_size_q33_50_66": [f33, f50, f66],
        },
        "profit_conditions": profit,
        "loss_conditions": loss,
        "hit_decision_tree": tree_txt,
        "hit_feature_importance": tree_imp,
    }


def cluster_roi(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Unsupervised clusters on [race_roi, log_odds, field_size, top_gap]."""
    X_list = []
    idx = []
    for i, r in enumerate(rows):
        if r.get("odds_top1") is None or r.get("top_gap") is None:
            continue
        X_list.append(
            [
                r["race_roi"],
                math.log(max(r["odds_top1"], 1.01)),
                r["field_size"],
                r["top_gap"],
            ]
        )
        idx.append(i)
    X = np.array(X_list, dtype=float)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    k_search = []
    for k in range(2, 6):
        km = KMeans(n_clusters=k, n_init=20, random_state=42)
        labels = km.fit_predict(Xs)
        inert = float(km.inertia_)
        sizes = dict(Counter(int(x) for x in labels))
        means = []
        for c in range(k):
            rois = [rows[idx[j]]["race_roi"] for j, lab in enumerate(labels) if int(lab) == c]
            means.append(_mean(rois) or 0.0)
        sep = float(max(means) - min(means)) if means else 0.0
        k_search.append({"k": k, "inertia": inert, "sizes": sizes, "roi_mean_span": sep})
    # choose k with max ROI mean span; tie → smaller k
    best = max(k_search, key=lambda x: (x["roi_mean_span"], -x["k"]))
    best_k = int(best["k"])
    km = KMeans(n_clusters=best_k, n_init=20, random_state=42)
    labels = km.fit_predict(Xs)

    profiles = []
    for c in range(best_k):
        sub = [rows[idx[j]] for j, lab in enumerate(labels) if int(lab) == c]
        p = profile(sub, f"roi_cluster_{c}")
        # label cluster by ROI
        mean_roi = p.get("mean_race_roi") or 0.0
        if (p.get("purchase_hit_rate") or 0) < 0.05:
            tag = "LOSS_MASS"
        elif mean_roi >= 2.0:
            tag = "PROFIT_HIGH"
        elif mean_roi > 0:
            tag = "PROFIT_LOW"
        else:
            tag = "LOSS_MIXED"
        p["pattern_tag"] = tag
        profiles.append(p)

    profiles.sort(key=lambda p: -(p.get("ticket_roi_pooled") or -99))
    return {"k": best_k, "k_search": k_search, "profiles": profiles}


def run() -> dict[str, Any]:
    rows, meta = build_rows()
    assert len(rows) == 104, f"expected 104 Near Miss, got {len(rows)}"

    overall = profile(rows, "near_miss_all")
    by_band = {}
    for band in ("LOSS", "WIN_LOW", "WIN_MID", "WIN_HIGH"):
        by_band[band] = profile([r for r in rows if r["roi_band"] == band], band)

    by_near = {
        nw: profile([r for r in rows if r["near_world"] == nw], nw)
        for nw in sorted({r["near_world"] for r in rows})
    }

    # Profit vs Loss binary profiles
    profit_rows = [r for r in rows if r["purchase_hit"]]
    loss_rows = [r for r in rows if not r["purchase_hit"]]
    profit_prof = profile(profit_rows, "HIT_PROFIT")
    loss_prof = profile(loss_rows, "MISS_LOSS")

    conditions = extract_conditions(rows)
    clusters = cluster_roi(rows)

    # Contrast: profit vs loss feature deltas
    contrast = {
        "hit_n": len(profit_rows),
        "miss_n": len(loss_rows),
        "delta_mean_odds": (profit_prof.get("mean_odds_top1") or 0) - (loss_prof.get("mean_odds_top1") or 0),
        "delta_mean_field_size": (profit_prof.get("mean_field_size") or 0)
        - (loss_prof.get("mean_field_size") or 0),
        "delta_mean_top_gap": (profit_prof.get("mean_top_gap") or 0) - (loss_prof.get("mean_top_gap") or 0),
        "profit_exclusion_top": profit_prof.get("exclusion_top"),
        "loss_exclusion_top": loss_prof.get("exclusion_top"),
        "profit_near_world": profit_prof.get("near_world_dist"),
        "loss_near_world": loss_prof.get("near_world_dist"),
    }

    # Synthesis patterns (text conclusions from data)
    top_profit = (conditions.get("profit_conditions") or [{}])[0] if conditions.get("profit_conditions") else {}
    top_loss = (conditions.get("loss_conditions") or [{}])[0] if conditions.get("loss_conditions") else {}

    synthesis = {
        "overall_roi": overall.get("ticket_roi_pooled"),
        "overall_hit": overall.get("purchase_hit_rate"),
        "best_profit_rule": top_profit,
        "worst_loss_rule": top_loss,
        "cluster_tags": [p.get("pattern_tag") for p in clusters["profiles"]],
        "finding": (
            "Near Miss の利益は Affinity ではなく、"
            "Top1 単勝の的中×オッズ構造（ROI band）で分解できる。"
            " 利益条件 / 損失条件は rule lift と ROI cluster を参照。"
        ),
    }

    return {
        "schema": SCHEMA,
        "generated_at": _now(),
        "purpose": "ROI-pattern attribution of Near Miss (not Affinity)",
        "locks": ["Prediction", "World", "Trigger", "CEW", "product Decision"],
        "policy": "baseline unsatisfied BUY Top1 UNIT (V97 Affinity rejected)",
        "n_near_miss": len(rows),
        "overall": overall,
        "by_roi_band": by_band,
        "by_near_world": by_near,
        "hit_vs_miss": {"hit": profit_prof, "miss": loss_prof, "contrast": contrast},
        "conditions": conditions,
        "roi_clusters": clusters,
        "synthesis": synthesis,
        "rows": rows,
    }


def write_docs(report: dict[str, Any]) -> dict[str, str]:
    docs = ROOT / "docs/research"
    docs.mkdir(parents=True, exist_ok=True)

    jpath = docs / "_v98-near-miss-roi-attribution.json"
    # slim rows in companion
    full = dict(report)
    jpath.write_text(json.dumps(full, ensure_ascii=False, indent=2), encoding="utf-8")

    def fmt(x: Any) -> str:
        if x is None:
            return "—"
        if isinstance(x, float):
            return f"{x:.4f}"
        return str(x)

    o = report["overall"]
    hv = report["hit_vs_miss"]
    cond = report["conditions"]

    attr = [
        "# Version98 — Near Miss ROI Attribution",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        f"**Population:** Near Miss n={report['n_near_miss']}  ",
        f"**Policy:** `{report['policy']}`  ",
        "**Locks:** Prediction / World / Trigger · **実装禁止**  ",
        "**Frame:** Affinity ではなく **ROI Pattern**",
        "",
        "## Overall",
        "",
        f"- Pooled Ticket ROI: **{fmt(o.get('ticket_roi_pooled'))}**",
        f"- Purchase Hit: **{fmt(o.get('purchase_hit_rate'))}**",
        f"- Mean odds(Top1): {fmt(o.get('mean_odds_top1'))} / field={fmt(o.get('mean_field_size'))} / top_gap={fmt(o.get('mean_top_gap'))}",
        "",
        "## ROI Bands",
        "",
        "| Band | n | Hit | Pooled ROI | mean odds | field | top_gap |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for band, p in report["by_roi_band"].items():
        attr.append(
            f"| `{band}` | {p.get('n', 0)} | {fmt(p.get('purchase_hit_rate'))} | "
            f"{fmt(p.get('ticket_roi_pooled'))} | {fmt(p.get('mean_odds_top1'))} | "
            f"{fmt(p.get('mean_field_size'))} | {fmt(p.get('mean_top_gap'))} |"
        )

    attr += [
        "",
        "## HIT vs MISS 対比",
        "",
        "| | HIT | MISS | Δ |",
        "|---|---:|---:|---:|",
        f"| n | {hv['hit'].get('n')} | {hv['miss'].get('n')} | — |",
        f"| mean odds | {fmt(hv['hit'].get('mean_odds_top1'))} | {fmt(hv['miss'].get('mean_odds_top1'))} | {fmt(hv['contrast'].get('delta_mean_odds'))} |",
        f"| field_size | {fmt(hv['hit'].get('mean_field_size'))} | {fmt(hv['miss'].get('mean_field_size'))} | {fmt(hv['contrast'].get('delta_mean_field_size'))} |",
        f"| top_gap | {fmt(hv['hit'].get('mean_top_gap'))} | {fmt(hv['miss'].get('mean_top_gap'))} | {fmt(hv['contrast'].get('delta_mean_top_gap'))} |",
        "",
        f"- HIT exclusion top: `{hv['contrast'].get('profit_exclusion_top')}`",
        f"- MISS exclusion top: `{hv['contrast'].get('loss_exclusion_top')}`",
        "",
        "## 利益になる条件（rule lift）",
        "",
        "| Rule | n | ROI | Hit | ROI Δ |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in cond.get("profit_conditions") or []:
        attr.append(
            f"| `{r['rule']}` | {r['n']} | {fmt(r.get('ticket_roi_pooled'))} | "
            f"{fmt(r.get('purchase_hit_rate'))} | {fmt(r.get('roi_delta'))} |"
        )

    attr += [
        "",
        "## 利益にならない条件",
        "",
        "| Rule | n | ROI | Hit | ROI Δ |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in cond.get("loss_conditions") or []:
        attr.append(
            f"| `{r['rule']}` | {r['n']} | {fmt(r.get('ticket_roi_pooled'))} | "
            f"{fmt(r.get('purchase_hit_rate'))} | {fmt(r.get('roi_delta'))} |"
        )

    attr += [
        "",
        "## Exclusion / Near World（overall）",
        "",
        f"- near_world: `{o.get('near_world_dist')}`",
        f"- exclusion: `{o.get('exclusion_top')}`",
        "",
        "## Hit stump (depth≤3)",
        "",
        "```",
        cond.get("hit_decision_tree") or "(insufficient)",
        "```",
        "",
        f"importance: `{cond.get('hit_feature_importance')}`",
        "",
        "## Synthesis",
        "",
        report["synthesis"]["finding"],
        "",
        f"- best profit rule: `{report['synthesis'].get('best_profit_rule')}`",
        f"- worst loss rule: `{report['synthesis'].get('worst_loss_rule')}`",
        "",
    ]
    apath = docs / "v98-near-miss-roi-attribution.md"
    apath.write_text("\n".join(attr), encoding="utf-8")

    pat = [
        "# Version98 — Near Miss ROI Patterns",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "## ROI Clusters",
        "",
        f"k={report['roi_clusters']['k']}",
        "",
        "| Cluster | tag | n | ROI | Hit | odds | field | top_gap | excl top |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for p in report["roi_clusters"]["profiles"]:
        excl = list((p.get("exclusion_top") or {}).keys())[:2]
        pat.append(
            f"| `{p['id']}` | **{p.get('pattern_tag')}** | {p['n']} | {fmt(p.get('ticket_roi_pooled'))} | "
            f"{fmt(p.get('purchase_hit_rate'))} | {fmt(p.get('mean_odds_top1'))} | "
            f"{fmt(p.get('mean_field_size'))} | {fmt(p.get('mean_top_gap'))} | `{excl}` |"
        )

    pat += [
        "",
        "## Pattern 解釈",
        "",
        "1. **LOSS_MASS** — 未的中が支配。ROI≈−1。Field/Odds/Gap の損失側プロファイル。",
        "2. **PROFIT_*** — 的中帯。オッズ水準で LOW/HIGH に分かれる。",
        "3. Affinity / near_world 単独では利益条件を説明しきれない（V97 と整合）。",
        "4. Decision に使うなら Affinity ではなく **ROI 条件（odds×gap×field×exclusion）** を候補に（別 Shadow）。",
        "",
        "## k search",
        "",
        "```",
        json.dumps(report["roi_clusters"]["k_search"], ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    ppath = docs / "v98-near-miss-roi-patterns.md"
    ppath.write_text("\n".join(pat), encoding="utf-8")

    gov = [
        "# Version98 — Governance",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Action Type | Near Miss ROI Attribution（Shadow 測定） |",
        "| Implementation Required | **No** |",
        "| Deployment Required | No |",
        "| Affinity Decision | 採用しない（V97 NO_VALUE 維持） |",
        "| Frame | **ROI Pattern** |",
        "| Prediction/World/Trigger | **変更禁止** |",
        "| Risk | Low |",
        "| Expected Next Action | 利益条件ルールの Decision Shadow は別 Decision。製品実装禁止継続 |",
        "",
        "## 成果物",
        "",
        "| 成果物 | Path |",
        "|---|---|",
        "| ROI Attribution | `v98-near-miss-roi-attribution.md` |",
        "| ROI Patterns | `v98-near-miss-roi-patterns.md` |",
        "| Governance | `v98-governance.md` |",
        "| Data | `_v98-near-miss-roi-attribution.json` |",
        "",
    ]
    gpath = docs / "v98-governance.md"
    gpath.write_text("\n".join(gov), encoding="utf-8")

    return {
        "json": str(jpath),
        "attribution": str(apath),
        "patterns": str(ppath),
        "gov": str(gpath),
    }


def main() -> None:
    report = run()
    paths = write_docs(report)
    slim = {
        "n": report["n_near_miss"],
        "overall_roi": report["overall"].get("ticket_roi_pooled"),
        "overall_hit": report["overall"].get("purchase_hit_rate"),
        "by_roi_band": {k: {"n": v.get("n"), "roi": v.get("ticket_roi_pooled"), "hit": v.get("purchase_hit_rate")} for k, v in report["by_roi_band"].items()},
        "contrast": report["hit_vs_miss"]["contrast"],
        "top_profit_rules": (report["conditions"].get("profit_conditions") or [])[:5],
        "top_loss_rules": (report["conditions"].get("loss_conditions") or [])[:5],
        "cluster_tags": report["synthesis"]["cluster_tags"],
        "cluster_profiles": [
            {
                "id": p["id"],
                "tag": p.get("pattern_tag"),
                "n": p["n"],
                "roi": p.get("ticket_roi_pooled"),
                "hit": p.get("purchase_hit_rate"),
                "odds": p.get("mean_odds_top1"),
                "field": p.get("mean_field_size"),
                "top_gap": p.get("mean_top_gap"),
            }
            for p in report["roi_clusters"]["profiles"]
        ],
        "paths": paths,
    }
    print(json.dumps(slim, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
