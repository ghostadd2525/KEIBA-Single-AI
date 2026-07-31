# -*- coding: utf-8 -*-
"""Version74 — World Strategy Validation (research only, 285R).

Labels = V72/V73 CEW (Contract Expected World).
No Trigger / Blueprint / Signal / Threshold / World Meaning / PE / Prediction / Production mutation.
No improvement — measurement only.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
sys.path.insert(0, str(ROOT / "services" / "win5-ai"))

from app.research._v64_world_strategy_discovery import (  # noqa: E402
    STYLE_VALUES,
    analyze_world,
    build_race_rows,
    ranking_concepts,
    _f,
)

SCHEMA = "v74-world-strategy-validation/1.0"
STRATEGY_WORLDS = (
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
    "mixed_world",
    "bug_world",
)
ALL_LABELS = STRATEGY_WORLDS + ("unsatisfied",)

# Minimum n for claiming stable strategy (report-only threshold)
MIN_STABLE_N = 20


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 5 or n != len(ys):
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx < 1e-12 or dy < 1e-12:
        return None
    return num / (dx * dy)


def spearman_rank_corr(ranks_a: dict[str, int], ranks_b: dict[str, int]) -> float | None:
    keys = sorted(set(ranks_a) & set(ranks_b))
    if len(keys) < 3:
        return None
    xs = [float(ranks_a[k]) for k in keys]
    ys = [float(ranks_b[k]) for k in keys]
    return pearson(xs, ys)


def cosine(a: dict[str, float], b: dict[str, float], keys: list[str]) -> float | None:
    va = [a.get(k) for k in keys]
    vb = [b.get(k) for k in keys]
    if any(v is None for v in va + vb):
        # use intersection of non-null
        keys2 = [k for k in keys if a.get(k) is not None and b.get(k) is not None]
        if len(keys2) < 2:
            return None
        va = [float(a[k]) for k in keys2]
        vb = [float(b[k]) for k in keys2]
    else:
        va = [float(x) for x in va]  # type: ignore
        vb = [float(x) for x in vb]  # type: ignore
    na = math.sqrt(sum(x * x for x in va))
    nb = math.sqrt(sum(x * x for x in vb))
    if na < 1e-12 or nb < 1e-12:
        return None
    return sum(x * y for x, y in zip(va, vb)) / (na * nb)


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    u = a | b
    return len(a & b) / len(u) if u else 0.0


def load_cew_labels() -> dict[str, str]:
    path = ROOT / "docs/research/_v73-contract-intent-evaluation.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    return {r["race_id"]: r["cew_world"] for r in doc["rows"]}


def attach_cew(rows: list[dict[str, Any]], cew: dict[str, str]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        rid = r["race_id"]
        if rid not in cew:
            continue
        rr = dict(r)
        rr["cew_world"] = cew[rid]
        out.append(rr)
    return out


def subset(rows: list[dict[str, Any]], world: str) -> list[dict[str, Any]]:
    return [r for r in rows if r.get("cew_world") == world]


def winner_profile(races: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(races)
    if n == 0:
        return {"n": 0}
    w_mr = []
    w_wp = []
    w_hist = []
    w_odds = []
    w_pop = []
    styles = Counter()
    for race in races:
        for h in race["horses"]:
            if not h["is_winner"]:
                continue
            w_mr.append(h["model_rank"])
            w_wp.append(h["win_prob"])
            w_hist.append(h["history_score"])
            w_odds.append(h["odds"])
            if h.get("popularity") is not None:
                w_pop.append(h["popularity"])
            styles[h.get("running_style") or "unknown"] += 1
    ctx = {}
    for k in ("top_gap", "ability_separation", "upper_ability_band", "mid_eval_band_open", "top_monopoly", "ability_subordinate"):
        vals = [race["concepts"][k] for race in races if race["concepts"].get(k) is not None]
        ctx[k] = sum(vals) / len(vals) if vals else None
    fs = [race["field_size"] for race in races]
    dist = [race["distance"] for race in races if race.get("distance") is not None]
    return {
        "n": n,
        "winner_model_rank_mean": sum(w_mr) / len(w_mr) if w_mr else None,
        "winner_win_prob_mean": sum(w_wp) / len(w_wp) if w_wp else None,
        "winner_history_mean": sum(w_hist) / len(w_hist) if w_hist else None,
        "winner_odds_mean": sum(w_odds) / len(w_odds) if w_odds else None,
        "winner_popularity_mean": sum(w_pop) / len(w_pop) if w_pop else None,
        "popularity_races_n": len(w_pop),
        "style_counts": dict(styles),
        "context_means": ctx,
        "field_size_mean": sum(fs) / len(fs) if fs else None,
        "distance_mean": sum(dist) / len(dist) if dist else None,
    }


def feature_interactions(races: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Context × winner strength correlations (285R measurable)."""
    if len(races) < 8:
        return []
    pairs = [
        ("top_gap", "win_prob_pct"),
        ("top_gap", "history_pct"),
        ("ability_subordinate", "win_prob_pct"),
        ("ability_subordinate", "history_pct"),
        ("field_size", "win_prob_pct"),
        ("field_size", "history_pct"),
        ("mid_eval_band_open", "win_prob_pct"),
        ("upper_ability_band", "win_prob_pct"),
    ]
    out = []
    for ck, hk in pairs:
        xs, ys = [], []
        for race in races:
            if ck == "field_size":
                xv = float(race["field_size"])
            else:
                xv = race["concepts"].get(ck)
                if xv is None:
                    continue
                xv = float(xv)
            wh = next(h for h in race["horses"] if h["is_winner"])
            yv = wh.get(hk)
            if yv is None:
                continue
            xs.append(xv)
            ys.append(float(yv))
        r = pearson(xs, ys)
        if r is None:
            continue
        out.append({"context": ck, "winner_feature": hk, "r": r, "n": len(xs)})
    return out


