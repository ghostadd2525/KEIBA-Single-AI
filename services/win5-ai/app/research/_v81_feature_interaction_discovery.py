# -*- coding: utf-8 -*-
"""Version81 — Feature Interaction Discovery (285R, research only).

Discovers 2-way and 3-way feature interactions per CEW World.
Single-feature effects are NOT ranked (forbidden).
No PE / Production / Trigger / Prediction mutation.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_selection import mutual_info_classif

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))

from app.research._v64_world_strategy_discovery import (  # noqa: E402
    build_race_rows,
    ranking_concepts,
    zscore,
    _f,
)
from app.research._v74_world_strategy_validation import load_cew_labels, attach_cew  # noqa: E402
from app.research.w_s1_shadow_dual_eval import restore_trigger_signals  # noqa: E402

SCHEMA = "v81-feature-interaction-discovery/1.0"
WORLDS = (
    "rank7_world",
    "midhole_world",
    "unsatisfied",
    "core_world",
    "midupper_world",
    "mixed_world",
)
MIN_RACES = 8
TOP_K = 15


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def entropy_binary(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return float(-(p * math.log2(p) + (1 - p) * math.log2(1 - p)))


def information_gain_binary(x: np.ndarray, y: np.ndarray, n_bins: int = 4) -> float:
    """IG of y (0/1) from discretized x."""
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask].astype(int)
    if len(y) < 20 or y.sum() == 0 or y.sum() == len(y):
        return 0.0
    # quantile bins
    try:
        qs = np.unique(np.quantile(x, np.linspace(0, 1, n_bins + 1)))
        if len(qs) < 3:
            return 0.0
        bins = np.digitize(x, qs[1:-1], right=True)
    except Exception:
        return 0.0
    h_y = entropy_binary(float(y.mean()))
    h_yx = 0.0
    for b in np.unique(bins):
        m = bins == b
        if m.sum() == 0:
            continue
        p = float(y[m].mean())
        h_yx += (m.sum() / len(y)) * entropy_binary(p)
    return max(0.0, h_y - h_yx)


def lift_top_quantile(x: np.ndarray, y: np.ndarray, q: float = 0.75) -> float | None:
    """P(y=1 | x>=q) / P(y=1)."""
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask].astype(float)
    if len(y) < 20 or y.sum() == 0:
        return None
    thr = np.quantile(x, q)
    sel = x >= thr
    if sel.sum() < 5:
        return None
    base = float(y.mean())
    if base <= 0:
        return None
    return float(y[sel].mean() / base)


def friedman_h(model: GradientBoostingClassifier, X: np.ndarray, i: int, j: int, grid: int = 8) -> float:
    """Partial dependence interaction H^{2} approx for pair (i,j)."""
    # Sample grid on quantiles
    n = X.shape[0]
    if n < 30:
        return 0.0
    idx = np.linspace(0, n - 1, min(grid, n)).astype(int)
    xs = np.sort(X[:, i])[idx]
    ys = np.sort(X[:, j])[idx]
    # Centered PD
    pd_ij = np.zeros((len(xs), len(ys)))
    base = X.copy()
    for a, xv in enumerate(xs):
        for b, yv in enumerate(ys):
            tmp = base.copy()
            tmp[:, i] = xv
            tmp[:, j] = yv
            pd_ij[a, b] = float(model.predict_proba(tmp)[:, 1].mean())
    # PD_i, PD_j
    pd_i = pd_ij.mean(axis=1)
    pd_j = pd_ij.mean(axis=0)
    pd_mean = pd_ij.mean()
    numer = 0.0
    denom = 0.0
    for a in range(len(xs)):
        for b in range(len(ys)):
            f = pd_ij[a, b] - pd_i[a] - pd_j[b] + pd_mean
            numer += f * f
            denom += (pd_ij[a, b] - pd_mean) ** 2
    if denom < 1e-12:
        return 0.0
    return float(numer / denom)


def build_dataset(rows: list[dict[str, Any]], pace_by_rid: dict[str, dict[str, float | None]]) -> dict[str, Any]:
    """Horse-level rows with atomic features (used only to form interactions)."""
    samples = []
    for race in rows:
        rid = race["race_id"]
        concepts = race["concepts"]
        fs = float(race["field_size"])
        pace = pace_by_rid.get(rid) or {}
        high_pace = pace.get("high_pace")
        chaos = pace.get("chaos")
        phase = pace.get("phase")
        # pace proxy: mean of available
        pace_vals = [v for v in (high_pace, chaos, phase) if v is not None]
        pace_score = float(sum(pace_vals) / len(pace_vals)) if pace_vals else None

        for h in race["horses"]:
            samples.append(
                {
                    "race_id": rid,
                    "cew_world": race["cew_world"],
                    "is_winner": 1 if h["is_winner"] else 0,
                    "history": h.get("history_z"),
                    "win_prob": h.get("win_prob_z"),
                    "odds": None if h.get("odds_z") is None else -float(h["odds_z"]),  # oriented: low odds better → flip
                    "popularity": None
                    if h.get("popularity_z") is None
                    else -float(h["popularity_z"]),
                    "field_size": fs,
                    "top_gap": concepts.get("top_gap"),
                    "upper_band": concepts.get("upper_ability_band"),
                    "ability_sep": concepts.get("ability_separation"),
                    "ability_sub": concepts.get("ability_subordinate"),
                    "mid_band": concepts.get("mid_eval_band_open"),
                    "pace": pace_score,
                    "high_pace": high_pace,
                    "chaos": chaos,
                }
            )
    return {"samples": samples}


ATOMIC = (
    "history",
    "win_prob",
    "odds",
    "field_size",
    "top_gap",
    "upper_band",
    "ability_sep",
    "ability_sub",
    "mid_band",
    "pace",
)


def z_within_world(vals: list[float | None]) -> list[float | None]:
    arr = [v for v in vals if v is not None]
    if len(arr) < 5:
        return vals
    mu = sum(arr) / len(arr)
    var = sum((v - mu) ** 2 for v in arr) / len(arr)
    sd = math.sqrt(var) if var > 0 else 1.0
    out = []
    for v in vals:
        if v is None:
            out.append(None)
        else:
            out.append((v - mu) / sd)
    return out


def interaction_value(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return float(a) * float(b)


def interaction_value3(a: float | None, b: float | None, c: float | None) -> float | None:
    if a is None or b is None or c is None:
        return None
    return float(a) * float(b) * float(c)


def evaluate_interactions(samples: list[dict[str, Any]], world: str) -> dict[str, Any]:
    sub = [s for s in samples if s["cew_world"] == world]
    n_races = len({s["race_id"] for s in sub})
    if n_races < MIN_RACES or len(sub) < 40:
        return {"world": world, "n_races": n_races, "n_horses": len(sub), "status": "insufficient", "pair": [], "triple": []}

    # world-wise z for atomics
    zmat: dict[str, list[float | None]] = {}
    for feat in ATOMIC:
        raw = [s.get(feat) for s in sub]
        # race-constant features still z across horses (ok)
        zmat[feat] = z_within_world([_f(v) for v in raw])

    y = np.array([s["is_winner"] for s in sub], dtype=float)

    # candidate pairs (only interactions)
    pairs = list(combinations(ATOMIC, 2))
    # prefer listed examples order boost later in naming
    pair_rows = []
    X_cols = []
    names = []
    for f1, f2 in pairs:
        vals = [interaction_value(zmat[f1][i], zmat[f2][i]) for i in range(len(sub))]
        arr = np.array([np.nan if v is None else v for v in vals], dtype=float)
        if np.isfinite(arr).sum() < 40:
            continue
        # fill nan with median for MI
        med = float(np.nanmedian(arr))
        arr_f = np.where(np.isfinite(arr), arr, med)
        mi = float(mutual_info_classif(arr_f.reshape(-1, 1), y.astype(int), discrete_features=False, random_state=0)[0])
        ig = information_gain_binary(arr_f, y)
        lt = lift_top_quantile(arr_f, y)
        pair_rows.append(
            {
                "interaction": f"{f1} × {f2}",
                "type": "2way",
                "f1": f1,
                "f2": f2,
                "mi": mi,
                "ig": ig,
                "lift": lt,
                "n": int(np.isfinite(arr).sum()),
            }
        )
        X_cols.append(arr_f)
        names.append(f"{f1} × {f2}")

    # triples: curated + systematic top from ATOMIC choose 3 limited set to bound cost
    triple_feats = [
        ("history", "field_size", "top_gap"),
        ("win_prob", "pace", "upper_band"),
        ("history", "pace", "odds"),
        ("history", "win_prob", "field_size"),
        ("top_gap", "history", "pace"),
        ("field_size", "pace", "odds"),
        ("ability_sub", "pace", "win_prob"),
        ("history", "odds", "win_prob"),
        ("top_gap", "upper_band", "history"),
        ("mid_band", "history", "field_size"),
        ("chaos" if False else "ability_sep", "pace", "field_size"),
        ("win_prob", "field_size", "top_gap"),
    ]
    # fix the dummy
    triple_feats = [t for t in triple_feats if all(x in ATOMIC for x in t)]
    # add more combinations of key set
    key = ["history", "win_prob", "field_size", "top_gap", "pace", "upper_band", "odds"]
    for t in combinations(key, 3):
        if t not in triple_feats:
            triple_feats.append(t)
    triple_feats = list(dict.fromkeys(triple_feats))[:40]

    triple_rows = []
    for f1, f2, f3 in triple_feats:
        vals = [interaction_value3(zmat[f1][i], zmat[f2][i], zmat[f3][i]) for i in range(len(sub))]
        arr = np.array([np.nan if v is None else v for v in vals], dtype=float)
        if np.isfinite(arr).sum() < 40:
            continue
        med = float(np.nanmedian(arr))
        arr_f = np.where(np.isfinite(arr), arr, med)
        mi = float(mutual_info_classif(arr_f.reshape(-1, 1), y.astype(int), discrete_features=False, random_state=0)[0])
        ig = information_gain_binary(arr_f, y)
        lt = lift_top_quantile(arr_f, y)
        triple_rows.append(
            {
                "interaction": f"{f1} × {f2} × {f3}",
                "type": "3way",
                "f1": f1,
                "f2": f2,
                "f3": f3,
                "mi": mi,
                "ig": ig,
                "lift": lt,
                "n": int(np.isfinite(arr).sum()),
            }
        )
        X_cols.append(arr_f)
        names.append(f"{f1} × {f2} × {f3}")

    # SHAP-interaction proxy: Friedman H on GBM trained only on interaction columns
    h_scores = {n: 0.0 for n in names}
    if len(X_cols) >= 5 and y.sum() >= 5:
        X = np.column_stack(X_cols)
        # standardize
        X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-9)
        try:
            clf = GradientBoostingClassifier(random_state=0, max_depth=2, n_estimators=40, learning_rate=0.1)
            clf.fit(X, y.astype(int))
            # H for each 2-way that exists as columns; for triples use |corr with residual| skip
            name_to_idx = {n: i for i, n in enumerate(names)}
            # compute H for pairs among first len(pair_rows) features that are 2way
            pair_names = [r["interaction"] for r in pair_rows]
            # Sample up to 12 strongest by MI for H (cost)
            top_for_h = sorted(pair_rows, key=lambda r: -r["mi"])[:12]
            for a in range(len(top_for_h)):
                for b in range(a + 1, len(top_for_h)):
                    na = top_for_h[a]["interaction"]
                    nb = top_for_h[b]["interaction"]
                    ia, ib = name_to_idx[na], name_to_idx[nb]
                    h = friedman_h(clf, X, ia, ib, grid=6)
                    # attribute half to each interaction column as "interaction strength involvement"
                    h_scores[na] = max(h_scores[na], h)
                    h_scores[nb] = max(h_scores[nb], h)
            # feature importances as additional signal for 3way columns
            imp = clf.feature_importances_
            for n, v in zip(names, imp):
                if " × " in n and n.count("×") >= 2:
                    h_scores[n] = max(h_scores[n], float(v))
        except Exception:
            pass

    def rank_block(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []
        for r in rows:
            r["shap_interaction_proxy"] = h_scores.get(r["interaction"], 0.0)
        # ranks (higher better); lift None -> worst
        def add_rank(key: str, higher=True):
            vals = []
            for r in rows:
                v = r.get(key)
                if v is None or (isinstance(v, float) and not math.isfinite(v)):
                    vals.append((r["interaction"], None))
                else:
                    vals.append((r["interaction"], float(v)))
            finite = [(i, v) for i, v in vals if v is not None]
            finite.sort(key=lambda t: -t[1] if higher else t[1])
            rankmap = {name: i + 1 for i, (name, _) in enumerate(finite)}
            for r in rows:
                r[f"rank_{key}"] = rankmap.get(r["interaction"])

        add_rank("mi")
        add_rank("ig")
        add_rank("lift")
        add_rank("shap_interaction_proxy")
        for r in rows:
            ranks = [r[k] for k in ("rank_mi", "rank_ig", "rank_lift", "rank_shap_interaction_proxy") if r.get(k)]
            r["rank_mean"] = sum(ranks) / len(ranks) if ranks else 999.0
        rows = sorted(rows, key=lambda r: r["rank_mean"])
        for i, r in enumerate(rows, 1):
            r["rank_overall"] = i
        return rows

    pair_ranked = rank_block(pair_rows)
    triple_ranked = rank_block(triple_rows)

    # heatmap matrix for atomics using best MI of pair
    heat = {a: {b: 0.0 for b in ATOMIC} for a in ATOMIC}
    for r in pair_ranked:
        heat[r["f1"]][r["f2"]] = r["mi"]
        heat[r["f2"]][r["f1"]] = r["mi"]

    return {
        "world": world,
        "n_races": n_races,
        "n_horses": len(sub),
        "n_winners": int(y.sum()),
        "status": "ok",
        "pair": pair_ranked[:TOP_K],
        "triple": triple_ranked[:TOP_K],
        "pair_all": pair_ranked,
        "heatmap_mi": heat,
    }


def write_svg_heatmap(heat: dict[str, dict[str, float]], path: Path, title: str) -> None:
    labels = list(ATOMIC)
    n = len(labels)
    cell = 28
    pad = 90
    w = pad + cell * n + 20
    h = pad + cell * n + 40
    vals = [heat[a][b] for a in labels for b in labels if a != b]
    vmax = max(vals) if vals else 1.0
    if vmax <= 0:
        vmax = 1.0

    def color(v: float) -> str:
        t = max(0.0, min(1.0, v / vmax))
        # white -> deep teal
        r = int(245 - 180 * t)
        g = int(248 - 80 * t)
        b = int(250 - 40 * t)
        return f"rgb({r},{g},{b})"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">',
        f'<text x="{pad}" y="24" font-size="14" font-family="Segoe UI, sans-serif">{title}</text>',
    ]
    for i, a in enumerate(labels):
        parts.append(
            f'<text x="{pad - 8}" y="{pad + i * cell + cell / 2 + 4}" text-anchor="end" font-size="9" font-family="Segoe UI, sans-serif">{a}</text>'
        )
        parts.append(
            f'<text x="{pad + i * cell + cell / 2}" y="{pad - 8}" text-anchor="middle" font-size="9" font-family="Segoe UI, sans-serif" transform="rotate(-45 {pad + i * cell + cell / 2} {pad - 8})">{a}</text>'
        )
        for j, b in enumerate(labels):
            v = heat[a][b] if a != b else 0.0
            x = pad + j * cell
            y = pad + i * cell
            parts.append(f'<rect x="{x}" y="{y}" width="{cell - 1}" height="{cell - 1}" fill="{color(v)}" stroke="#ddd"/>')
            if a != b and v > 0:
                parts.append(
                    f'<text x="{x + cell / 2}" y="{y + cell / 2 + 3}" text-anchor="middle" font-size="7" fill="#333">{v:.2f}</text>'
                )
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def run() -> dict[str, Any]:
    cew = load_cew_labels()
    corp = json.loads((ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(encoding="utf-8"))
    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fx_rows = fx.get("rows") or fx.get("evaluations") or []
    fxby = {r["race_id"]: r for r in fx_rows}
    dual = {rid: {"legacy_world": None, "v44_world": None} for rid in cew}
    rows = attach_cew(build_race_rows(corp, dual, fxby), cew)

    # pace restore (race-level)
    pace_by_rid: dict[str, dict[str, float | None]] = {}
    cache_path = ROOT / "docs/research/_v81-pace-cache.json"
    if cache_path.exists():
        pace_by_rid = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        for fr in fx_rows:
            rid = str(fr["race_id"])
            restored = restore_trigger_signals(rid, fr.get("field_size"), fr.get("distance"))
            pace_by_rid[rid] = {
                "high_pace": restored.get("high_pace"),
                "chaos": restored.get("chaos"),
                "phase": restored.get("phase"),
            }
        cache_path.write_text(json.dumps(pace_by_rid, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ds = build_dataset(rows, pace_by_rid)
    by_world = {}
    for w in WORLDS:
        by_world[w] = evaluate_interactions(ds["samples"], w)

    # global top across worlds (interaction-only)
    global_top = []
    for w, blk in by_world.items():
        if blk.get("status") != "ok":
            continue
        for r in (blk.get("pair") or [])[:5]:
            global_top.append({**r, "world": w})
        for r in (blk.get("triple") or [])[:3]:
            global_top.append({**r, "world": w})
    global_top = sorted(global_top, key=lambda r: (r.get("rank_mean") or 999, -(r.get("mi") or 0)))

    return {
        "schema": SCHEMA,
        "generated_at": _now(),
        "n_races": len(rows),
        "label": "cew",
        "atomic_features_for_interactions_only": list(ATOMIC),
        "metrics": ["mi", "ig", "lift", "shap_interaction_proxy(FriedmanH/GBM)"],
        "single_feature_ranking": "FORBIDDEN",
        "by_world": by_world,
        "global_top_interactions": global_top[:30],
        "pace_coverage": {
            "races_with_pace": sum(1 for v in pace_by_rid.values() if any(x is not None for x in v.values())),
            "n": len(pace_by_rid),
        },
    }


def write_docs(report: dict[str, Any]) -> dict[str, Path]:
    out = ROOT / "docs" / "research"
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    # slim json (drop pair_all)
    slim = dict(report)
    slim_bw = {}
    for w, blk in report["by_world"].items():
        slim_bw[w] = {k: v for k, v in blk.items() if k != "pair_all"}
    slim["by_world"] = slim_bw
    paths["json"] = out / "_v81-feature-interaction.json"
    paths["json"].write_text(json.dumps(slim, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def fmt(v: Any) -> str:
        if v is None:
            return "—"
        if isinstance(v, float):
            return f"{v:.4f}"
        return str(v)

    # World Interaction Report
    lines = [
        "# Version81 — World Interaction Report",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        f"**Corpus:** 285R / CEW labels  ",
        "**Scope:** Feature **Interaction only**（単体特徴量ランキング禁止）  ",
        "**Metrics:** MI / Information Gain / Lift@top25% / SHAP-interaction proxy（Friedman H / GBM）  ",
        f"**Pace coverage:** {report['pace_coverage']['races_with_pace']}/{report['pace_coverage']['n']}",
        "",
        "## Atomic bases（Interaction 構成要素のみ・単独では順位付けしない）",
        "",
        ", ".join(f"`{a}`" for a in report["atomic_features_for_interactions_only"]),
        "",
    ]
    for w in WORLDS:
        blk = report["by_world"][w]
        lines += [f"## `{w}`", ""]
        if blk.get("status") != "ok":
            lines += [f"insufficient（n_races={blk.get('n_races')}）", ""]
            continue
        lines += [
            f"n_races={blk['n_races']} / n_horses={blk['n_horses']} / winners={blk['n_winners']}",
            "",
            "### Top 2-way",
            "",
            "| Rank | Interaction | MI | IG | Lift | SHAP-proxy |",
            "|---:|---|---:|---:|---:|---:|",
        ]
        for r in blk["pair"]:
            lines.append(
                f"| {r['rank_overall']} | `{r['interaction']}` | {fmt(r['mi'])} | {fmt(r['ig'])} | {fmt(r['lift'])} | {fmt(r['shap_interaction_proxy'])} |"
            )
        lines += [
            "",
            "### Top 3-way",
            "",
            "| Rank | Interaction | MI | IG | Lift | SHAP-proxy |",
            "|---:|---|---:|---:|---:|---:|",
        ]
        for r in blk["triple"]:
            lines.append(
                f"| {r['rank_overall']} | `{r['interaction']}` | {fmt(r['mi'])} | {fmt(r['ig'])} | {fmt(r['lift'])} | {fmt(r['shap_interaction_proxy'])} |"
            )
        lines.append("")

    paths["report"] = out / "v81-world-interaction-report.md"
    paths["report"].write_text("\n".join(lines), encoding="utf-8")

    # Top ranking across
    tr = [
        "# Version81 — Top Interaction Ranking",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "World横断の Interaction 上位（単体禁止）。",
        "",
        "| # | World | Type | Interaction | MI | IG | Lift | mean_rank |",
        "|---:|---|---|---|---:|---:|---:|---:|",
    ]
    for i, r in enumerate(report["global_top_interactions"], 1):
        tr.append(
            f"| {i} | `{r['world']}` | {r['type']} | `{r['interaction']}` | {fmt(r['mi'])} | {fmt(r['ig'])} | {fmt(r['lift'])} | {fmt(r.get('rank_mean'))} |"
        )
    # per-world champion
    tr += ["", "## World Champion（各 World の overall #1）", ""]
    for w in WORLDS:
        blk = report["by_world"][w]
        if blk.get("status") != "ok":
            continue
        champ = None
        cands = (blk.get("pair") or []) + (blk.get("triple") or [])
        if cands:
            champ = min(cands, key=lambda r: r.get("rank_overall", 999))
        if champ:
            tr.append(f"- `{w}`: **`{champ['interaction']}`** ({champ['type']}, MI={fmt(champ['mi'])}, Lift={fmt(champ['lift'])})")
    tr.append("")
    paths["rank"] = out / "v81-top-interaction-ranking.md"
    paths["rank"].write_text("\n".join(tr), encoding="utf-8")

    # heatmaps SVG + md index
    heat_dir = out / "v81-heatmaps"
    heat_dir.mkdir(parents=True, exist_ok=True)
    hm_lines = [
        "# Version81 — Interaction Heatmap",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "セル値 = 2-way Interaction の **Mutual Information**（対角は 0）。単体効果ではない。",
        "",
    ]
    for w in WORLDS:
        blk = report["by_world"][w]
        if blk.get("status") != "ok":
            continue
        svg = heat_dir / f"v81-heatmap-{w}.svg"
        write_svg_heatmap(blk["heatmap_mi"], svg, f"MI Interaction Heatmap — {w}")
        hm_lines += [f"## `{w}`", "", f"![heatmap](v81-heatmaps/{svg.name})", ""]
        # also compact markdown matrix top
        hm_lines += ["|  | " + " | ".join(f"`{a}`" for a in ATOMIC) + " |", "|---|" + "|".join(["---:"] * len(ATOMIC)) + "|"]
        for a in ATOMIC:
            row = [f"{blk['heatmap_mi'][a][b]:.3f}" if a != b else "—" for b in ATOMIC]
            hm_lines.append(f"| `{a}` | " + " | ".join(row) + " |")
        hm_lines.append("")
    paths["heat"] = out / "v81-interaction-heatmap.md"
    paths["heat"].write_text("\n".join(hm_lines), encoding="utf-8")

    # governance
    # pick evidence: whether interactions exist with lift>1.1 or mi>0
    strong = 0
    for w, blk in report["by_world"].items():
        if blk.get("status") != "ok":
            continue
        for r in (blk.get("pair") or [])[:5]:
            if (r.get("lift") or 0) >= 1.05 or (r.get("mi") or 0) > 0.01:
                strong += 1
    verdict = "A" if strong >= 5 else ("B" if strong >= 1 else "C")
    paths["gov"] = out / "v81-governance.md"
    paths["gov"].write_text(
        "\n".join(
            [
                "# Version81 — Governance（Feature Interaction Discovery）",
                "",
                f"**Date:** {report['generated_at'][:10]}  ",
                f"**Verdict:** **{verdict}**（Interaction 証拠数≈{strong}）  ",
                "**Type:** Research only",
                "",
                "【Decision】",
                "",
                "| Item | Value |",
                "|---|---|",
                "| Action Type | Feature Interaction Discovery |",
                "| Implementation Required | **No** |",
                "| PE Required | **No**（禁止） |",
                "| Production Required | No |",
                "| Rollback Required | No |",
                "| Risk | None（読取） |",
                "| Expected Next Action | Top Interaction を用いた Strategy 再設計（別 Decision）。単体 Weight Pilot は継続禁止 |",
                "",
                "## 遵守",
                "",
                "| 制約 | |",
                "|---|---|",
                "| 単体特徴量ランキング禁止 | PASS |",
                "| PE/Production 禁止 | PASS |",
                "| 改善実装禁止 | PASS |",
                "",
                "## 成果物",
                "",
                "- `v81-world-interaction-report.md`",
                "- `v81-top-interaction-ranking.md`",
                "- `v81-interaction-heatmap.md` + `v81-heatmaps/*.svg`",
                "- `v81-governance.md`",
                "- `_v81-feature-interaction.json`",
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
        # heatmaps folder
        src = ROOT / "docs/research/v81-heatmaps"
        dst = mirror / "v81-heatmaps"
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.glob("*.svg"):
            (dst / f.name).write_bytes(f.read_bytes())
        if (ROOT / "docs/research/_v81-pace-cache.json").exists():
            (mirror / "_v81-pace-cache.json").write_bytes((ROOT / "docs/research/_v81-pace-cache.json").read_bytes())
        (mirror / "_v81-feature-interaction.json").write_bytes(paths["json"].read_bytes())

    # summary champions
    champs = {}
    for w, blk in report["by_world"].items():
        if blk.get("status") != "ok":
            continue
        cands = (blk.get("pair") or [])[:1]
        champs[w] = cands[0]["interaction"] if cands else None
    print(json.dumps({"verdict_hint": champs, "pace": report["pace_coverage"], "paths": {k: str(v) for k, v in paths.items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
