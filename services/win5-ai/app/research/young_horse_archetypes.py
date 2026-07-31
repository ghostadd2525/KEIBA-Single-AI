# -*- coding: utf-8 -*-
"""
Version13 Young Horse Archetype Research

Research-only: find winning debut/young-horse types via feature combinations.
Does NOT mutate Prediction / PE / CE / AI / Challenge / ResultAutomation / Resolver.
Does NOT create Young Horse Score.
"""
from __future__ import annotations

import itertools
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .analyzer import (
    EvidenceAnalyzer,
    _ig_bits,
    extract_runners,
    strict_hit,
    tie_group,
)
from .config import evidence_root, repo_root
from .ranking_engine import CATEGORICAL_FEATURES, feature_score, resolve_by_score
from .young_horse_intelligence import DEBUT_AGE_GROUPS, _pct, _safe_div

SCHEMA_VERSION = "expect-younghorse-archetype/1.0"

V13_FEATURES: tuple[str, ...] = (
    "popularity",
    "win_odds",
    "trainer",
    "sire",
    "damsire",
    "breeder",
    "oikiri_time",
    "oikiri_rating",
    "owner",
    "sale_price",
)

ORDINAL_BINS = (
    "popularity",
    "win_odds",
    "oikiri_time",
    "oikiri_rating",
    "sale_price",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_sale_man(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value)
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*万", s)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _oikiri_letter(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    for ch in text:
        if ch in {"A", "B", "C", "D", "E"}:
            return ch
    return None


def discretize_horse(
    *,
    values: dict[str, Any],
    cat_priors: dict[str, dict[str, float]],
    race_oikiri_times: list[float],
) -> dict[str, str]:
    """Map raw features -> coarse bins used for archetypes."""
    bins: dict[str, str] = {}

    # popularity
    try:
        pop = int(float(values.get("popularity")))
        if pop <= 1:
            bins["popularity"] = "P1"
        elif pop <= 3:
            bins["popularity"] = "P2-3"
        elif pop <= 6:
            bins["popularity"] = "P4-6"
        else:
            bins["popularity"] = "P7+"
    except (TypeError, ValueError):
        bins["popularity"] = "P_MISS"

    # win odds
    try:
        odds = float(values.get("win_odds"))
        if odds < 4.0:
            bins["win_odds"] = "O_SHORT"
        elif odds < 10.0:
            bins["win_odds"] = "O_MID"
        elif odds < 20.0:
            bins["win_odds"] = "O_LONG"
        else:
            bins["win_odds"] = "O_HEAVY"
    except (TypeError, ValueError):
        bins["win_odds"] = "O_MISS"

    # workout rating
    letter = _oikiri_letter(values.get("oikiri_rating"))
    if letter in {"A", "B"}:
        bins["oikiri_rating"] = f"WK_{letter}"
    elif letter in {"C", "D", "E"}:
        bins["oikiri_rating"] = "WK_CDE"
    else:
        bins["oikiri_rating"] = "WK_MISS"

    # workout time relative within race
    try:
        ot = float(values.get("oikiri_time"))
        if race_oikiri_times:
            ranked = sorted(race_oikiri_times)
            # faster (smaller) is better
            idx = ranked.index(ot) if ot in ranked else None
            if idx is None:
                bins["oikiri_time"] = "OT_MISS"
            else:
                q = (idx + 1) / len(ranked)
                if q <= 0.33:
                    bins["oikiri_time"] = "OT_FAST"
                elif q <= 0.66:
                    bins["oikiri_time"] = "OT_MID"
                else:
                    bins["oikiri_time"] = "OT_SLOW"
        else:
            bins["oikiri_time"] = "OT_MISS"
    except (TypeError, ValueError):
        bins["oikiri_time"] = "OT_MISS"

    # sale price
    sale = _parse_sale_man(values.get("sale_price"))
    if sale is None:
        bins["sale_price"] = "SALE_MISS"
    elif sale >= 8000:
        bins["sale_price"] = "SALE_HIGH"
    elif sale >= 3000:
        bins["sale_price"] = "SALE_MID"
    else:
        bins["sale_price"] = "SALE_LOW"

    # categorical prior strength (LOO)
    for fid in ("trainer", "sire", "damsire", "breeder", "owner"):
        prior = cat_priors.get(fid) or {}
        raw = values.get(fid)
        if raw is None or str(raw).strip() in {"", "-", "null", "None"}:
            bins[fid] = f"{fid.upper()}_MISS"
            continue
        key = str(raw).strip()
        p = float(prior.get(key, 0.0))
        # Laplace prior typically ~0.1-0.6; thresholds exploratory
        if p >= 0.35:
            bins[fid] = f"{fid.upper()}_STRONG"
        elif p >= 0.22:
            bins[fid] = f"{fid.upper()}_MID"
        else:
            bins[fid] = f"{fid.upper()}_WEAK"

    return bins


def _matches_rules(bins: dict[str, str], rules: dict[str, Any]) -> bool:
    for fid, allowed in rules.items():
        val = bins.get(fid)
        if isinstance(allowed, (list, tuple, set, frozenset)):
            if val not in allowed:
                return False
        else:
            if val != allowed:
                return False
    return True


# Hypothesis archetypes (research labels, not product scores)
HYPOTHESIS_ARCHETYPES: list[dict[str, Any]] = [
    {
        "id": "market_favorite",
        "label": "Market Favorite (P1)",
        "rules": {"popularity": "P1"},
    },
    {
        "id": "market_contender",
        "label": "Market Contender (P2-3)",
        "rules": {"popularity": "P2-3"},
    },
    {
        "id": "short_odds",
        "label": "Short Odds",
        "rules": {"win_odds": "O_SHORT"},
    },
    {
        "id": "fav_short",
        "label": "Favorite + Short Odds",
        "rules": {"popularity": "P1", "win_odds": "O_SHORT"},
    },
    {
        "id": "fav_workout",
        "label": "Favorite/Contender + Workout A/B",
        "rules": {
            "popularity": ["P1", "P2-3"],
            "oikiri_rating": ["WK_A", "WK_B"],
        },
    },
    {
        "id": "high_sale_market",
        "label": "High Sale + Market Top3",
        "rules": {
            "sale_price": "SALE_HIGH",
            "popularity": ["P1", "P2-3"],
        },
    },
    {
        "id": "sire_strong_market",
        "label": "Strong Sire + Market Top3",
        "rules": {
            "sire": "SIRE_STRONG",
            "popularity": ["P1", "P2-3"],
        },
    },
    {
        "id": "trainer_strong_market",
        "label": "Strong Trainer + Market Top3",
        "rules": {
            "trainer": "TRAINER_STRONG",
            "popularity": ["P1", "P2-3"],
        },
    },
    {
        "id": "blood_combo",
        "label": "Strong Sire + Strong Damsire",
        "rules": {"sire": "SIRE_STRONG", "damsire": "DAMSIRE_STRONG"},
    },
    {
        "id": "owner_breeder",
        "label": "Strong Owner + Strong Breeder",
        "rules": {"owner": "OWNER_STRONG", "breeder": "BREEDER_STRONG"},
    },
    {
        "id": "workout_fast_market",
        "label": "Fast Workout + Market Top6",
        "rules": {
            "oikiri_time": "OT_FAST",
            "popularity": ["P1", "P2-3", "P4-6"],
        },
    },
]


class YoungHorseArchetypeResearch:
    def __init__(self) -> None:
        migrate()
        self.features = V13_FEATURES
        self.analyzer = EvidenceAnalyzer(features=self.features)

    def load_young_corpus(self, *, debut_only: bool = False) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT
                  c.corpus_id, c.race_id, c.race_date, c.venue, c.surface, c.distance,
                  c.class_label, c.age_group, c.winner_horse_number, c.source,
                  c.prediction_id, s.snapshot_id, s.capture_status, p.bundle_json,
                  r.result_json, r.field_size
                FROM research_prediction_corpus c
                JOIN research_prediction_snapshots s
                  ON s.race_id = c.race_id AND s.capture_status = 'complete'
                JOIN predictions p ON p.id = s.prediction_id
                JOIN race_results r ON r.race_id = c.race_id
                WHERE c.is_young_horse = 1
                  AND c.winner_horse_number IS NOT NULL
                  AND c.race_id NOT LIKE '2099%'
                ORDER BY c.race_date ASC, c.race_id ASC
                """
            ).fetchall()
            seen: set[str] = set()
            out: list[dict[str, Any]] = []
            for r in rows:
                rid = str(r["race_id"])
                if rid in seen:
                    continue
                if debut_only and str(r["age_group"]) not in DEBUT_AGE_GROUPS:
                    continue
                seen.add(rid)
                out.append(dict(r))
            return out
        finally:
            conn.close()

    def _cat_priors_loo(
        self,
        races: list[dict[str, Any]],
        fmap: dict[str, dict[str, dict[int, Any]]],
        holdout_idx: int,
        feature_id: str,
    ) -> dict[str, float]:
        wins: Counter[str] = Counter()
        apps: Counter[str] = Counter()
        for i, race in enumerate(races):
            if i == holdout_idx:
                continue
            snap = str(race["snapshot_id"])
            winner = int(race["winner_horse_number"])
            vals = (fmap.get(snap) or {}).get(feature_id) or {}
            for hn, val in vals.items():
                if val is None:
                    continue
                key = str(val).strip()
                if not key or key in {"-", "null", "None"}:
                    continue
                apps[key] += 1
                if int(hn) == winner:
                    wins[key] += 1
        out: dict[str, float] = {}
        for k, n in apps.items():
            out[k] = (wins.get(k, 0) + 1.0) / (n + 2.0)
        return out

    def _parse_result(self, result_json: str | None) -> dict[str, Any]:
        try:
            payload = json.loads(result_json or "{}")
        except Exception:
            payload = {}
        finish = payload.get("finish_order") or payload.get("chakujun") or []
        payouts = payload.get("payouts") or payload.get("haraimodoshi") or {}
        win_pay = payouts.get("単勝") or {}
        # normalize keys to int-able
        win_map: dict[int, float] = {}
        if isinstance(win_pay, dict):
            for k, v in win_pay.items():
                try:
                    win_map[int(k)] = float(v)
                except (TypeError, ValueError):
                    continue
        finish_list: list[int] = []
        for x in finish:
            try:
                finish_list.append(int(x))
            except (TypeError, ValueError):
                continue
        return {"finish_order": finish_list, "win_payout": win_map}

    def _build_horse_rows(
        self, races: list[dict[str, Any]], fmap: dict[str, dict[str, dict[int, Any]]]
    ) -> list[dict[str, Any]]:
        horse_rows: list[dict[str, Any]] = []
        for idx, race in enumerate(races):
            bundle = {}
            try:
                bundle = json.loads(race.get("bundle_json") or "{}")
            except Exception:
                bundle = {}
            runners = extract_runners(bundle)
            if not runners:
                continue
            winner = int(race["winner_horse_number"])
            g = tie_group(runners)
            g_hns = {int(r.get("horse_number") or 0) for r in g}
            base_strict = strict_hit(runners, winner)
            result = self._parse_result(race.get("result_json"))
            finish = result["finish_order"]
            finish_rank = {hn: i + 1 for i, hn in enumerate(finish)}
            snap = str(race["snapshot_id"])
            feat_maps = fmap.get(snap) or {}

            # race-level oikiri times
            ot_vals: list[float] = []
            for r in runners:
                hn = int(r.get("horse_number") or 0)
                raw = (feat_maps.get("oikiri_time") or {}).get(hn)
                try:
                    ot_vals.append(float(raw))
                except (TypeError, ValueError):
                    pass

            cat_priors = {
                fid: self._cat_priors_loo(races, fmap, idx, fid)
                for fid in ("trainer", "sire", "damsire", "breeder", "owner")
            }

            for r in runners:
                hn = int(r.get("horse_number") or 0)
                values = {
                    fid: (feat_maps.get(fid) or {}).get(hn) for fid in self.features
                }
                bins = discretize_horse(
                    values=values, cat_priors=cat_priors, race_oikiri_times=ot_vals
                )
                fr = finish_rank.get(hn)
                horse_rows.append(
                    {
                        "race_id": race["race_id"],
                        "age_group": race.get("age_group"),
                        "horse_number": hn,
                        "is_winner": int(hn == winner),
                        "is_place": int(fr is not None and fr <= 2),
                        "finish_rank": fr,
                        "in_tie_group": int(hn in g_hns and len(g) >= 2),
                        "tie_size": len(g),
                        "baseline_strict": base_strict,
                        "win_payout": result["win_payout"].get(hn),
                        "bins": bins,
                        "values": values,
                        "runners": runners,
                        "tie_group": g,
                        "winner": winner,
                        "race_idx": idx,
                        "cat_priors": cat_priors,
                        "feat_maps": feat_maps,
                    }
                )
        return horse_rows

    def _eval_archetype(
        self, horse_rows: list[dict[str, Any]], arch: dict[str, Any]
    ) -> dict[str, Any]:
        rules = arch["rules"]
        matched = [h for h in horse_rows if _matches_rules(h["bins"], rules)]
        n = len(matched)
        wins = sum(h["is_winner"] for h in matched)
        places = sum(h["is_place"] for h in matched)
        in_tie = sum(h["in_tie_group"] for h in matched)

        # Race-level pick: if multiple matches in a race, pick by market (pop then odds)
        by_race: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for h in matched:
            by_race[str(h["race_id"])].append(h)

        stakes = 0
        returns = 0.0
        strict_hits = 0
        soft_hits = 0
        races_picked = 0
        ig_sum = 0.0
        ig_n = 0
        resolved_tie = 0
        tie_races_touched = 0

        for race_id, horses in by_race.items():
            races_picked += 1
            # choose unique archetype representative
            def sort_key(h: dict[str, Any]) -> tuple:
                try:
                    pop = float(h["values"].get("popularity") or 999)
                except (TypeError, ValueError):
                    pop = 999
                try:
                    odds = float(h["values"].get("win_odds") or 9999)
                except (TypeError, ValueError):
                    odds = 9999
                return (pop, odds, h["horse_number"])

            pick_h = sorted(horses, key=sort_key)[0]
            pick = int(pick_h["horse_number"])
            winner = int(pick_h["winner"])
            runners = pick_h["runners"]
            g = pick_h["tie_group"]

            stakes += 100
            if pick == winner:
                strict_hits += 1
                pay = pick_h.get("win_payout")
                if pay is None:
                    try:
                        pay = float(pick_h["values"].get("win_odds") or 0) * 100
                    except (TypeError, ValueError):
                        pay = 0
                returns += float(pay)
            g_hns = {int(x.get("horse_number") or 0) for x in g}
            if pick == winner or (len(g) >= 2 and pick in g_hns and winner in g_hns):
                soft_hits += 1

            if len(g) >= 2:
                tie_races_touched += 1
                # archetype members inside G
                g_match = [
                    h
                    for h in horses
                    if h["horse_number"]
                    in {int(x.get("horse_number") or 0) for x in g}
                ]
                if len(g_match) == 1:
                    resolved_tie += 1
                    ig = _ig_bits(len(g), True)
                    ig_sum += ig
                    ig_n += 1
                elif len(g_match) > 1:
                    ig_sum += _ig_bits(len(g), False, remaining=len(g_match))
                    ig_n += 1

        roi = _safe_div(returns - stakes, stakes) if stakes else None
        return {
            "id": arch["id"],
            "label": arch.get("label") or arch["id"],
            "rules": rules,
            "source": arch.get("source", "hypothesis"),
            "n_horses": n,
            "n_races": len(by_race),
            "wins": wins,
            "places": places,
            "win_rate": _safe_div(wins, n),
            "place_rate": _safe_div(places, n),
            "tie_horse_rate": _safe_div(in_tie, n),
            "tie_races_touched": tie_races_touched,
            "tie_unique_resolve_rate": _safe_div(resolved_tie, tie_races_touched),
            "strict_hits": strict_hits,
            "soft_hits": soft_hits,
            "strict_rate": _safe_div(strict_hits, races_picked),
            "soft_rate": _safe_div(soft_hits, races_picked),
            "roi": roi,
            "stakes": stakes,
            "returns": returns,
            "avg_ig": _safe_div(ig_sum, ig_n) if ig_n else None,
            "ig_n": ig_n,
        }

    def _mine_combinations(
        self, horse_rows: list[dict[str, Any]], *, k: int, top_n: int = 20
    ) -> list[dict[str, Any]]:
        """Mine frequent winning bin combinations of size k among winners."""
        winners = [h for h in horse_rows if h["is_winner"]]
        # candidate feature dims for mining (avoid ultra-sparse miss-only)
        dims = [
            "popularity",
            "win_odds",
            "oikiri_rating",
            "oikiri_time",
            "sale_price",
            "trainer",
            "sire",
            "damsire",
            "breeder",
            "owner",
        ]
        combo_wins: Counter[tuple[tuple[str, str], ...]] = Counter()
        combo_apps: Counter[tuple[tuple[str, str], ...]] = Counter()

        for h in horse_rows:
            bins = h["bins"]
            items = [(d, bins.get(d, "NA")) for d in dims]
            for comb in itertools.combinations(items, k):
                # skip if any MISS-heavy for ordinal workout/sale unless intentional
                key = tuple(sorted(comb))
                combo_apps[key] += 1
                if h["is_winner"]:
                    combo_wins[key] += 1

        scored = []
        for key, apps in combo_apps.items():
            w = combo_wins.get(key, 0)
            if w < 2 and apps < 3:
                continue
            wr = w / apps if apps else 0.0
            # lift vs base win rate ~ 1/field; use empirical winner rate among all horses
            base = _safe_div(len(winners), len(horse_rows)) or 0.0
            lift = wr / base if base > 0 else 0.0
            scored.append((lift, wr, w, apps, key))
        scored.sort(key=lambda x: (-x[0], -x[1], -x[2], -x[3]))

        out = []
        for lift, wr, w, apps, key in scored[:top_n]:
            rules = {fid: val for fid, val in key}
            out.append(
                {
                    "id": f"mined_k{k}_" + "_".join(f"{a}-{b}" for a, b in key)[:80],
                    "label": " + ".join(f"{a}={b}" for a, b in key),
                    "rules": rules,
                    "source": f"mined_{k}way",
                    "mine_wins": w,
                    "mine_apps": apps,
                    "mine_win_rate": wr,
                    "mine_lift": lift,
                }
            )
        return out

    def analyze(self) -> dict[str, Any]:
        all_young = self.load_young_corpus(debut_only=False)
        debut = self.load_young_corpus(debut_only=True)
        # Primary: all young with evidence; also report debut slice metrics
        races = all_young
        snap_ids = [str(r["snapshot_id"]) for r in races]
        fmap = self.analyzer.load_feature_map(snap_ids)
        horse_rows = self._build_horse_rows(races, fmap)

        debut_ids = {str(r["race_id"]) for r in debut}
        debut_horses = [h for h in horse_rows if str(h["race_id"]) in debut_ids]

        mined2 = self._mine_combinations(horse_rows, k=2, top_n=15)
        mined3 = self._mine_combinations(horse_rows, k=3, top_n=15)

        archetypes = list(HYPOTHESIS_ARCHETYPES) + mined2 + mined3
        # de-dupe by rules signature
        seen_rules: set[str] = set()
        uniq_arch: list[dict[str, Any]] = []
        for a in archetypes:
            sig = json.dumps(a["rules"], ensure_ascii=False, sort_keys=True)
            if sig in seen_rules:
                continue
            seen_rules.add(sig)
            uniq_arch.append(a)

        evaluated = [self._eval_archetype(horse_rows, a) for a in uniq_arch]
        evaluated = [e for e in evaluated if e["n_horses"] > 0]
        for e in evaluated:
            # stability-aware research score (NOT product Young Horse Score)
            n = max(e["n_horses"], 1)
            wr = e.get("win_rate") or 0.0
            pr = e.get("place_rate") or 0.0
            roi = e.get("roi") if e.get("roi") is not None else -1.0
            # shrink extreme win rates when N is tiny
            wr_adj = (wr * n + 0.08 * 8) / (n + 8)  # toward ~base field win
            e["stability_n"] = n
            e["research_rank_score"] = round(
                0.45 * wr_adj
                + 0.25 * pr
                + 0.20 * max(min(roi, 2.0), -1.0) / 2.0
                + 0.10 * min(n / 20.0, 1.0),
                6,
            )
        evaluated.sort(
            key=lambda e: (
                -(e.get("research_rank_score") or 0.0),
                -(e.get("n_horses") or 0),
                -(e.get("win_rate") or 0.0),
            )
        )
        for i, e in enumerate(evaluated, start=1):
            e["rank"] = i
            e["overfit_risk"] = e["n_horses"] < 5 or e["n_races"] < 3

        # primary ranking view: prefer more stable rows first in docs top
        stable = [e for e in evaluated if not e["overfit_risk"]]
        risky = [e for e in evaluated if e["overfit_risk"]]
        ranked_view = stable + risky
        for i, e in enumerate(ranked_view, start=1):
            e["rank"] = i
        evaluated = ranked_view

        debut_eval = [
            self._eval_archetype(debut_horses, a)
            for a in uniq_arch
            if any(_matches_rules(h["bins"], a["rules"]) for h in debut_horses)
        ]
        debut_eval = [e for e in debut_eval if e["n_horses"] > 0]
        debut_eval.sort(key=lambda e: (-(e.get("win_rate") or 0), -e["n_horses"]))

        # Interaction tables (2-way / 3-way mined already); also evaluate top interactions
        interactions_2 = [e for e in evaluated if e.get("source") == "mined_2way"][:20]
        interactions_3 = [e for e in evaluated if e.get("source") == "mined_3way"][:20]

        n_races = len({h["race_id"] for h in horse_rows})
        n_horses = len(horse_rows)
        base_wr = _safe_div(sum(h["is_winner"] for h in horse_rows), n_horses)

        report = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "shadow_only": True,
            "young_horse_score": "NOT_CREATED",
            "prediction_mutation": "FORBIDDEN",
            "resolver_mutation": "FORBIDDEN",
            "sample": {
                "young_races": n_races,
                "young_horses": n_horses,
                "debut_races": len(debut_ids),
                "debut_horses": len(debut_horses),
                "base_horse_win_rate": base_wr,
                "exploratory": n_races < 100,
                "by_age": dict(Counter(str(r.get("age_group")) for r in races)),
            },
            "features": list(self.features),
            "archetypes": evaluated,
            "debut_archetypes": debut_eval[:20],
            "interactions_2way": interactions_2,
            "interactions_3way": interactions_3,
            "ranking": [
                {
                    "rank": e["rank"],
                    "id": e["id"],
                    "label": e["label"],
                    "source": e.get("source"),
                    "n_horses": e["n_horses"],
                    "n_races": e["n_races"],
                    "win_rate": e["win_rate"],
                    "place_rate": e["place_rate"],
                    "tie_horse_rate": e["tie_horse_rate"],
                    "strict_rate": e["strict_rate"],
                    "soft_rate": e["soft_rate"],
                    "roi": e["roi"],
                    "avg_ig": e["avg_ig"],
                    "research_rank_score": e.get("research_rank_score"),
                    "overfit_risk": e.get("overfit_risk"),
                }
                for e in evaluated[:30]
            ],
        }
        return report


def write_archetypes_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    s = report.get("sample") or {}
    lines = [
        "# Version13 Research - Young Horse Archetypes",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Scope:** Research only / No Young Horse Score / Prediction+Resolver FORBIDDEN  ",
        "",
        "## Sample",
        "",
        f"- Young races: `{s.get('young_races')}` / horses: `{s.get('young_horses')}`",
        f"- Debut (2yo_newcomer) races: `{s.get('debut_races')}` / horses: `{s.get('debut_horses')}`",
        f"- Base horse win rate: `{_pct(s.get('base_horse_win_rate'))}`",
        f"- Exploratory: `{s.get('exploratory')}`",
        "",
        "### Age",
        "",
        "| Age | Count |",
        "|-----|------:|",
    ]
    for k, v in (s.get("by_age") or {}).items():
        lines.append(f"| `{k}` | {v} |")
    lines.extend(
        [
            "",
            "## Archetypes",
            "",
            "| Rank | Archetype | N | Races | Win | Place | TieHorse | Strict | Soft | ROI | IG | Risk |",
            "|-----:|-----------|--:|------:|----:|------:|---------:|-------:|-----:|----:|---:|:----:|",
        ]
    )
    for e in (report.get("archetypes") or [])[:25]:
        risk = "HIGH" if e.get("overfit_risk") else "ok"
        lines.append(
            f"| {e.get('rank')} | `{e.get('label')}` | {e.get('n_horses')} | {e.get('n_races')} | "
            f"{_pct(e.get('win_rate'))} | {_pct(e.get('place_rate'))} | {_pct(e.get('tie_horse_rate'))} | "
            f"{_pct(e.get('strict_rate'))} | {_pct(e.get('soft_rate'))} | "
            f"{_pct(e.get('roi')) if e.get('roi') is not None else 'N/A'} | "
            f"{e.get('avg_ig') if e.get('avg_ig') is not None else 'N/A'} | {risk} |"
        )
    lines.extend(
        [
            "",
            "## Debut-only (2yo_newcomer)",
            "",
            "| Archetype | N | Win | Place | Strict | Soft | ROI |",
            "|-----------|--:|----:|------:|-------:|-----:|----:|",
        ]
    )
    for e in (report.get("debut_archetypes") or [])[:15]:
        lines.append(
            f"| `{e.get('label')}` | {e.get('n_horses')} | {_pct(e.get('win_rate'))} | "
            f"{_pct(e.get('place_rate'))} | {_pct(e.get('strict_rate'))} | {_pct(e.get('soft_rate'))} | "
            f"{_pct(e.get('roi')) if e.get('roi') is not None else 'N/A'} |"
        )
    lines.extend(
        [
            "",
            "## Definitions",
            "",
            "- **Win/Place**: among horses matching the archetype bins",
            "- **Place**: finish_order rank <= 2 (連対)",
            "- **Strict/Soft/ROI/IG**: race-level pick = best matching horse by popularity then odds; ROI uses 単勝 payout (100yen flat)",
            "- Categorical STRONG/MID/WEAK from leave-one-out Laplace prior",
            "",
            "## Decision",
            "",
            "```",
            "Action Type: Young Horse Archetype Research",
            "Young Horse Score: NOT CREATED",
            "Prediction Mutation: FORBIDDEN",
            "Resolver Mutation: FORBIDDEN",
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_ranking_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Version13 Research - Young Horse Archetype Ranking",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**IMPORTANT:** Research ordering only. No product score.  ",
        "",
        "| Rank | ID | Label | Source | N | Win | Place | Strict | Soft | ROI | IG | Risk |",
        "|-----:|----|-------|--------|--:|----:|------:|-------:|-----:|----:|---:|:----:|",
    ]
    for e in report.get("ranking") or []:
        risk = "HIGH" if e.get("overfit_risk") else "ok"
        lines.append(
            f"| {e.get('rank')} | `{e.get('id')}` | `{e.get('label')}` | `{e.get('source')}` | "
            f"{e.get('n_horses')} | {_pct(e.get('win_rate'))} | {_pct(e.get('place_rate'))} | "
            f"{_pct(e.get('strict_rate'))} | {_pct(e.get('soft_rate'))} | "
            f"{_pct(e.get('roi')) if e.get('roi') is not None else 'N/A'} | "
            f"{e.get('avg_ig') if e.get('avg_ig') is not None else 'N/A'} | {risk} |"
        )
    lines.extend(
        [
            "",
            "Sorted by stability-adjusted research score (not a product score).",
            "Risk=HIGH when N_horses<5 or N_races<3 (treat as anecdote).",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_interactions_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Version13 Research - Young Horse Archetype Interactions",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Scope:** 2-feature and 3-feature mined combinations  ",
        "",
        "## 2-feature interactions",
        "",
        "| Combo | N | Win | Place | Strict | Soft | ROI | Lift(mine) |",
        "|-------|--:|----:|------:|-------:|-----:|----:|-----------:|",
    ]
    for e in report.get("interactions_2way") or []:
        lines.append(
            f"| `{e.get('label')}` | {e.get('n_horses')} | {_pct(e.get('win_rate'))} | "
            f"{_pct(e.get('place_rate'))} | {_pct(e.get('strict_rate'))} | {_pct(e.get('soft_rate'))} | "
            f"{_pct(e.get('roi')) if e.get('roi') is not None else 'N/A'} | "
            f"{(e.get('rules') and '') or ''} |"
        )
    # fix lift column - use mine fields if present on original; evaluated may not have mine_lift
    # Rebuild from interactions list properly
    lines = [
        "# Version13 Research - Young Horse Archetype Interactions",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Scope:** 2-feature and 3-feature mined combinations  ",
        "",
        "## 2-feature interactions",
        "",
        "| Combo | N | Races | Win | Place | Strict | Soft | ROI | IG |",
        "|-------|--:|------:|----:|------:|-------:|-----:|----:|---:|",
    ]
    for e in report.get("interactions_2way") or []:
        lines.append(
            f"| `{e.get('label')}` | {e.get('n_horses')} | {e.get('n_races')} | "
            f"{_pct(e.get('win_rate'))} | {_pct(e.get('place_rate'))} | "
            f"{_pct(e.get('strict_rate'))} | {_pct(e.get('soft_rate'))} | "
            f"{_pct(e.get('roi')) if e.get('roi') is not None else 'N/A'} | "
            f"{e.get('avg_ig') if e.get('avg_ig') is not None else 'N/A'} |"
        )
    lines.extend(
        [
            "",
            "## 3-feature interactions",
            "",
            "| Combo | N | Races | Win | Place | Strict | Soft | ROI | IG |",
            "|-------|--:|------:|----:|------:|-------:|-----:|----:|---:|",
        ]
    )
    for e in report.get("interactions_3way") or []:
        lines.append(
            f"| `{e.get('label')}` | {e.get('n_horses')} | {e.get('n_races')} | "
            f"{_pct(e.get('win_rate'))} | {_pct(e.get('place_rate'))} | "
            f"{_pct(e.get('strict_rate'))} | {_pct(e.get('soft_rate'))} | "
            f"{_pct(e.get('roi')) if e.get('roi') is not None else 'N/A'} | "
            f"{e.get('avg_ig') if e.get('avg_ig') is not None else 'N/A'} |"
        )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "- Combinations mined from discretized bins among all young horses.",
            "- Evaluated metrics are out-of-sample style only via LOO priors for categoricals;",
            "  combination selection itself is exploratory and can overfit at low N.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write() -> dict[str, Any]:
    report = YoungHorseArchetypeResearch().analyze()
    root = repo_root()
    docs = root / "docs" / "research"
    write_archetypes_md(report, docs / "v13-younghorse-archetypes.md")
    write_ranking_md(report, docs / "v13-archetype-ranking.md")
    write_interactions_md(report, docs / "v13-archetype-interactions.md")
    json_path = evidence_root() / "reports" / "v13-younghorse-archetypes.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {
        "archetypes": str(docs / "v13-younghorse-archetypes.md"),
        "ranking": str(docs / "v13-archetype-ranking.md"),
        "interactions": str(docs / "v13-archetype-interactions.md"),
        "json": str(json_path),
    }
    return report