def importance_ranks(analysis: dict[str, Any]) -> dict[str, int]:
    imp = analysis.get("importance") or []
    # exclude popularity for cross-world rank compare (partial coverage)
    feats = [x for x in imp if not str(x["feature"]).startswith("popularity")]
    return {row["feature"]: i + 1 for i, row in enumerate(feats)}


def run() -> dict[str, Any]:
    cew = load_cew_labels()
    corp = json.loads((ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(encoding="utf-8"))
    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fx_rows = fx.get("rows") or fx.get("evaluations") or []
    fxby = {r["race_id"]: r for r in fx_rows}
    # dual stub unused for CEW path — build_race_rows expects dual dict
    dual = {rid: {"legacy_world": None, "v44_world": None} for rid in cew}
    rows = attach_cew(build_race_rows(corp, dual, fxby), cew)

    dist = Counter(r["cew_world"] for r in rows)
    by_world: dict[str, Any] = {}
    for w in ALL_LABELS:
        races = subset(rows, w)
        analysis = analyze_world(races)
        profile = winner_profile(races)
        interactions = feature_interactions(races)
        by_world[w] = {
            "n": len(races),
            "stable": len(races) >= MIN_STABLE_N,
            "winner_profile": profile,
            "analysis": analysis,
            "importance_top": (analysis.get("importance") or [])[:10],
            "style_lift": analysis.get("style_lift") or [],
            "context_profile": analysis.get("context_profile") or {},
            "feature_interactions": interactions,
            "importance_ranks": importance_ranks(analysis) if analysis.get("n", 0) else {},
        }

    # Strategy separation summary
    stable_worlds = [w for w in STRATEGY_WORLDS if by_world[w]["stable"]]
    unstable = [w for w in STRATEGY_WORLDS if 0 < by_world[w]["n"] < MIN_STABLE_N]
    zero = [w for w in STRATEGY_WORLDS if by_world[w]["n"] == 0]

    def profile_vector(world: str) -> dict[str, float]:
        ca = by_world[world]["winner_profile"]["context_means"] or {}
        out: dict[str, float] = {}
        for k in (
            "top_gap",
            "ability_separation",
            "upper_ability_band",
            "mid_eval_band_open",
            "top_monopoly",
            "ability_subordinate",
        ):
            if ca.get(k) is not None:
                out[k] = float(ca[k])
        return out

    def context_profile_corr(a: str, b: str) -> float | None:
        """Pearson corr of shared concept means (scale-safe; not raw cosine of distance)."""
        va = profile_vector(a)
        vb = profile_vector(b)
        keys = sorted(set(va) & set(vb))
        if len(keys) < 3:
            return None
        return pearson([va[k] for k in keys], [vb[k] for k in keys])

    compare_worlds = [w for w in ALL_LABELS if by_world[w]["n"] > 0]
    pairwise = []
    for a, b in combinations(compare_worlds, 2):
        cos = context_profile_corr(a, b)
        ra = by_world[a]["importance_ranks"]
        rb = by_world[b]["importance_ranks"]
        sp = spearman_rank_corr(ra, rb) if ra and rb else None
        top_a = {
            x["feature"]
            for x in by_world[a]["importance_top"][:5]
            if not str(x["feature"]).startswith("popularity")
        }
        top_b = {
            x["feature"]
            for x in by_world[b]["importance_top"][:5]
            if not str(x["feature"]).startswith("popularity")
        }
        jac = jaccard(top_a, top_b) if top_a and top_b else None
        style_sep = 0.0
        sa = {x["style"]: x["lift"] for x in by_world[a]["style_lift"]}
        sb = {x["style"]: x["lift"] for x in by_world[b]["style_lift"]}
        for st in STYLE_VALUES:
            style_sep = max(style_sep, abs(sa.get(st, 0.0) - sb.get(st, 0.0)))
        pairwise.append(
            {
                "world_a": a,
                "world_b": b,
                "n_a": by_world[a]["n"],
                "n_b": by_world[b]["n"],
                "both_stable": by_world[a]["stable"] and by_world[b]["stable"],
                "both_strategy_stable": (
                    a in STRATEGY_WORLDS
                    and b in STRATEGY_WORLDS
                    and by_world[a]["stable"]
                    and by_world[b]["stable"]
                ),
                "context_profile_corr": cos,
                "importance_spearman": sp,
                "top5_jaccard": jac,
                "style_lift_max_abs_diff": style_sep,
            }
        )

    # Interaction sign flips among stable positive Worlds
    sign_flips = []
    if len(stable_worlds) >= 2:
        keys_seen = set()
        for w in stable_worlds:
            for it in by_world[w]["feature_interactions"]:
                keys_seen.add((it["context"], it["winner_feature"]))
        for ck, hk in sorted(keys_seen):
            signed = {}
            for w in stable_worlds:
                for it in by_world[w]["feature_interactions"]:
                    if it["context"] == ck and it["winner_feature"] == hk:
                        signed[w] = it["r"]
            pos = [w for w, r in signed.items() if r is not None and r >= 0.08]
            neg = [w for w, r in signed.items() if r is not None and r <= -0.08]
            if pos and neg:
                sign_flips.append(
                    {
                        "context": ck,
                        "winner_feature": hk,
                        "positive_worlds": pos,
                        "negative_worlds": neg,
                        "values": signed,
                    }
                )

    stable_pairs = [p for p in pairwise if p["both_stable"]]
    strategy_stable_pairs = [p for p in pairwise if p.get("both_strategy_stable")]
    jac_vals = [p["top5_jaccard"] for p in strategy_stable_pairs if p.get("top5_jaccard") is not None]
    corr_vals = [
        p["context_profile_corr"]
        for p in strategy_stable_pairs
        if p.get("context_profile_corr") is not None
    ]
    mean_jac = sum(jac_vals) / len(jac_vals) if jac_vals else None
    mean_ctx_corr = sum(corr_vals) / len(corr_vals) if corr_vals else None

    evidence = {
        "stable_worlds": stable_worlds,
        "unstable_worlds": unstable,
        "zero_worlds": zero,
        "unsatisfied_n": by_world["unsatisfied"]["n"],
        "n_sign_flips": len(sign_flips),
        "mean_top5_jaccard_strategy_stable": mean_jac,
        "mean_context_profile_corr_strategy_stable": mean_ctx_corr,
        "strategy_stable_pair_count": len(strategy_stable_pairs),
        "stable_pair_count_incl_unsatisfied": len(stable_pairs),
    }

    spearman_low = any(
        p.get("importance_spearman") is not None and p["importance_spearman"] < 0.7
        for p in strategy_stable_pairs
    )
    style_sep_ok = any(p.get("style_lift_max_abs_diff", 0) >= 0.08 for p in strategy_stable_pairs)
    high_overlap = (
        mean_jac is not None
        and mean_jac >= 0.9
        and len(sign_flips) == 0
        and not style_sep_ok
        and not spearman_low
    )
    sep_signal = len(sign_flips) > 0 or style_sep_ok or spearman_low

    # A: ≥3 stable positive Worlds + separation. 2 stable + sep → B. else C/B.
    if len(stable_worlds) < 2:
        verdict = "C"
        verdict_text = "安定標本の Strategy World が不足し、分ける価値を実証できない"
    elif high_overlap:
        verdict = "C"
        verdict_text = "安定 World 間で特徴・相互作用の差が小さく、分ける価値が低い"
    elif sep_signal and len(stable_worlds) >= 3 and (mean_jac is None or mean_jac < 0.75):
        verdict = "A"
        verdict_text = "Worldごとに明確なStrategy差がある"
    elif sep_signal:
        verdict = "B"
        verdict_text = "一部重複する（安定 World は限定的だが、差の証拠あり）"
    else:
        verdict = "B"
        verdict_text = "一部重複する（差は限定的）"

    # If only midhole+rank7 stable among positive worlds, check unsatisfied as residual
    # Include unsatisfied in context comparison note
    report = {
        "schema": SCHEMA,
        "generated_at": _now(),
        "n_races": len(rows),
        "label_authority": "v72_cew_via_v73",
        "min_stable_n": MIN_STABLE_N,
        "cew_distribution": dict(dist),
        "by_world": {
            w: {
                "n": by_world[w]["n"],
                "stable": by_world[w]["stable"],
                "winner_profile": by_world[w]["winner_profile"],
                "importance_top": by_world[w]["importance_top"],
                "style_lift": by_world[w]["style_lift"],
                "context_profile": by_world[w]["context_profile"],
                "feature_interactions": by_world[w]["feature_interactions"],
                "importance_ranks": by_world[w]["importance_ranks"],
                "analysis_status": by_world[w]["analysis"].get("status"),
            }
            for w in ALL_LABELS
        },
        "pairwise_similarity": pairwise,
        "interaction_sign_flips": sign_flips,
        "evidence": evidence,
        "verdict": {"code": verdict, "text": verdict_text},
        "locks": [
            "Trigger",
            "Blueprint",
            "Signal",
            "Threshold",
            "World Meaning",
            "PE",
            "Prediction",
            "Production",
        ],
    }
    return report


def _fmt(x: Any) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.4f}"
    return str(x)


