# -*- coding: utf-8 -*-
"""Version64 — World Strategy Discovery (research only, 285R).

No PE / Prediction / Trigger / Signal / World / Threshold / Production mutation.
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\win5-ai\KEIBA-Single-AI")
WORLDS = (
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
    "mixed_world",
    "bug_world",
)

# Horse features oriented so higher = more "favorable" for winning hypothesis tests
# odds/popularity/model_rank are inverted (lower raw → higher oriented)
HORSE_FEATURES = (
    "win_prob",
    "history_score",
    "odds_inv",  # 1/odds
    "popularity_inv",  # lower popularity number is better → invert via rank pct
    "history_pct",  # within-race percentile of history_score
    "win_prob_pct",
    "odds_pct_low",  # percentile where low odds = high score
    "popularity_pct_low",
)

STYLE_VALUES = ("逃げ", "先行", "差し", "追込")


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


def ranking_concepts(runners: list[dict[str, Any]]) -> dict[str, float | None]:
    probs = []
    for u in runners:
        p = _f(u.get("win_prob"))
        if p is not None:
            probs.append(p)
    if len(probs) < 2:
        return {
            "top_gap": None,
            "ability_separation": None,
            "upper_ability_band": None,
            "mid_eval_band_open": None,
            "top_monopoly": None,
            "ability_subordinate": None,
        }
    probs = sorted(probs, reverse=True)
    s = sum(probs) or 1.0
    top_gap = probs[0] - probs[1]
    median = probs[len(probs) // 2]
    return {
        "top_gap": top_gap,
        "ability_separation": probs[0] - median,
        "upper_ability_band": sum(probs[:3]) / s,
        "mid_eval_band_open": (sum(probs[3:10]) / s) if len(probs) > 3 else 0.0,
        "top_monopoly": probs[0] / s,
        "ability_subordinate": 1.0 - min(1.0, top_gap * 5.0),
    }


def pct_rank(values: list[float], idx: int, higher_better: bool) -> float:
    """0..1 percentile within race; 1 = best under orientation."""
    n = len(values)
    if n <= 1:
        return 0.5
    v = values[idx]
    if higher_better:
        better = sum(1 for x in values if x < v)
        ties = sum(1 for x in values if x == v)
    else:
        better = sum(1 for x in values if x > v)
        ties = sum(1 for x in values if x == x and x == v)
        better = sum(1 for x in values if x > v)
        ties = sum(1 for x in values if x == v)
    return (better + 0.5 * (ties - 1)) / (n - 1) if n > 1 else 0.5


def zscore(values: list[float], idx: int) -> float | None:
    n = len(values)
    if n < 2:
        return None
    mu = sum(values) / n
    var = sum((x - mu) ** 2 for x in values) / n
    sd = math.sqrt(var)
    if sd < 1e-12:
        return 0.0
    return (values[idx] - mu) / sd


def build_race_rows(corp, dual, fxby):
    rows = []
    for race in corp["races"]:
        rid = race["race_id"]
        d = dual.get(rid) or {}
        fx = fxby.get(rid) or {}
        runners = list(race.get("runners") or [])
        if len(runners) < 3:
            continue
        wid = str(race.get("winner_id") or "")
        widx = None
        for i, u in enumerate(runners):
            if str(u.get("horse_id") or "") == wid:
                widx = i
                break
        if widx is None:
            continue

        win_probs = [_f(u.get("win_prob")) or 0.0 for u in runners]
        hist = [_f(u.get("history_score")) or 0.0 for u in runners]
        odds = []
        for u in runners:
            o = _f(u.get("odds"))
            odds.append(o if o and o > 0 else None)
        pops = []
        for u in runners:
            p = _f(u.get("popularity"))
            pops.append(p if p and p > 0 else None)

        # Odds: fill rare missing with max observed (still real variance elsewhere)
        if any(x is None for x in odds):
            mx = max((x for x in odds if x is not None), default=99.0)
            odds = [mx if x is None else x for x in odds]
        # Popularity: only use when race has real varying values (>0 and >1 unique).
        # Do NOT impute placeholders (would fabricate constant fields).
        valid_pops = [p for p in pops if p is not None]
        has_valid_popularity = len(set(valid_pops)) > 1 and len(valid_pops) == len(runners)

        concepts = ranking_concepts(runners)
        field_size = int(fx.get("field_size") or race.get("context", {}).get("field_size") or len(runners))
        distance = _f(fx.get("distance"))
        surface = fx.get("surface")

        horse_feats = []
        for i, u in enumerate(runners):
            feats = {
                "win_prob": win_probs[i],
                "history_score": hist[i],
                "odds": odds[i],
                "popularity": pops[i] if has_valid_popularity else None,
                "model_rank": int(u.get("model_rank") or 999),
                "running_style": u.get("running_style"),
                "win_prob_z": zscore(win_probs, i),
                "history_z": zscore(hist, i),
                "odds_z": zscore(odds, i),
                "popularity_z": zscore(valid_pops, i) if has_valid_popularity else None,
                "win_prob_pct": pct_rank(win_probs, i, True),
                "history_pct": pct_rank(hist, i, True),
                "odds_pct_low": pct_rank(odds, i, False),
                "popularity_pct_low": pct_rank(valid_pops, i, False) if has_valid_popularity else None,
                "is_winner": i == widx,
            }
            horse_feats.append(feats)

        rows.append(
            {
                "race_id": rid,
                "legacy_world": d.get("legacy_world"),
                "v44_world": d.get("v44_world"),
                "field_size": field_size,
                "distance": distance,
                "surface": surface,
                "concepts": concepts,
                "horses": horse_feats,
                "winner_model_rank": horse_feats[widx]["model_rank"],
                "has_valid_popularity": has_valid_popularity,
            }
        )
    return rows


def world_subset(rows, world: str, label_source: str):
    out = []
    for r in rows:
        if label_source == "legacy":
            if r["legacy_world"] == world:
                out.append(r)
        elif label_source == "v44":
            if r["v44_world"] == world:
                out.append(r)
        elif label_source == "hybrid":
            # Legacy for worlds that exist; else V44 for rank7/bug only
            if world in ("rank7_world", "bug_world"):
                if r["v44_world"] == world:
                    out.append(r)
            else:
                if r["legacy_world"] == world:
                    out.append(r)
        else:
            raise ValueError(label_source)
    return out


def analyze_world(races: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(races)
    if n == 0:
        return {"n": 0, "status": "insufficient_sample"}

    # Winner / loser aggregates for oriented features (higher = more winner-like)
    orient_keys = [
        ("win_prob_z", "win_prob_z", +1),
        ("history_z", "history_z", +1),
        ("odds_z", "odds_z", -1),  # winners tend to lower odds → negative z preferred; flip sign for "favor"
        ("popularity_z", "popularity_z", -1),
        ("win_prob_pct", "win_prob_pct", +1),
        ("history_pct", "history_pct", +1),
        ("odds_pct_low", "odds_pct_low", +1),
        ("popularity_pct_low", "popularity_pct_low", +1),
    ]

    def collect(key: str, winners_only: bool | None):
        vals = []
        for race in races:
            for h in race["horses"]:
                if winners_only is True and not h["is_winner"]:
                    continue
                if winners_only is False and h["is_winner"]:
                    continue
                v = h.get(key)
                if v is None:
                    continue
                vals.append(float(v))
        return vals

    importance = []
    for name, key, sign in orient_keys:
        wvals = collect(key, True)
        lvals = collect(key, False)
        if not wvals or not lvals:
            continue
        if name.startswith("popularity") and len(wvals) < 8:
            continue
        wmean = sum(wvals) / len(wvals)
        lmean = sum(lvals) / len(lvals)
        # effect: signed so positive = winners higher on "good" orientation
        raw_delta = wmean - lmean
        effect = raw_delta * sign if name in ("odds_z", "popularity_z") else raw_delta
        # For odds_z/popularity_z: winners should have lower raw z; raw_delta negative; * (-1) → positive effect
        if name in ("odds_z", "popularity_z"):
            effect = (lmean - wmean)  # positive if winners lower than losers

        # field hit: winner best on orientation (skip races lacking feature)
        hits = 0
        hit_den = 0
        for race in races:
            hs = race["horses"]
            if name.startswith("popularity") and not race.get("has_valid_popularity"):
                continue
            hit_den += 1
            if name == "win_prob_z":
                best = max(hs, key=lambda h: h["win_prob"])
                hits += int(best["is_winner"])
            elif name == "history_z":
                best = max(hs, key=lambda h: h["history_score"])
                hits += int(best["is_winner"])
            elif name == "odds_z":
                best = min(hs, key=lambda h: h["odds"])
                hits += int(best["is_winner"])
            elif name == "popularity_z":
                best = min(hs, key=lambda h: h["popularity"])
                hits += int(best["is_winner"])
            elif name.endswith("_pct") or name.endswith("_pct_low"):
                best = max(hs, key=lambda h: (h.get(key) if h.get(key) is not None else -999))
                hits += int(best["is_winner"])
            else:
                best = max(hs, key=lambda h: (h.get(key) or -999) * (1 if sign > 0 else -1))
                hits += int(best["is_winner"])
        if hit_den == 0:
            continue

        importance.append(
            {
                "feature": name,
                "winner_mean": wmean,
                "loser_mean": lmean,
                "effect": effect,
                "abs_effect": abs(effect),
                "field_hit_rate": hits / hit_den,
                "field_hit_n": hits,
                "field_hit_den": hit_den,
            }
        )

    importance.sort(key=lambda x: (-x["abs_effect"], -x["field_hit_rate"]))

    # Losing features: among losers, traits more extreme than winners (opposite of winner favor)
    losing = []
    for row in importance:
        # losers worse on oriented effect → list as losing trait description
        losing.append(
            {
                "feature": row["feature"],
                "loser_vs_winner_gap": -row["effect"],  # positive => losers lack this favor
                "loser_mean": row["loser_mean"],
                "winner_mean": row["winner_mean"],
            }
        )
    losing.sort(key=lambda x: -x["loser_vs_winner_gap"])

    # Style distribution
    w_styles = Counter()
    l_styles = Counter()
    for race in races:
        for h in race["horses"]:
            st = h.get("running_style") or "unknown"
            if h["is_winner"]:
                w_styles[st] += 1
            else:
                l_styles[st] += 1
    w_total = sum(w_styles.values()) or 1
    l_total = sum(l_styles.values()) or 1
    style_lift = []
    for st in STYLE_VALUES:
        wr = w_styles.get(st, 0) / w_total
        lr = l_styles.get(st, 0) / l_total
        style_lift.append({"style": st, "winner_share": wr, "loser_share": lr, "lift": wr - lr})
    style_lift.sort(key=lambda x: -x["lift"])

    # Race context profile
    ctx_keys = list(races[0]["concepts"].keys()) + ["field_size", "distance"]
    context_profile = {}
    for k in ctx_keys:
        vals = []
        for race in races:
            if k in race["concepts"]:
                v = race["concepts"][k]
            else:
                v = race.get(k)
            if v is None:
                continue
            vals.append(float(v))
        if vals:
            context_profile[k] = {
                "mean": sum(vals) / len(vals),
                "n": len(vals),
            }

    surface_dist = Counter(r.get("surface") for r in races)

    # Stable vs Context: split by median top_gap and by surface
    def stratum_effects(subset):
        if len(subset) < 5:
            return None
        out = {}
        for name, key, sign in orient_keys:
            wvals = []
            lvals = []
            for race in subset:
                for h in race["horses"]:
                    v = h.get(key)
                    if v is None:
                        continue
                    (wvals if h["is_winner"] else lvals).append(float(v))
            if len(wvals) < 3 or len(lvals) < 3:
                continue
            wmean = sum(wvals) / len(wvals)
            lmean = sum(lvals) / len(lvals)
            if name in ("odds_z", "popularity_z"):
                effect = lmean - wmean
            else:
                effect = wmean - lmean
            out[name] = effect
        return out

    gaps = [r["concepts"].get("top_gap") for r in races if r["concepts"].get("top_gap") is not None]
    stable = []
    contextual = []
    if len(gaps) >= 10:
        med = sorted(gaps)[len(gaps) // 2]
        low = [r for r in races if (r["concepts"].get("top_gap") or 0) <= med]
        high = [r for r in races if (r["concepts"].get("top_gap") or 0) > med]
        e_low = stratum_effects(low) or {}
        e_high = stratum_effects(high) or {}
        for feat in set(e_low) | set(e_high):
            a = e_low.get(feat)
            b = e_high.get(feat)
            if a is None or b is None:
                continue
            same_sign = (a >= 0 and b >= 0) or (a < 0 and b < 0)
            both_strong = abs(a) >= 0.05 and abs(b) >= 0.05
            if same_sign and both_strong:
                stable.append(
                    {
                        "feature": feat,
                        "effect_low_top_gap": a,
                        "effect_high_top_gap": b,
                        "split": "top_gap_median",
                    }
                )
            elif (a >= 0) != (b >= 0) or (abs(a) >= 0.08 and abs(b) < 0.03) or (abs(b) >= 0.08 and abs(a) < 0.03):
                contextual.append(
                    {
                        "feature": feat,
                        "effect_low_top_gap": a,
                        "effect_high_top_gap": b,
                        "split": "top_gap_median",
                    }
                )

    # surface split if both turf and dirt present
    turf = [r for r in races if r.get("surface") == "芝"]
    dirt = [r for r in races if r.get("surface") == "ダ"]
    if len(turf) >= 5 and len(dirt) >= 5:
        e_t = stratum_effects(turf) or {}
        e_d = stratum_effects(dirt) or {}
        for feat in set(e_t) | set(e_d):
            a = e_t.get(feat)
            b = e_d.get(feat)
            if a is None or b is None:
                continue
            if (a >= 0) != (b >= 0) and max(abs(a), abs(b)) >= 0.05:
                contextual.append(
                    {
                        "feature": feat,
                        "effect_turf": a,
                        "effect_dirt": b,
                        "split": "surface",
                    }
                )

    # winner model_rank distribution
    wranks = [r["winner_model_rank"] for r in races]
    wranks_sorted = sorted(wranks)

    return {
        "n": n,
        "status": "ok",
        "importance": importance,
        "top10": importance[:10],
        "losing_features": losing[:10],
        "style_lift": style_lift,
        "context_profile": context_profile,
        "surface_dist": dict(surface_dist),
        "stable_features": stable,
        "context_features": contextual,
        "winner_model_rank": {
            "mean": sum(wranks) / len(wranks),
            "median": wranks_sorted[len(wranks_sorted) // 2],
            "p25": wranks_sorted[len(wranks_sorted) // 4],
            "p75": wranks_sorted[(3 * len(wranks_sorted)) // 4],
        },
    }


def cross_world(by_world: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    # feature -> world -> effect
    feats = set()
    for w, rec in by_world.items():
        if rec.get("status") != "ok":
            continue
        for row in rec.get("importance") or []:
            feats.add(row["feature"])
    conflicts = []
    for feat in sorted(feats):
        effects = {}
        for w, rec in by_world.items():
            if rec.get("status") != "ok":
                continue
            for row in rec.get("importance") or []:
                if row["feature"] == feat:
                    effects[w] = row["effect"]
        if len(effects) < 2:
            continue
        pos = [w for w, e in effects.items() if e >= 0.05]
        neg = [w for w, e in effects.items() if e <= -0.05]
        if pos and neg:
            conflicts.append(
                {
                    "feature": feat,
                    "positive_worlds": pos,
                    "negative_worlds": neg,
                    "effects": effects,
                    "span": max(effects.values()) - min(effects.values()),
                }
            )
    conflicts.sort(key=lambda x: -x["span"])
    return conflicts


def strategy_text(world: str, rec: dict[str, Any]) -> str:
    if rec.get("status") != "ok":
        return f"{world}: サンプル不足のため戦略抽出不可（n={rec.get('n', 0)}）。"
    top = rec["top10"][:5]
    styles = rec["style_lift"][:2]
    ctx = rec.get("context_profile") or {}
    parts = []
    fav = [t["feature"] for t in top if t["effect"] > 0]
    parts.append("勝ち馬が相対的に高い: " + (", ".join(fav[:4]) if fav else "(明確な正効果なし)"))
    if styles:
        parts.append(
            "脚質リフト: "
            + ", ".join(f"{s['style']}({s['lift']:+.2f})" for s in styles if s["lift"] > 0)
            or "脚質差小"
        )
    tg = (ctx.get("top_gap") or {}).get("mean")
    mono = (ctx.get("top_monopoly") or {}).get("mean")
    mid = (ctx.get("mid_eval_band_open") or {}).get("mean")
    ctx_bits = []
    if tg is not None:
        ctx_bits.append(f"top_gap_mean={tg:.3f}")
    if mono is not None:
        ctx_bits.append(f"top_monopoly_mean={mono:.3f}")
    if mid is not None:
        ctx_bits.append(f"mid_band_mean={mid:.3f}")
    if ctx_bits:
        parts.append("レース文脈: " + ", ".join(ctx_bits))
    wr = rec.get("winner_model_rank") or {}
    if wr:
        parts.append(f"勝ち馬 model_rank median={wr.get('median')}")
    return " / ".join(parts)


def differentiation_score(by_world: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Measure whether worlds have distinct top-feature signatures."""
    usable = {w: r for w, r in by_world.items() if r.get("status") == "ok" and r.get("n", 0) >= 10}
    if len(usable) < 2:
        return {"grade_hint": "C", "reason": "usable worlds < 2", "pairwise_topk_jaccard": {}}

    def topk(rec, k=5):
        return [x["feature"] for x in (rec.get("top10") or [])[:k]]

    pairs = {}
    jaccs = []
    worlds = sorted(usable.keys())
    for i, a in enumerate(worlds):
        for b in worlds[i + 1 :]:
            sa, sb = set(topk(usable[a])), set(topk(usable[b]))
            inter = len(sa & sb)
            union = len(sa | sb) or 1
            j = inter / union
            pairs[f"{a}|{b}"] = {"jaccard_top5": j, "shared": sorted(sa & sb)}
            jaccs.append(j)

    # effect vector correlation proxy: rank correlation of effects on shared features
    mean_j = sum(jaccs) / len(jaccs)
    # sign conflicts count
    conflicts = cross_world(usable)
    n_conflict_feats = len(conflicts)

    # top1 feature diversity
    top1s = [topk(r, 1)[0] for r in usable.values() if topk(r, 1)]
    unique_top1 = len(set(top1s))

    if mean_j <= 0.4 and (n_conflict_feats >= 1 or unique_top1 >= 3):
        hint = "A"
        reason = f"mean top5 Jaccard={mean_j:.2f}, conflict_features={n_conflict_feats}, unique_top1={unique_top1}"
    elif mean_j <= 0.7:
        hint = "B"
        reason = f"partial overlap mean Jaccard={mean_j:.2f}, conflict_features={n_conflict_feats}"
    else:
        hint = "C"
        reason = f"high overlap mean Jaccard={mean_j:.2f}"
    return {
        "grade_hint": hint,
        "reason": reason,
        "mean_top5_jaccard": mean_j,
        "conflict_feature_count": n_conflict_feats,
        "unique_top1": unique_top1,
        "pairwise_topk_jaccard": pairs,
        "usable_worlds": {w: usable[w]["n"] for w in usable},
    }


