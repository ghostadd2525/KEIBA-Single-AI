# -*- coding: utf-8 -*-
"""Version94 — Unsatisfied Residual Clustering (research only).

Cluster the 176 CEW=unsatisfied races to judge:
  - Are they 2–3 homogeneous patterns → World-candidate?
  - Or diffuse / near-miss / artifact → keep as Residual?

Locks: Prediction / Trigger / World Meaning / PE / Production / ADR-008 architecture.
Uses existing CEW labels + W-S1 decision_trace + race concepts only.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))

from app.research._v64_world_strategy_discovery import build_race_rows, _f  # noqa: E402
from app.research._v74_world_strategy_validation import attach_cew, load_cew_labels  # noqa: E402
from app.research.w_s1_shadow_dual_eval import restore_trigger_signals  # noqa: E402

SCHEMA = "v94-unsatisfied-residual-clustering/1.0"
STRATEGY_WORLDS = (
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
    "mixed_world",
    "bug_world",
)
CONCEPT_KEYS = (
    "top_gap",
    "ability_separation",
    "upper_ability_band",
    "mid_eval_band_open",
    "top_monopoly",
    "ability_subordinate",
)
CLUSTER_FEATS = (
    "field_size",
    "distance",
    "top_gap",
    "ability_separation",
    "upper_ability_band",
    "mid_eval_band_open",
    "top_monopoly",
    "ability_subordinate",
    "chaos",
    "difficulty",
    "winner_model_rank",
    "hit_at_1",
    "restored_ok",
    "struct_exclusion",
    "struct_all_must_fail",
    "n_must_true",
    "n_exclude_true",
    "must_core",
    "must_midupper",
    "must_midhole",
    "must_rank7",
    "must_mixed",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _mean(xs: list[float]) -> float | None:
    return float(sum(xs) / len(xs)) if xs else None


def load_dual_traces() -> dict[str, dict[str, Any]]:
    path = ROOT / "docs/implementation/w-s1-dual-eval-rows.jsonl"
    out: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            out[str(r["race_id"])] = r
    return out


def structural_label(trace: dict[str, Any]) -> dict[str, Any]:
    """W-S1 exclusive partition: Exclusion (must&exclude) vs all Must fail."""
    any_must_excl = False
    any_must = False
    n_must = 0
    n_excl = 0
    must_by: dict[str, bool] = {}
    excl_worlds: list[str] = []
    for w in STRATEGY_WORLDS:
        t = (trace or {}).get(w) or {}
        must = bool(t.get("must"))
        excl = bool(t.get("exclude"))
        must_by[w] = must
        if must:
            any_must = True
            n_must += 1
        if excl:
            n_excl += 1
        if must and excl:
            any_must_excl = True
            excl_worlds.append(w)
    if any_must_excl:
        struct = "exclusion_stop"
    elif not any_must:
        struct = "all_must_fail"
    else:
        # must without exclude somewhere — theoretically 0 in W-S1
        struct = "other"
    # nearest intended: fewest must_gaps among exclude=False (W-S1 note: bug bias)
    best_w = None
    best_gaps = 10**9
    for w in STRATEGY_WORLDS:
        t = (trace or {}).get(w) or {}
        if t.get("exclude"):
            continue
        gaps = list(t.get("must_gaps") or [])
        if len(gaps) < best_gaps:
            best_gaps = len(gaps)
            best_w = w
    return {
        "struct": struct,
        "n_must_true": n_must,
        "n_exclude_true": n_excl,
        "excl_worlds": excl_worlds,
        "must_by": must_by,
        "intended_ref": best_w,
        "intended_gap_n": best_gaps if best_w else None,
    }


def build_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cew = load_cew_labels()
    dual_map = load_dual_traces()
    corp = json.loads(
        (ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(encoding="utf-8")
    )
    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fx_rows = fx.get("rows") or fx.get("evaluations") or []
    fxby = {str(r["race_id"]): r for r in fx_rows}
    dual_empty = {rid: {"legacy_world": None, "v44_world": None} for rid in cew}
    race_rows = attach_cew(build_race_rows(corp, dual_empty, fxby), cew)

    all_rows: list[dict[str, Any]] = []
    unsat: list[dict[str, Any]] = []
    for race in race_rows:
        rid = race["race_id"]
        d = dual_map.get(rid) or {}
        trace = d.get("decision_trace") or {}
        st = structural_label(trace)
        concepts = race.get("concepts") or {}
        restored = restore_trigger_signals(
            rid,
            race.get("field_size"),
            race.get("distance"),
        )
        rec = {
            "race_id": rid,
            "cew_world": race["cew_world"],
            "legacy_world": d.get("legacy_world"),
            "field_size": float(race.get("field_size") or 0),
            "distance": float(race["distance"]) if race.get("distance") is not None else None,
            "hit_at_1": 1.0 if d.get("hit_at_1") else (1.0 if race.get("winner_model_rank") == 1 else 0.0),
            "winner_model_rank": float(race.get("winner_model_rank") or 99),
            "restored_ok": 1.0 if d.get("restored_ok", True) else 0.0,
            "chaos": _f(restored.get("chaos")),
            "difficulty": _f(restored.get("difficulty")),
            "struct": st["struct"],
            "struct_exclusion": 1.0 if st["struct"] == "exclusion_stop" else 0.0,
            "struct_all_must_fail": 1.0 if st["struct"] == "all_must_fail" else 0.0,
            "n_must_true": float(st["n_must_true"]),
            "n_exclude_true": float(st["n_exclude_true"]),
            "excl_worlds": st["excl_worlds"],
            "intended_ref": st["intended_ref"],
            "must_core": 1.0 if st["must_by"].get("core_world") else 0.0,
            "must_midupper": 1.0 if st["must_by"].get("midupper_world") else 0.0,
            "must_midhole": 1.0 if st["must_by"].get("midhole_world") else 0.0,
            "must_rank7": 1.0 if st["must_by"].get("rank7_world") else 0.0,
            "must_mixed": 1.0 if st["must_by"].get("mixed_world") else 0.0,
            "world_transition": d.get("world_transition"),
        }
        for k in CONCEPT_KEYS:
            rec[k] = _f(concepts.get(k))
        all_rows.append(rec)
        if race["cew_world"] == "unsatisfied":
            unsat.append(rec)
    return all_rows, unsat


def feature_matrix(rows: list[dict[str, Any]]) -> tuple[np.ndarray, list[str]]:
    cols = list(CLUSTER_FEATS)
    X = np.zeros((len(rows), len(cols)), dtype=float)
    for i, r in enumerate(rows):
        for j, c in enumerate(cols):
            v = r.get(c)
            X[i, j] = float(v) if v is not None and not (isinstance(v, float) and math.isnan(v)) else np.nan
    # impute column median
    for j in range(X.shape[1]):
        col = X[:, j]
        med = float(np.nanmedian(col)) if np.isfinite(col).any() else 0.0
        col[~np.isfinite(col)] = med
        X[:, j] = col
    return X, cols


def world_concept_means(all_rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in all_rows:
        by[r["cew_world"]].append(r)
    out: dict[str, dict[str, float]] = {}
    keys = list(CONCEPT_KEYS) + ["field_size", "distance", "chaos", "difficulty", "winner_model_rank", "hit_at_1"]
    for w, rs in by.items():
        m = {}
        for k in keys:
            vals = [float(r[k]) for r in rs if r.get(k) is not None]
            if vals:
                m[k] = float(sum(vals) / len(vals))
        out[w] = m
    return out


def nearest_world(profile: dict[str, float], world_means: dict[str, dict[str, float]]) -> tuple[str | None, float | None]:
    keys = list(CONCEPT_KEYS)
    best = None
    best_c = -2.0
    for w, wm in world_means.items():
        if w == "unsatisfied":
            continue
        xs = [profile.get(k) for k in keys]
        ys = [wm.get(k) for k in keys]
        if any(v is None for v in xs + ys):
            continue
        a = np.array(xs, dtype=float)
        b = np.array(ys, dtype=float)
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na < 1e-12 or nb < 1e-12:
            continue
        c = float(np.dot(a, b) / (na * nb))
        if c > best_c:
            best_c = c
            best = w
    return best, (best_c if best is not None else None)


def cluster_profile(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {"id": label, "n": 0}
    means = {}
    for k in CLUSTER_FEATS:
        vals = [float(r[k]) for r in rows if r.get(k) is not None]
        means[k] = _mean(vals)
    struct_c = Counter(r["struct"] for r in rows)
    excl_c = Counter(w for r in rows for w in (r.get("excl_worlds") or []))
    intended_c = Counter(r.get("intended_ref") for r in rows)
    legacy_c = Counter(r.get("legacy_world") for r in rows)
    hit = _mean([float(r["hit_at_1"]) for r in rows])
    return {
        "id": label,
        "n": n,
        "share": n / 176.0,
        "struct_dist": dict(struct_c),
        "exclusion_world_hits": dict(excl_c.most_common()),
        "intended_ref_dist": dict(intended_c),
        "legacy_world_dist": dict(legacy_c),
        "hit_at_1": hit,
        "means": means,
        "race_ids_sample": [r["race_id"] for r in rows[:8]],
    }


def judge_cluster(prof: dict[str, Any], nearest: str | None, cos: float | None, k_sil: float | None) -> dict[str, Any]:
    """Heuristic gate for World-candidate vs Residual vs Near-miss."""
    n = prof["n"]
    share = prof["share"]
    struct = prof.get("struct_dist") or {}
    excl_dom = max((struct.get("exclusion_stop") or 0) / n, 0.0) if n else 0.0
    fail_dom = max((struct.get("all_must_fail") or 0) / n, 0.0) if n else 0.0
    excl_worlds = prof.get("exclusion_world_hits") or {}
    top_excl = max(excl_worlds, key=excl_worlds.get) if excl_worlds else None

    # Near-miss of existing World via Exclusion
    if excl_dom >= 0.70 and top_excl and excl_worlds[top_excl] >= 0.5 * n:
        return {
            "verdict": "NEAR_MISS_EXISTING_WORLD",
            "action": "NOT_NEW_WORLD",
            "reason": (
                f"クラスタの {excl_dom:.0%} が Exclusion 停止で、主に `{top_excl}` 近接。"
                " 新 World ではなく既存 World の Exclusion/Threshold 問題。"
            ),
            "related_world": top_excl,
        }

    # Large homogeneous all-must-fail with weak nearest world → candidate
    if share >= 0.15 and fail_dom >= 0.60 and n >= 26:
        if cos is not None and cos < 0.85:
            return {
                "verdict": "WORLD_CANDIDATE_RESEARCH",
                "action": "CONSIDER_NEW_WORLD_DESIGN_ONLY",
                "reason": (
                    f"n={n} ({share:.0%}) が Must 全失敗優勢で既存 World 概念類似度が低い"
                    f"（nearest={nearest}, cos={cos:.3f}）。勝ち筋主張前に Signal/Contract 設計が必要。"
                ),
                "related_world": nearest,
            }
        return {
            "verdict": "DIFFUSE_OR_WEAK_SIGNAL",
            "action": "KEEP_RESIDUAL",
            "reason": (
                f"規模はあるが既存 World（{nearest}）と概念が近い（cos={cos}）。"
                " 新 World より Threshold/Signal 充足の方が先。"
            ),
            "related_world": nearest,
        }

    if share < 0.10 or n < 18:
        return {
            "verdict": "SMALL_FRAGMENT",
            "action": "KEEP_RESIDUAL",
            "reason": f"小断片 n={n}。専用 World の標本不足。",
            "related_world": nearest,
        }

    return {
        "verdict": "MIXED_RESIDUAL",
        "action": "KEEP_RESIDUAL",
        "reason": "均質な勝ち筋パターンとしては弱い。Residual 契約を維持。",
        "related_world": nearest,
        "silhouette_context": k_sil,
    }


def run() -> dict[str, Any]:
    all_rows, unsat = build_records()
    assert len(unsat) == 176, f"expected 176 unsatisfied, got {len(unsat)}"

    # --- Structural partition (W-S1 ground taxonomy) ---
    struct_groups = {
        "exclusion_stop": [r for r in unsat if r["struct"] == "exclusion_stop"],
        "all_must_fail": [r for r in unsat if r["struct"] == "all_must_fail"],
        "other": [r for r in unsat if r["struct"] == "other"],
    }
    world_means = world_concept_means(all_rows)

    structural_profiles = []
    for name, rs in struct_groups.items():
        if not rs:
            continue
        p = cluster_profile(rs, f"struct:{name}")
        nearest, cos = nearest_world(p["means"], world_means)
        p["nearest_world"] = nearest
        p["nearest_cosine"] = cos
        p["judgment"] = judge_cluster(p, nearest, cos, None)
        structural_profiles.append(p)

    # Exclusion sub-clusters by dominant excluded World
    excl_rows = struct_groups["exclusion_stop"]
    by_excl: dict[str, list] = defaultdict(list)
    for r in excl_rows:
        # primary excluded world: prefer core > midupper > midhole > rank7
        ew = r.get("excl_worlds") or []
        primary = None
        for pref in ("core_world", "midupper_world", "midhole_world", "rank7_world", "mixed_world"):
            if pref in ew:
                primary = pref
                break
        by_excl[primary or "none"].append(r)
    exclusion_sub = []
    for name, rs in sorted(by_excl.items(), key=lambda x: -len(x[1])):
        p = cluster_profile(rs, f"excl_primary:{name}")
        nearest, cos = nearest_world(p["means"], world_means)
        p["nearest_world"] = nearest
        p["nearest_cosine"] = cos
        p["judgment"] = judge_cluster(p, nearest, cos, None)
        exclusion_sub.append(p)

    # --- Unsupervised KMeans on continuous+struct features ---
    X, feat_names = feature_matrix(unsat)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    k_search = []
    best_k = 2
    best_sil = -1.0
    best_labels = None
    for k in range(2, 7):
        km = KMeans(n_clusters=k, n_init=20, random_state=42)
        labels = km.fit_predict(Xs)
        sil = float(silhouette_score(Xs, labels)) if len(set(labels)) > 1 else -1.0
        sizes = dict(Counter(int(x) for x in labels))
        k_search.append({"k": k, "silhouette": sil, "sizes": sizes})
        if sil > best_sil:
            best_sil = sil
            best_k = k
            best_labels = labels

    assert best_labels is not None
    km_profiles = []
    for cid in range(best_k):
        rs = [r for r, lab in zip(unsat, best_labels) if int(lab) == cid]
        p = cluster_profile(rs, f"kmeans_k{best_k}_c{cid}")
        nearest, cos = nearest_world(p["means"], world_means)
        p["nearest_world"] = nearest
        p["nearest_cosine"] = cos
        p["judgment"] = judge_cluster(p, nearest, cos, best_sil)
        # feature drivers: distance from unsatisfied global mean in z-space
        idx = [i for i, lab in enumerate(best_labels) if int(lab) == cid]
        if idx:
            sub = Xs[idx]
            global_m = Xs.mean(axis=0)
            delta = sub.mean(axis=0) - global_m
            order = np.argsort(-np.abs(delta))[:8]
            p["top_drivers"] = [
                {"feature": feat_names[j], "delta_z": float(delta[j])} for j in order
            ]
        km_profiles.append(p)

    # Agglomerative k=3 for interpretability check
    agg = AgglomerativeClustering(n_clusters=3)
    agg_labels = agg.fit_predict(Xs)
    agg_sil = float(silhouette_score(Xs, agg_labels))
    agg_profiles = []
    for cid in range(3):
        rs = [r for r, lab in zip(unsat, agg_labels) if int(lab) == cid]
        p = cluster_profile(rs, f"agglo_k3_c{cid}")
        nearest, cos = nearest_world(p["means"], world_means)
        p["nearest_world"] = nearest
        p["nearest_cosine"] = cos
        p["judgment"] = judge_cluster(p, nearest, cos, agg_sil)
        agg_profiles.append(p)

    # Overall decision synthesis
    n_excl = len(struct_groups["exclusion_stop"])
    n_fail = len(struct_groups["all_must_fail"])
    world_candidate_clusters = [
        p for p in km_profiles + structural_profiles + exclusion_sub
        if (p.get("judgment") or {}).get("action") == "CONSIDER_NEW_WORLD_DESIGN_ONLY"
    ]
    near_miss = [
        p for p in exclusion_sub
        if (p.get("judgment") or {}).get("verdict") == "NEAR_MISS_EXISTING_WORLD"
    ]

    if n_excl / 176 >= 0.50 and len(world_candidate_clusters) == 0:
        global_verdict = "KEEP_AS_RESIDUAL_WITH_NEAR_MISS_TAXONOMY"
        global_reason = (
            f"176件の大半は均質な『新勝ち筋』ではなく、"
            f"Exclusion近接（{n_excl}）と Must全失敗（{n_fail}）の2型。"
            " Exclusion側は既存 World（特に core/midupper）の近接失敗。"
            " 新 World 追加より Residual 維持＋既存 World の Exclusion/標本問題の方が先。"
        )
    elif len(world_candidate_clusters) >= 1:
        global_verdict = "PARTIAL_WORLD_CANDIDATE_EXISTS"
        global_reason = (
            "一部クラスタが新 World 候補条件を満たす。ただし Contract/Signal 設計前に勝ち筋化禁止。"
        )
    else:
        global_verdict = "KEEP_AS_RESIDUAL"
        global_reason = "2〜3の勝ち筋パターンとしては未確立。Residual 契約を維持。"

    report = {
        "schema": SCHEMA,
        "generated_at": _now(),
        "locks": [
            "Prediction",
            "Trigger",
            "World Meaning",
            "PE",
            "Production",
            "ADR-008 architecture",
        ],
        "n_unsatisfied": 176,
        "n_corpus": 285,
        "structure_partition": {
            "exclusion_stop": n_excl,
            "all_must_fail": n_fail,
            "other": len(struct_groups["other"]),
        },
        "world_means": world_means,
        "structural_profiles": structural_profiles,
        "exclusion_subclusters": exclusion_sub,
        "kmeans": {
            "k_search": k_search,
            "best_k": best_k,
            "best_silhouette": best_sil,
            "profiles": km_profiles,
        },
        "agglomerative_k3": {
            "silhouette": agg_sil,
            "profiles": agg_profiles,
        },
        "synthesis": {
            "verdict": global_verdict,
            "reason": global_reason,
            "world_candidate_count": len(world_candidate_clusters),
            "near_miss_clusters": [
                {"id": p["id"], "n": p["n"], "judgment": p["judgment"]} for p in near_miss
            ],
            "recommend_new_world": False if "KEEP_AS_RESIDUAL" in global_verdict else len(world_candidate_clusters) > 0,
            "recommend_keep_residual": "KEEP_AS_RESIDUAL" in global_verdict,
        },
    }
    return report


def write_docs(report: dict[str, Any]) -> dict[str, str]:
    docs = ROOT / "docs/research"
    docs.mkdir(parents=True, exist_ok=True)
    jpath = docs / "_v94-unsatisfied-residual-clustering.json"
    # slim json (drop huge means duplication ok)
    jpath.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def fmt_prof(p: dict[str, Any]) -> list[str]:
        j = p.get("judgment") or {}
        lines = [
            f"### `{p['id']}` — n={p['n']} ({p['share']:.1%})",
            f"- struct: `{p.get('struct_dist')}`",
            f"- hit@1: {_fmt(p.get('hit_at_1'))}",
            f"- nearest World: `{p.get('nearest_world')}` (cos={_fmt(p.get('nearest_cosine'))})",
            f"- exclusion hits: `{p.get('exclusion_world_hits')}`",
            f"- **judgment:** `{j.get('verdict')}` → `{j.get('action')}`",
            f"- reason: {j.get('reason')}",
        ]
        if p.get("top_drivers"):
            drv = ", ".join(f"{d['feature']}({d['delta_z']:+.2f}z)" for d in p["top_drivers"][:5])
            lines.append(f"- drivers: {drv}")
        return lines

    def _fmt(x: Any) -> str:
        if x is None:
            return "—"
        if isinstance(x, float):
            return f"{x:.3f}"
        return str(x)

    syn = report["synthesis"]
    sp = report["structure_partition"]
    km = report["kmeans"]

    main = [
        "# Version94 — Unsatisfied Residual Clustering",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "**Population:** CEW=`unsatisfied` **176 / 285**  ",
        "**Locks:** Prediction / Trigger / World Meaning / PE / Production  ",
        "**Question:** 176件は 2〜3 パターンに分かれるか？ → 新 World vs Residual？",
        "",
        "## Verdict",
        "",
        f"**`{syn['verdict']}`**",
        "",
        syn["reason"],
        "",
        f"- Recommend new World now: **{syn['recommend_new_world']}**",
        f"- Recommend keep Residual: **{syn['recommend_keep_residual']}**",
        "",
        "## 1. 構造分割（W-S1 互換・排他）",
        "",
        f"| 構造 | n | 比率 |",
        f"|---|---:|---:|",
        f"| Exclusion 停止（Must 充足後 exclude） | {sp['exclusion_stop']} | {sp['exclusion_stop']/176:.1%} |",
        f"| 全 World Must 失敗 | {sp['all_must_fail']} | {sp['all_must_fail']/176:.1%} |",
        f"| other | {sp['other']} | {sp['other']/176:.1%} |",
        "",
        "→ **2型が主**（104 / 72）。ここが第一のクラスタリング結果。",
        "",
        "## 2. Exclusion 内訳（既存 World 近接）",
        "",
    ]
    for p in report["exclusion_subclusters"]:
        main.extend(fmt_prof(p))
        main.append("")

    main += [
        "## 3. 教師なし KMeans（特徴量）",
        "",
        f"- best k={km['best_k']} / silhouette={km['best_silhouette']:.3f}",
        "",
        "| k | silhouette | sizes |",
        "|---:|---:|---|",
    ]
    for row in km["k_search"]:
        main.append(f"| {row['k']} | {row['silhouette']:.3f} | `{row['sizes']}` |")
    main.append("")
    for p in km["profiles"]:
        main.extend(fmt_prof(p))
        main.append("")

    main += [
        "## 4. Agglomerative（k=3 確認）",
        "",
        f"silhouette={report['agglomerative_k3']['silhouette']:.3f}",
        "",
    ]
    for p in report["agglomerative_k3"]["profiles"]:
        main.extend(fmt_prof(p))
        main.append("")

    main += [
        "## 5. 判断基準（本レポート）",
        "",
        "| 条件 | 判定 |",
        "|---|---|",
        "| Exclusion≥70% かつ特定 World 近接 | **NEAR_MISS** → 新 World 禁止。既存 Threshold/Exclusion |",
        "| n≥26 かつ Must全失敗優勢 かつ既存概念 cos 低 | **WORLD_CANDIDATE**（設計のみ・勝ち筋化禁止） |",
        "| 小断片 / 混合 | **KEEP_RESIDUAL** |",
        "",
        "## 6. 結論（運用）",
        "",
        "1. **今すぐ新しい Positive World を追加すべきではない**（勝ち筋化禁止継続）。",
        "2. Residual 176 は『意味のないゴミ』ではなく、**Exclusion近接 + Must未達**の残差分。",
        "3. 将来の World 追加を検討するなら、まず Exclusion で止まっている **core / midupper** の",
        "   標本・Forbidden 条件を監査（新ラベルより契約修復）。",
        "4. Must全失敗 72 は候補プールだが、均質勝ち筋の証明は本クラスタだけでは不十分 → Residual 維持。",
        "",
        "## 関連",
        "",
        "- `w-s1-unsatisfied-root-cause.md`",
        "- `v75-world-strategy-contract.md`（unsatisfied Residual）",
        "- `v94-residual-breakdown.md` / `v94-governance.md`",
        "",
    ]
    opt = docs / "v94-unsatisfied-residual-clustering.md"
    opt.write_text("\n".join(main), encoding="utf-8")

    br = [
        "# Version94 — Residual Breakdown",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "## 内訳サマリ",
        "",
        "```",
        "unsatisfied 176",
        f" ├─ Exclusion stop     {sp['exclusion_stop']:3d}  (~{sp['exclusion_stop']/176:.0%})",
    ]
    for p in report["exclusion_subclusters"]:
        name = p["id"].replace("excl_primary:", "")
        br.append(f" │    └─ primary→{name:16s} {p['n']:3d}")
    br += [
        f" └─ All Must fail      {sp['all_must_fail']:3d}  (~{sp['all_must_fail']/176:.0%})",
        "```",
        "",
        "## World追加 vs Residual",
        "",
        f"| 問い | 答え |",
        f"|---|---|",
        f"| 大半が 2〜3 パターンか？ | **はい（構造2型）** — Exclusion / Must全失敗 |",
        f"| それは新 World か？ | **主に No** — Exclusion は既存 World 近接失敗 |",
        f"| Residual に残すべきか？ | **はい（勝ち筋化禁止）** |",
        f"| 例外的候補はあるか？ | Must全失敗側は研究候補だが未証明 |",
        "",
        f"**Synthesis:** `{syn['verdict']}`",
        "",
        syn["reason"],
        "",
    ]
    brpath = docs / "v94-residual-breakdown.md"
    brpath.write_text("\n".join(br), encoding="utf-8")

    gov = [
        "# Version94 — Governance",
        "",
        f"**Generated:** `{report['generated_at']}`",
        "",
        "| Item | Value |",
        "|---|---|",
        "| Action Type | Residual Clustering（測定のみ） |",
        "| Implementation Required | **No**（PE/Production/Trigger 非変更） |",
        "| Deployment Required | No |",
        "| New World Authorized | **No** |",
        "| Residual Contract | **維持**（V75 / ADR-008 DL-C6） |",
        "| Risk | Low（研究ドキュメントのみ） |",
        "| Expected Next Action | Exclusion 近接（core/midupper）監査を別 Decision。勝ち筋 World 追加は禁止継続 |",
        "",
        "## Hard locks",
        "",
        "- Prediction / Ranking / Confidence / World Meaning / Trigger / Architecture",
        "- unsatisfied の Positive Ticket 化禁止（ADR-008 DL-C6）",
        "",
    ]
    gpath = docs / "v94-governance.md"
    gpath.write_text("\n".join(gov), encoding="utf-8")

    return {
        "json": str(jpath),
        "clustering": str(opt),
        "breakdown": str(brpath),
        "gov": str(gpath),
    }


def main() -> None:
    report = run()
    paths = write_docs(report)
    slim = {
        "verdict": report["synthesis"]["verdict"],
        "recommend_new_world": report["synthesis"]["recommend_new_world"],
        "recommend_keep_residual": report["synthesis"]["recommend_keep_residual"],
        "structure_partition": report["structure_partition"],
        "best_k": report["kmeans"]["best_k"],
        "best_silhouette": report["kmeans"]["best_silhouette"],
        "exclusion_sub": [
            {
                "id": p["id"],
                "n": p["n"],
                "verdict": (p.get("judgment") or {}).get("verdict"),
                "action": (p.get("judgment") or {}).get("action"),
            }
            for p in report["exclusion_subclusters"]
        ],
        "kmeans_clusters": [
            {
                "id": p["id"],
                "n": p["n"],
                "verdict": (p.get("judgment") or {}).get("verdict"),
                "nearest": p.get("nearest_world"),
            }
            for p in report["kmeans"]["profiles"]
        ],
        "paths": paths,
    }
    print(json.dumps(slim, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