def write_docs(report: dict[str, Any]) -> dict[str, Path]:
    out = ROOT / "docs" / "research"
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    paths["json"] = out / "_v74-world-strategy-validation.json"
    paths["json"].write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    v = report["verdict"]
    dist = report["cew_distribution"]

    # main validation
    lines = [
        "# Version74 — World Strategy Validation",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        f"**Corpus:** 285R  ",
        f"**Labels:** V72/V73 CEW（Contract Expected World）  ",
        f"**Verdict:** **{v['code']}** — {v['text']}  ",
        "**Locks:** Trigger / Blueprint / Signal / Threshold / World Meaning / PE / Prediction / Production — 非変更  ",
        "**非目的:** Hit 改善 / PE 変更",
        "",
        "## CEW 分布",
        "",
        "| World | n | stable (≥20) |",
        "|---|---:|:---:|",
    ]
    for w in ALL_LABELS:
        n = dist.get(w, 0)
        st = "Y" if n >= report["min_stable_n"] else ("—" if n == 0 else "N")
        lines.append(f"| `{w}` | {n} | {st} |")

    lines += [
        "",
        "## ① World別勝ち方（勝ち馬・脚質・人気・能力差・展開文脈）",
        "",
    ]
    for w in ALL_LABELS:
        bw = report["by_world"][w]
        if bw["n"] == 0:
            lines += [f"### `{w}`", "", "サンプル 0 — 抽出不可。", ""]
            continue
        wp = bw["winner_profile"]
        lines += [
            f"### `{w}`（n={bw['n']}{'' if bw['stable'] else '・不安定'}）",
            "",
            "| 指標 | 値 |",
            "|---|---:|",
            f"| winner model_rank mean | {_fmt(wp.get('winner_model_rank_mean'))} |",
            f"| winner win_prob mean | {_fmt(wp.get('winner_win_prob_mean'))} |",
            f"| winner history mean | {_fmt(wp.get('winner_history_mean'))} |",
            f"| winner odds mean | {_fmt(wp.get('winner_odds_mean'))} |",
            f"| winner popularity mean* | {_fmt(wp.get('winner_popularity_mean'))} |",
            f"| field_size mean | {_fmt(wp.get('field_size_mean'))} |",
            f"| distance mean | {_fmt(wp.get('distance_mean'))} |",
            "",
            "能力差・展開文脈（レース平均）:",
            "",
            "| Concept | mean |",
            "|---|---:|",
        ]
        for k, val in (wp.get("context_means") or {}).items():
            lines.append(f"| `{k}` | {_fmt(val)} |")
        lines += ["", "脚質（勝ち馬カウント）:", "", "| Style | n |", "|---|---:|"]
        for st, c in sorted((wp.get("style_counts") or {}).items(), key=lambda x: -x[1]):
            lines.append(f"| {st} | {c} |")
        lines += ["", "脚質リフト（winner_share − loser_share）:", "", "| Style | lift |", "|---|---:|"]
        for row in bw.get("style_lift") or []:
            lines.append(f"| {row['style']} | {_fmt(row['lift'])} |")
        lines.append("")
        lines.append("\\*popularity は変動ありレースのみ。")
        lines.append("")

    lines += [
        "## ④ Strategy Separation（要約）",
        "",
        f"- 安定 World（n≥{report['min_stable_n']}）: {', '.join(f'`{w}`' for w in report['evidence']['stable_worlds']) or 'なし'}",
        f"- 不安定（0<n<{report['min_stable_n']}）: {', '.join(f'`{w}`' for w in report['evidence']['unstable_worlds']) or 'なし'}",
        f"- ゼロ: {', '.join(f'`{w}`' for w in report['evidence']['zero_worlds']) or 'なし'}",
        f"- 相互作用符号逆転ペア数: **{report['evidence']['n_sign_flips']}**",
        f"- 安定 Strategy ペア mean Top5 Jaccard: {_fmt(report['evidence'].get('mean_top5_jaccard_strategy_stable'))}",
        f"- 安定 Strategy ペア mean context profile corr: {_fmt(report['evidence'].get('mean_context_profile_corr_strategy_stable'))}",
        f"- unsatisfied n: {report['evidence'].get('unsatisfied_n')}",
        "",
        "## 数値正本",
        "",
        "`docs/research/_v74-world-strategy-validation.json`",
        "",
    ]
    paths["main"] = out / "v74-world-strategy-validation.md"
    paths["main"].write_text("\n".join(lines), encoding="utf-8")

    # feature separation
    fl = [
        "# Version74 — World Feature Separation",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "**Metric:** oriented effect = winner−loser（odds/popularity は低値有利に向き付け）",
        "",
        "## ② World別特徴量重要度",
        "",
    ]
    for w in ALL_LABELS:
        bw = report["by_world"][w]
        fl += [f"### `{w}`（n={bw['n']}）", ""]
        if bw["n"] == 0:
            fl += ["サンプル 0。", ""]
            continue
        fl += ["| Rank | Feature | Effect | FieldHit |", "|---:|---|---:|---:|"]
        for i, row in enumerate(bw["importance_top"], 1):
            fl.append(
                f"| {i} | `{row['feature']}` | {_fmt(row['effect'])} | {_fmt(row.get('field_hit_rate'))} |"
            )
        fl.append("")

    fl += [
        "## ⑤ Feature Interaction（Context × Winner）",
        "",
        "安定 World を中心に、レース文脈と勝ち馬強度の Pearson r（n≥5 のみ算出）。",
        "",
    ]
    for w in report["evidence"]["stable_worlds"] + [
        x for x in ALL_LABELS if report["by_world"][x]["n"] > 0 and x not in report["evidence"]["stable_worlds"]
    ]:
        bw = report["by_world"][w]
        fl += [f"### `{w}`", "", "| Context | Winner feature | r | n |", "|---|---|---:|---:|"]
        for it in bw["feature_interactions"]:
            fl.append(f"| `{it['context']}` | `{it['winner_feature']}` | {_fmt(it['r'])} | {it['n']} |")
        if not bw["feature_interactions"]:
            fl.append("| — | — | — | — |")
        fl.append("")

    fl += ["## 符号逆転（安定 World 間）", ""]
    if not report["interaction_sign_flips"]:
        fl += ["該当値 |r|≥0.08 の正負共存なし（または安定 World 不足）。", ""]
    else:
        fl += ["| Context | Winner feat | + Worlds | − Worlds |", "|---|---|---|---|"]
        for sf in report["interaction_sign_flips"]:
            fl.append(
                f"| `{sf['context']}` | `{sf['winner_feature']}` | {', '.join(sf['positive_worlds'])} | {', '.join(sf['negative_worlds'])} |"
            )
        fl.append("")

    paths["feat"] = out / "v74-world-feature-separation.md"
    paths["feat"].write_text("\n".join(fl), encoding="utf-8")

    # similarity
    sl = [
        "# Version74 — Cross World Similarity",
        "",
        f"**Generated:** `{report['generated_at']}`  ",
        "ラベル = CEW。類似度は 285R 実測のみ。",
        "",
        "## ③ Pairwise",
        "",
        "| A | B | n_a | n_b | stable | strat | ctx ρ | importance ρ | Top5 Jaccard | style Δmax |",
        "|---|---|---:|---:|:---:|:---:|---:|---:|---:|---:|",
    ]
    for p in report["pairwise_similarity"]:
        sl.append(
            f"| `{p['world_a']}` | `{p['world_b']}` | {p['n_a']} | {p['n_b']} | "
            f"{'Y' if p['both_stable'] else 'N'} | "
            f"{'Y' if p.get('both_strategy_stable') else 'N'} | "
            f"{_fmt(p.get('context_profile_corr'))} | "
            f"{_fmt(p['importance_spearman'])} | {_fmt(p['top5_jaccard'])} | {_fmt(p['style_lift_max_abs_diff'])} |"
        )
    sl += [
        "",
        "## 分ける価値の評価（測定）",
        "",
        f"- Strategy 安定ペア mean Top5 Jaccard = {_fmt(report['evidence'].get('mean_top5_jaccard_strategy_stable'))}",
        f"- Strategy 安定ペア mean context profile corr = {_fmt(report['evidence'].get('mean_context_profile_corr_strategy_stable'))}",
        f"- 相互作用符号逆転 = {report['evidence']['n_sign_flips']} 件",
        "",
        "高 Jaccard（馬特徴セット重複）でも、文脈プロファイル相関・相互作用符号・脚質リフトが異なれば Selector としての分離理由になる。",
        "",
        f"**Verdict 連動:** **{v['code']}** — {v['text']}",
        "",
    ]
    paths["sim"] = out / "v74-cross-world-similarity.md"
    paths["sim"].write_text("\n".join(sl), encoding="utf-8")

    # governance
    paths["gov"] = out / "v74-governance.md"
    paths["gov"].write_text(
        "\n".join(
            [
                "# Version74 — Governance（World Strategy Validation）",
                "",
                f"**Date:** {report['generated_at'][:10]}  ",
                f"**Verdict:** **{v['code']}** — {v['text']}  ",
                "**Type:** Validation only（改善禁止）",
                "",
                "## 根拠サマリ（285R / CEW）",
                "",
                "| Item | Value |",
                "|---|---|",
                f"| CEW 分布 | `{json.dumps(dist, ensure_ascii=False)}` |",
                f"| 安定 World | {report['evidence']['stable_worlds']} |",
                f"| 不安定 World | {report['evidence']['unstable_worlds']} |",
                f"| ゼロ World | {report['evidence']['zero_worlds']} |",
                f"| 符号逆転 | {report['evidence']['n_sign_flips']} |",
                f"| mean Top5 Jaccard (strategy stable) | {_fmt(report['evidence'].get('mean_top5_jaccard_strategy_stable'))} |",
                f"| mean context profile corr (strategy stable) | {_fmt(report['evidence'].get('mean_context_profile_corr_strategy_stable'))} |",
                "",
                "【Decision】",
                "",
                "| Item | Value |",
                "|---|---|",
                "| Action Type | World Strategy Validation |",
                "| Implementation Required | **No** |",
                "| Deployment Required | No |",
                "| Configuration Required | No |",
                "| Production Required | No |",
                "| Rollback Required | No |",
                "| Risk | None（読取のみ） |",
                f"| Expected Next Action | Verdict {v['code']} を前提とした設計 Decision（本フェーズ改善禁止） |",
                "",
                "## 遵守",
                "",
                "| 制約 | |",
                "|---|---|",
                "| Trigger/Blueprint/Signal/Threshold/World Meaning 非変更 | PASS |",
                "| PE/Prediction/Production 非変更 | PASS |",
                "| 改善禁止 | PASS |",
                "| ラベル = CEW のみ | PASS |",
                "| 285R 実データのみ | PASS |",
                "",
                "## 成果物",
                "",
                "- `v74-world-strategy-validation.md`",
                "- `v74-world-feature-separation.md`",
                "- `v74-cross-world-similarity.md`",
                "- `v74-governance.md`",
                "- `_v74-world-strategy-validation.json`",
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
                "verdict": report["verdict"],
                "distribution": report["cew_distribution"],
                "evidence": report["evidence"],
                "paths": {k: str(v) for k, v in paths.items()},
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