def main() -> None:
    corp = json.loads(
        (ROOT / "research/v3_lab/baselines/offline_gate/real_285r_corpus.json").read_text(encoding="utf-8")
    )
    dual = {
        json.loads(l)["race_id"]: json.loads(l)
        for l in (ROOT / "docs/implementation/w-s1-dual-eval-rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if l.strip()
    }
    fx = json.loads((ROOT / "fixtures/stats/baseline-285r-evaluations.json").read_text(encoding="utf-8"))
    fxby = {r["race_id"]: r for r in (fx.get("rows") or fx.get("evaluations"))}

    rows = build_race_rows(corp, dual, fxby)

    # Primary: hybrid labeling (Legacy + V44 for rank7/bug only)
    by_hybrid = {}
    for w in WORLDS:
        sub = world_subset(rows, w, "hybrid")
        by_hybrid[w] = analyze_world(sub)
        by_hybrid[w]["label_source"] = (
            "v44_positive" if w in ("rank7_world", "bug_world") else "legacy"
        )

    by_legacy = {w: analyze_world(world_subset(rows, w, "legacy")) for w in WORLDS}
    by_v44 = {w: analyze_world(world_subset(rows, w, "v44")) for w in WORLDS}

    conflicts = cross_world(by_hybrid)
    diff = differentiation_score(by_hybrid)

    # Race-context differentiation (Strategy Selector layer)
    concept_keys = [
        "top_gap",
        "ability_separation",
        "upper_ability_band",
        "mid_eval_band_open",
        "top_monopoly",
        "ability_subordinate",
    ]

    def mean_ctx(sub, key):
        vals = []
        for r in sub:
            if key == "field_size":
                vals.append(float(r["field_size"]))
            elif key == "distance":
                if r.get("distance") is not None:
                    vals.append(float(r["distance"]))
            else:
                v = r["concepts"].get(key)
                if v is not None:
                    vals.append(float(v))
        if not vals:
            return None
        return sum(vals) / len(vals)

    context_by_world = {}
    for w in WORLDS:
        sub = world_subset(rows, w, "hybrid")
        if not sub:
            context_by_world[w] = {"n": 0}
            continue
        context_by_world[w] = {
            "n": len(sub),
            **{k: mean_ctx(sub, k) for k in concept_keys + ["field_size", "distance"]},
            "winner_model_rank_median": sorted(r["winner_model_rank"] for r in sub)[len(sub) // 2],
        }

    def pearson(xs, ys):
        n = len(xs)
        if n < 8:
            return None
        mx = sum(xs) / n
        my = sum(ys) / n
        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
        dy = math.sqrt(sum((y - my) ** 2 for y in ys))
        if dx < 1e-12 or dy < 1e-12:
            return 0.0
        return num / (dx * dy)

    # Cross-world: correlation of race concept vs winner horse strength (sign flips)
    corr_specs = [
        ("top_gap", "win_prob_pct"),
        ("top_gap", "history_pct"),
        ("mid_eval_band_open", "win_prob_pct"),
        ("ability_subordinate", "history_pct"),
        ("field_size", "win_prob_pct"),
    ]
    corr_by_world = {}
    for w in WORLDS:
        sub = world_subset(rows, w, "hybrid")
        if len(sub) < 8:
            continue
        corr_by_world[w] = {}
        for ck, hk in corr_specs:
            xs, ys = [], []
            for r in sub:
                if ck == "field_size":
                    xv = float(r["field_size"])
                else:
                    xv = r["concepts"].get(ck)
                wh = next(h for h in r["horses"] if h["is_winner"])
                yv = wh.get(hk)
                if xv is None or yv is None:
                    continue
                xs.append(float(xv))
                ys.append(float(yv))
            corr_by_world[w][f"corr({ck},{hk})"] = pearson(xs, ys)

    corr_conflicts = []
    for key in [f"corr({a},{b})" for a, b in corr_specs]:
        effects = {w: corr_by_world[w][key] for w in corr_by_world if corr_by_world[w].get(key) is not None}
        pos = [w for w, e in effects.items() if e is not None and e >= 0.08]
        neg = [w for w, e in effects.items() if e is not None and e <= -0.08]
        if pos and neg:
            corr_conflicts.append(
                {
                    "metric": key,
                    "positive_worlds": pos,
                    "negative_worlds": neg,
                    "effects": effects,
                    "span": max(effects.values()) - min(effects.values()),
                }
            )
    corr_conflicts.sort(key=lambda x: -x["span"])

    # Style reverse lifts across worlds
    style_matrix = {}
    for w in WORLDS:
        rec = by_hybrid[w]
        if rec.get("status") != "ok":
            continue
        style_matrix[w] = {s["style"]: s["lift"] for s in rec.get("style_lift") or []}
    style_conflicts = []
    for st in STYLE_VALUES:
        effects = {w: style_matrix[w].get(st, 0.0) for w in style_matrix}
        pos = [w for w, e in effects.items() if e >= 0.05]
        neg = [w for w, e in effects.items() if e <= -0.05]
        if pos and neg:
            style_conflicts.append(
                {
                    "feature": f"style:{st}",
                    "positive_worlds": pos,
                    "negative_worlds": neg,
                    "effects": effects,
                    "span": max(effects.values()) - min(effects.values()),
                }
            )

    strategies = {w: strategy_text(w, by_hybrid[w]) for w in WORLDS}

    # Refine grade with context/style evidence
    ctx_means = {
        w: context_by_world[w].get("top_gap")
        for w in WORLDS
        if context_by_world.get(w, {}).get("n", 0) >= 10
    }
    if len(ctx_means) >= 2:
        ctx_span = max(ctx_means.values()) - min(ctx_means.values())
    else:
        ctx_span = 0.0
    if diff["grade_hint"] == "C" and (corr_conflicts or style_conflicts or ctx_span >= 0.01):
        diff["grade_hint"] = "B"
        diff["reason"] = (
            diff["reason"]
            + f"; upgraded by race-context span(top_gap)={ctx_span:.4f}, "
            + f"corr_conflicts={len(corr_conflicts)}, style_conflicts={len(style_conflicts)}"
        )

    out = {
        "schema": "v64-world-strategy-discovery/1.0",
        "corpus": "real_285r",
        "n_races": len(rows),
        "method": {
            "horse_features": "within-race z / percentile from 285R runners (win_prob, history_score, odds; popularity only if valid)",
            "race_concepts": "derived from win_prob distribution (W-S1 ranking_concepts)",
            "labels": "hybrid: legacy_world for core/midupper/midhole/mixed; v44_world for rank7/bug",
            "importance": "winner_mean - loser_mean on oriented features; field_hit_rate",
            "popularity_note": "240/285 races lack varying popularity; excluded unless valid",
            "no_weighting": True,
            "no_pe_mutation": True,
        },
        "sample_sizes": {
            "hybrid": {w: by_hybrid[w].get("n", 0) for w in WORLDS},
            "legacy": {w: by_legacy[w].get("n", 0) for w in WORLDS},
            "v44": {w: by_v44[w].get("n", 0) for w in WORLDS},
        },
        "by_world": by_hybrid,
        "by_world_legacy": {w: {"n": by_legacy[w].get("n"), "status": by_legacy[w].get("status")} for w in WORLDS},
        "by_world_v44": {w: {"n": by_v44[w].get("n"), "status": by_v44[w].get("status")} for w in WORLDS},
        "race_context_by_world": context_by_world,
        "corr_by_world": corr_by_world,
        "cross_world_conflicts": conflicts,
        "cross_world_corr_conflicts": corr_conflicts,
        "cross_world_style_conflicts": style_conflicts,
        "differentiation": diff,
        "strategies": strategies,
    }

    path = ROOT / "docs/research/_v64-sim.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("n_races", len(rows))
    print("sample hybrid", out["sample_sizes"]["hybrid"])
    print("diff", diff["grade_hint"], diff["reason"])
    for w in WORLDS:
        rec = by_hybrid[w]
        print("---", w, "n", rec.get("n"), rec.get("status"))
        if rec.get("status") == "ok":
            for i, t in enumerate(rec["top10"][:5], 1):
                print(
                    f"  {i}. {t['feature']} effect={t['effect']:.3f} hit={t['field_hit_rate']:.1%}"
                )
            print("  strategy:", strategies[w][:140])
    print("horse_conflicts", len(conflicts))
    print("corr_conflicts", corr_conflicts)
    print("style_conflicts", style_conflicts)
    print("wrote", path)


if __name__ == "__main__":
    main()
