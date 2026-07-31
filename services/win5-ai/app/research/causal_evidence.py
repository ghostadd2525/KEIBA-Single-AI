# -*- coding: utf-8 -*-
"""
Version21 Causal Evidence Research

Study *why* / *under what conditions* features associate with outcomes.
Not predictive productization.

FORBIDDEN to mutate:
  Prediction / PE / CE / AI / Resolver / Challenge /
  ResultAutomation / Production
"""
from __future__ import annotations

import itertools
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .analyzer import extract_runners, soft_hit, strict_hit, tie_group, unique_top_pick
from .config import evidence_root, repo_root
from .evidence_discovery import (
    CONFIDENT_MIN_N,
    FEATURE_LABELS,
    HORSE_FEATURES,
    EvidenceDiscoveryResearch,
    classify_gate,
    research_category,
    wilson_ci,
)
from .knowledge_base import _load_json
from .ranking_engine import CATEGORICAL_FEATURES, feature_score, resolve_by_score
from .young_horse_archetypes import discretize_horse
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-causal-evidence/1.0"

# Causal focal features (horse-level)
FOCAL_FEATURES: tuple[str, ...] = (
    "popularity",
    "win_odds",
    "trainer",
    "sire",
    "damsire",
    "breeder",
    "owner",
    "oikiri_rating",
)

# Condition axes (race / segment context)
CONDITION_AXES: tuple[str, ...] = (
    "surface",
    "distance_bucket",
    "going",
    "weather",
    "venue",
    "field_bucket",
    "category",
    "debut",  # derived: 2yo_newcomer vs other
)

# Preset Feature → Condition → Outcome chains (research hypotheses)
PRESET_CHAINS: tuple[dict[str, Any], ...] = (
    {"feature": "popularity", "condition": "surface", "outcome": "hit"},
    {"feature": "popularity", "condition": "distance_bucket", "outcome": "hit"},
    {"feature": "popularity", "condition": "going", "outcome": "roi"},
    {"feature": "trainer", "condition": "category", "outcome": "hit"},
    {"feature": "sire", "condition": "debut", "outcome": "hit"},
    {"feature": "win_odds", "condition": "surface", "outcome": "hit"},
    {"feature": "sire", "condition": "surface", "outcome": "hit"},
    {"feature": "trainer", "condition": "going", "outcome": "hit"},
    {"feature": "oikiri_rating", "condition": "debut", "outcome": "hit"},
    {"feature": "popularity", "condition": "field_bucket", "outcome": "soft"},
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _is_debut(category: str, age_group: str | None = None) -> str:
    if category == "2yo_newcomer" or age_group == "2yo_newcomer":
        return "debut"
    return "non_debut"


class CausalEvidenceResearch:
    def __init__(self) -> None:
        migrate()
        self.discovery = EvidenceDiscoveryResearch()
        self.root = repo_root()
        self.evidence = evidence_root()

    def _load_reliability(self) -> dict[str, float]:
        data = _load_json(self.evidence / "reports" / "v14-evidence-reliability.json")
        return {
            str(f.get("feature_id")): float(f.get("reliability_score") or 50.0)
            for f in data.get("features") or []
            if f.get("feature_id")
        }

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
            snap = str(race.get("snapshot_id") or "")
            if not snap:
                continue
            winner = int(race["winner"])
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
        out = {}
        for k, a in apps.items():
            out[k] = (wins.get(k, 0) + 1.0) / (a + 2.0)
        return out

    def _pick_by_feature(
        self,
        *,
        feature_id: str,
        runners: list[dict[str, Any]],
        values: dict[int, Any],
        cat_prior: dict[str, float] | None,
    ) -> int | None:
        scores = {
            int(r.get("horse_number") or 0): feature_score(
                feature_id,
                values.get(int(r.get("horse_number") or 0)),
                cat_prior=cat_prior,
            )
            for r in runners
        }
        pick, status = resolve_by_score(runners, scores)
        return pick if status == "resolved" else None

    def _condition_value(self, race: dict[str, Any], axis: str) -> str:
        if axis == "debut":
            return _is_debut(str(race.get("category") or ""), race.get("age_group"))
        val = race.get(axis)
        s = str(val if val is not None else "unknown")
        if s in {"", "None", "null"}:
            return "unknown"
        return s

    def _roi_unit(self, hit: bool) -> tuple[float, float]:
        """100yen stake; hit → illustrative 250yen return."""
        stake = 100.0
        ret = 250.0 if hit else 0.0
        return stake, ret

    def analyze_feature_condition_effects(
        self,
        races: list[dict[str, Any]],
        fmap: dict[str, dict[str, dict[int, Any]]],
        reliability_map: dict[str, float],
    ) -> dict[str, Any]:
        evidence = [r for r in races if r.get("has_snapshot")]
        # Global baseline: prediction strict / feature-unconditional
        global_pred_strict = _safe_div(
            sum(int(r.get("strict") or 0) for r in evidence), len(evidence)
        ) or 0.0

        # Unconditional feature effect (field-best)
        unconditional: dict[str, dict[str, Any]] = {}
        for fid in FOCAL_FEATURES:
            hits = 0
            softs = 0
            resolved = 0
            stakes = 0.0
            returns = 0.0
            for idx, race in enumerate(evidence):
                snap = str(race["snapshot_id"])
                values = (fmap.get(snap) or {}).get(fid) or {}
                cat_prior = (
                    self._cat_priors_loo(evidence, fmap, idx, fid)
                    if fid in CATEGORICAL_FEATURES
                    else None
                )
                pick = self._pick_by_feature(
                    feature_id=fid,
                    runners=race["runners"],
                    values=values,
                    cat_prior=cat_prior,
                )
                if pick is None:
                    continue
                resolved += 1
                winner = int(race["winner"])
                hit = pick == winner
                g = {int(x.get("horse_number") or 0) for x in tie_group(race["runners"])}
                soft = hit or (pick in g and winner in g)
                if hit:
                    hits += 1
                if soft:
                    softs += 1
                st, rt = self._roi_unit(hit)
                stakes += st
                returns += rt
            rate = _safe_div(hits, resolved)
            soft_rate = _safe_div(softs, resolved)
            roi = _safe_div(returns - stakes, stakes) if stakes else None
            lo, hi = wilson_ci(hits, resolved) if resolved else (0.0, 1.0)
            gate = classify_gate(
                n=resolved, successes=hits, baseline=global_pred_strict
            )
            unconditional[fid] = {
                "feature": fid,
                "label": FEATURE_LABELS.get(fid, fid),
                "n": resolved,
                "hit": hits,
                "hit_rate": rate,
                "soft_rate": soft_rate,
                "roi": roi,
                "wilson_ci": {"low": round(lo, 4), "high": round(hi, 4)},
                "reliability": reliability_map.get(fid),
                "confidence": "High"
                if gate.get("confident")
                else ("Medium" if resolved >= 10 else "Exploratory"),
                "gate": gate,
                "effect_vs_baseline": round((rate or 0) - global_pred_strict, 4)
                if rate is not None
                else None,
            }

        # Conditional effects: Feature × Condition → Outcome
        condition_effects: list[dict[str, Any]] = []
        for fid in FOCAL_FEATURES:
            base = unconditional.get(fid) or {}
            base_rate = base.get("hit_rate")
            for axis in CONDITION_AXES:
                buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
                for idx, race in enumerate(evidence):
                    cond = self._condition_value(race, axis)
                    if cond == "unknown":
                        continue
                    snap = str(race["snapshot_id"])
                    values = (fmap.get(snap) or {}).get(fid) or {}
                    cat_prior = (
                        self._cat_priors_loo(evidence, fmap, idx, fid)
                        if fid in CATEGORICAL_FEATURES
                        else None
                    )
                    pick = self._pick_by_feature(
                        feature_id=fid,
                        runners=race["runners"],
                        values=values,
                        cat_prior=cat_prior,
                    )
                    if pick is None:
                        continue
                    winner = int(race["winner"])
                    hit = pick == winner
                    g = {
                        int(x.get("horse_number") or 0)
                        for x in tie_group(race["runners"])
                    }
                    soft = hit or (pick in g and winner in g)
                    st, rt = self._roi_unit(hit)
                    buckets[cond].append(
                        {
                            "hit": int(hit),
                            "soft": int(soft),
                            "stake": st,
                            "ret": rt,
                        }
                    )
                for cond, items in buckets.items():
                    n = len(items)
                    hits = sum(x["hit"] for x in items)
                    softs = sum(x["soft"] for x in items)
                    stakes = sum(x["stake"] for x in items)
                    returns = sum(x["ret"] for x in items)
                    rate = _safe_div(hits, n)
                    soft_rate = _safe_div(softs, n)
                    roi = _safe_div(returns - stakes, stakes) if stakes else None
                    lo, hi = wilson_ci(hits, n) if n else (0.0, 1.0)
                    # Feature Effect under condition = conditional − unconditional
                    effect = (
                        round((rate or 0) - (base_rate or 0), 4)
                        if rate is not None and base_rate is not None
                        else None
                    )
                    effect_vs_global = (
                        round((rate or 0) - global_pred_strict, 4)
                        if rate is not None
                        else None
                    )
                    gate = classify_gate(
                        n=n, successes=hits, baseline=base_rate or global_pred_strict
                    )
                    condition_effects.append(
                        {
                            "feature": fid,
                            "feature_label": FEATURE_LABELS.get(fid, fid),
                            "condition_axis": axis,
                            "condition_value": cond,
                            "chain": f"{FEATURE_LABELS.get(fid, fid)} → {axis}={cond} → Outcome",
                            "n": n,
                            "hit": hits,
                            "hit_rate": rate,
                            "soft_rate": soft_rate,
                            "roi": roi,
                            "wilson_ci": {"low": round(lo, 4), "high": round(hi, 4)},
                            "reliability": reliability_map.get(fid),
                            "confidence": "High"
                            if gate.get("confident")
                            else ("Medium" if n >= 10 else "Exploratory"),
                            "feature_effect": effect,
                            "effect_vs_global_baseline": effect_vs_global,
                            "unconditional_hit_rate": base_rate,
                            "gate": gate,
                            "exploratory": not gate.get("confident"),
                        }
                    )

        condition_effects.sort(
            key=lambda x: (
                -int(not x.get("exploratory")),
                -abs(x.get("feature_effect") or 0),
                -int(x.get("n") or 0),
            )
        )
        return {
            "global_pred_strict": global_pred_strict,
            "evidence_n": len(evidence),
            "unconditional": unconditional,
            "condition_effects": condition_effects,
        }

    def analyze_preset_chains(
        self,
        condition_effects: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        out = []
        idx = {
            (e["feature"], e["condition_axis"], e["condition_value"]): e
            for e in condition_effects
        }
        by_feature_axis: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for e in condition_effects:
            by_feature_axis[(e["feature"], e["condition_axis"])].append(e)

        for preset in PRESET_CHAINS:
            fid = preset["feature"]
            axis = preset["condition"]
            outcome = preset["outcome"]
            rows = by_feature_axis.get((fid, axis)) or []
            # summarize best/worst condition for this chain
            if outcome == "roi":
                ranked = sorted(
                    [r for r in rows if r.get("roi") is not None],
                    key=lambda x: -(x.get("roi") or -999),
                )
            elif outcome == "soft":
                ranked = sorted(rows, key=lambda x: -(x.get("soft_rate") or 0))
            else:
                ranked = sorted(rows, key=lambda x: -(x.get("hit_rate") or 0))
            out.append(
                {
                    "preset": f"{FEATURE_LABELS.get(fid, fid)} → {axis} → {outcome.upper()}",
                    "feature": fid,
                    "condition_axis": axis,
                    "outcome": outcome,
                    "n_condition_bins": len(rows),
                    "best": ranked[0] if ranked else None,
                    "worst": ranked[-1] if ranked else None,
                    "bins": ranked[:8],
                }
            )
        return out

    def analyze_interactions(
        self,
        races: list[dict[str, Any]],
        fmap: dict[str, dict[str, dict[int, Any]]],
        reliability_map: dict[str, float],
        *,
        max_k: int = 4,
    ) -> dict[str, Any]:
        """3–4 way Feature×Condition patterns via discretized bins + race axes."""
        evidence = [r for r in races if r.get("has_snapshot")]
        mean_field = sum(len(r["runners"]) for r in evidence) / max(len(evidence), 1)
        baseline = 1.0 / max(mean_field, 2.0)

        # Build horse-level rows with bins + race conditions
        horse_rows: list[dict[str, Any]] = []
        for idx, race in enumerate(evidence):
            snap = str(race["snapshot_id"])
            feat_maps = fmap.get(snap) or {}
            cat_priors = {
                fid: self._cat_priors_loo(evidence, fmap, idx, fid)
                for fid in FOCAL_FEATURES
                if fid in CATEGORICAL_FEATURES
            }
            oikiri_times = []
            for v in (feat_maps.get("oikiri_time") or {}).values():
                try:
                    oikiri_times.append(float(v))
                except (TypeError, ValueError):
                    pass
            for r in race["runners"]:
                hn = int(r.get("horse_number") or 0)
                values = {
                    fid: (feat_maps.get(fid) or {}).get(hn) for fid in HORSE_FEATURES
                }
                bins = discretize_horse(
                    values=values,
                    cat_priors=cat_priors,
                    race_oikiri_times=oikiri_times,
                )
                bins["surface"] = race.get("surface") or "unknown"
                bins["distance_bucket"] = race.get("distance_bucket") or "unknown"
                bins["going"] = race.get("going") or "unknown"
                bins["category"] = race.get("category") or "unknown"
                bins["debut"] = _is_debut(str(race.get("category") or ""))
                bins["field_bucket"] = race.get("field_bucket") or "unknown"
                is_win = hn == race["winner"]
                # soft approx: top-group — use win for interaction mining primarily
                horse_rows.append({"bins": bins, "win": int(is_win), "race_id": race["race_id"]})

        # Candidate interaction keys
        keys_3 = [
            ("popularity", "surface", "distance_bucket"),
            ("popularity", "going", "surface"),
            ("popularity", "sire", "debut"),
            ("popularity", "trainer", "category"),
            ("sire", "debut", "surface"),
            ("trainer", "category", "going"),
            ("popularity", "field_bucket", "surface"),
            ("win_odds", "surface", "distance_bucket"),
            ("oikiri_rating", "debut", "surface"),
        ]
        keys_4 = [
            ("popularity", "sire", "surface", "distance_bucket"),
            ("popularity", "trainer", "category", "going"),
            ("popularity", "sire", "debut", "surface"),
            ("win_odds", "trainer", "surface", "field_bucket"),
            ("popularity", "oikiri_rating", "debut", "going"),
        ]

        def _mine(key_sets: list[tuple[str, ...]], kind: str) -> list[dict[str, Any]]:
            counter: Counter[str] = Counter()
            win_counter: Counter[str] = Counter()
            for row in horse_rows:
                bins = row["bins"]
                for keys in key_sets:
                    vals = []
                    skip = False
                    for k in keys:
                        v = bins.get(k)
                        if not v or "MISS" in str(v) or v == "unknown":
                            skip = True
                            break
                        vals.append(f"{k}={v}")
                    if skip:
                        continue
                    pat = "|".join(vals)
                    counter[pat] += 1
                    if row["win"]:
                        win_counter[pat] += 1
            rows = []
            for pat, n in counter.most_common(60):
                w = win_counter.get(pat, 0)
                rate = _safe_div(w, n)
                lo, hi = wilson_ci(w, n)
                gate = classify_gate(n=n, successes=w, baseline=baseline)
                # effect vs baseline random field
                effect = round((rate or 0) - baseline, 4) if rate is not None else None
                feats = [p.split("=", 1)[0] for p in pat.split("|")]
                rels = [reliability_map[f] for f in feats if f in reliability_map]
                rows.append(
                    {
                        "kind": kind,
                        "pattern": pat,
                        "features": feats,
                        "n": n,
                        "hit": w,
                        "hit_rate": rate,
                        "soft_rate": None,
                        "roi": None,
                        "wilson_ci": {"low": round(lo, 4), "high": round(hi, 4)},
                        "reliability_mean": round(sum(rels) / len(rels), 2)
                        if rels
                        else None,
                        "confidence": "High"
                        if gate.get("confident")
                        else ("Medium" if n >= 10 else "Exploratory"),
                        "feature_effect_vs_random": effect,
                        "gate": gate,
                        "exploratory": not gate.get("confident"),
                    }
                )
            rows.sort(
                key=lambda x: (
                    -int(not x["exploratory"]),
                    -(x.get("hit_rate") or 0),
                    -x["n"],
                )
            )
            return rows

        return {
            "interactions_3way": _mine(keys_3, "3way") if max_k >= 3 else [],
            "interactions_4way": _mine(keys_4, "4way") if max_k >= 4 else [],
            "baseline_random": baseline,
            "horse_rows": len(horse_rows),
        }

    def build_context_map(
        self, condition_effects: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Feature → Condition → effect heatmap-like structure."""
        by_feature: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for e in condition_effects:
            if e.get("condition_value") == "unknown":
                continue
            by_feature[e["feature"]][e["condition_axis"]].append(
                {
                    "condition": e["condition_value"],
                    "n": e["n"],
                    "hit_rate": e["hit_rate"],
                    "feature_effect": e["feature_effect"],
                    "roi": e["roi"],
                    "confidence": e["confidence"],
                }
            )
        # top context per feature
        contexts = []
        for fid, axes in by_feature.items():
            best_pos = None
            best_neg = None
            for axis, rows in axes.items():
                for r in rows:
                    if r.get("n", 0) < 5:
                        continue
                    eff = r.get("feature_effect")
                    if eff is None:
                        continue
                    item = {"feature": fid, "axis": axis, **r}
                    if best_pos is None or eff > (best_pos.get("feature_effect") or -9):
                        best_pos = item
                    if best_neg is None or eff < (best_neg.get("feature_effect") or 9):
                        best_neg = item
            contexts.append(
                {
                    "feature": fid,
                    "label": FEATURE_LABELS.get(fid, fid),
                    "amplifies_when": best_pos,
                    "weakens_when": best_neg,
                    "axes": {
                        axis: sorted(
                            rows, key=lambda x: -abs(x.get("feature_effect") or 0)
                        )[:6]
                        for axis, rows in axes.items()
                    },
                }
            )
        contexts.sort(key=lambda x: x["feature"])
        return {"by_feature": contexts}

    def analyze(self) -> dict[str, Any]:
        races = self.discovery.load_corpus()
        evidence = [r for r in races if r.get("has_snapshot")]
        snap_ids = [str(r["snapshot_id"]) for r in evidence]
        fmap = self.discovery.analyzer.load_feature_map(snap_ids)
        reliability_map = self._load_reliability()

        effects = self.analyze_feature_condition_effects(
            races, fmap, reliability_map
        )
        presets = self.analyze_preset_chains(effects["condition_effects"])
        interactions = self.analyze_interactions(
            races, fmap, reliability_map, max_k=4
        )
        context_map = self.build_context_map(effects["condition_effects"])

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "prediction_mutation": "FORBIDDEN",
            "causal_claim": "ASSOCIATIONAL_ONLY",
            "sample": {
                "unique_races": len(races),
                "with_evidence": len(evidence),
                "exploratory": len(evidence) < 100,
                "global_pred_strict": effects.get("global_pred_strict"),
            },
            "unconditional": effects.get("unconditional"),
            "condition_effects": effects.get("condition_effects"),
            "preset_chains": presets,
            "interactions": interactions,
            "context_map": context_map,
            "notes": [
                "Feature Effect = HitRate(feature|condition) − HitRate(feature unconditional).",
                "Results are associational research findings, not causal proof.",
                "No Prediction / PE / CE / AI / Resolver changes.",
            ],
        }


def write_causal_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    s = report.get("sample") or {}
    lines = [
        "# Version21 Research - Causal Evidence",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Scope:** Feature → Condition → Outcome (associational) / Prediction FORBIDDEN  ",
        "",
        "## Sample",
        "",
        f"- Unique races: `{s.get('unique_races')}` / Evidence: `{s.get('with_evidence')}`",
        f"- Global Prediction Strict: `{_pct(s.get('global_pred_strict'))}`",
        f"- Exploratory: `{s.get('exploratory')}`",
        "",
        "## Unconditional feature effects (field-best)",
        "",
        "| Feature | N | Hit | Soft | ROI | Effect vs Pred | Reliability | Confidence |",
        "|---------|--:|----:|-----:|----:|---------------:|------------:|------------|",
    ]
    for fid, row in (report.get("unconditional") or {}).items():
        lines.append(
            f"| `{row.get('label')}` | {row.get('n')} | {_pct(row.get('hit_rate'))} | "
            f"{_pct(row.get('soft_rate'))} | "
            f"{_pct(row.get('roi')) if row.get('roi') is not None else 'N/A'} | "
            f"{row.get('effect_vs_baseline')} | {row.get('reliability')} | "
            f"{row.get('confidence')} |"
        )
    lines.extend(
        [
            "",
            "## Preset causal chains",
            "",
        ]
    )
    for p in report.get("preset_chains") or []:
        best = p.get("best") or {}
        worst = p.get("worst") or {}
        lines.extend(
            [
                f"### {p.get('preset')}",
                "",
                f"- Condition bins: `{p.get('n_condition_bins')}`",
                f"- Best: `{best.get('condition_value')}` hit={_pct(best.get('hit_rate'))} "
                f"effect={best.get('feature_effect')} n={best.get('n')} "
                f"({best.get('confidence')})",
                f"- Worst: `{worst.get('condition_value')}` hit={_pct(worst.get('hit_rate'))} "
                f"effect={worst.get('feature_effect')} n={worst.get('n')} "
                f"({worst.get('confidence')})",
                "",
            ]
        )
    lines.extend(
        [
            "## Guardrails",
            "",
            "- Associational only — not causal proof",
            "- No Prediction / PE / CE / AI / Resolver / Production changes",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_condition_effects_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Version21 Research - Condition Effects",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "Feature Effect = conditional hit rate − unconditional feature hit rate.",
        "",
        "## Top condition effects (by |effect|)",
        "",
        "| Chain | N | Hit | Soft | ROI | Effect | Conf |",
        "|-------|--:|----:|-----:|----:|-------:|------|",
    ]
    for e in (report.get("condition_effects") or [])[:40]:
        lines.append(
            f"| `{e.get('chain')}` | {e.get('n')} | {_pct(e.get('hit_rate'))} | "
            f"{_pct(e.get('soft_rate'))} | "
            f"{_pct(e.get('roi')) if e.get('roi') is not None else 'N/A'} | "
            f"{e.get('feature_effect')} | {e.get('confidence')} |"
        )
    inter = report.get("interactions") or {}
    lines.extend(
        [
            "",
            "## 3-feature interactions",
            "",
            "| Pattern | N | HitRate | Effect vs random | Conf |",
            "|---------|--:|--------:|-----------------:|------|",
        ]
    )
    for r in (inter.get("interactions_3way") or [])[:25]:
        lines.append(
            f"| `{r.get('pattern')}` | {r.get('n')} | {_pct(r.get('hit_rate'))} | "
            f"{r.get('feature_effect_vs_random')} | {r.get('confidence')} |"
        )
    lines.extend(
        [
            "",
            "## 4-feature interactions",
            "",
            "| Pattern | N | HitRate | Effect vs random | Conf |",
            "|---------|--:|--------:|-----------------:|------|",
        ]
    )
    for r in (inter.get("interactions_4way") or [])[:25]:
        lines.append(
            f"| `{r.get('pattern')}` | {r.get('n')} | {_pct(r.get('hit_rate'))} | "
            f"{r.get('feature_effect_vs_random')} | {r.get('confidence')} |"
        )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_context_map_md(report: dict[str, Any], path: Path) -> None:
    cm = report.get("context_map") or {}
    lines = [
        "# Version21 Research - Context Map",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "Where each feature amplifies or weakens (associational).",
        "",
        "```",
        "Feature → Condition → Outcome",
        "```",
        "",
    ]
    for ctx in cm.get("by_feature") or []:
        amp = ctx.get("amplifies_when") or {}
        weak = ctx.get("weakens_when") or {}
        lines.extend(
            [
                f"## {ctx.get('label')}",
                "",
                f"- **Amplifies when:** `{amp.get('axis')}={amp.get('condition')}` "
                f"(effect={amp.get('feature_effect')}, hit={_pct(amp.get('hit_rate'))}, "
                f"n={amp.get('n')})",
                f"- **Weakens when:** `{weak.get('axis')}={weak.get('condition')}` "
                f"(effect={weak.get('feature_effect')}, hit={_pct(weak.get('hit_rate'))}, "
                f"n={weak.get('n')})",
                "",
            ]
        )
        for axis, rows in (ctx.get("axes") or {}).items():
            if not rows:
                continue
            lines.append(f"### Condition axis `{axis}`")
            lines.append("")
            lines.append("| Condition | N | Hit | Effect | Conf |")
            lines.append("|-----------|--:|----:|-------:|------|")
            for r in rows:
                lines.append(
                    f"| `{r.get('condition')}` | {r.get('n')} | "
                    f"{_pct(r.get('hit_rate'))} | {r.get('feature_effect')} | "
                    f"{r.get('confidence')} |"
                )
            lines.append("")
    lines.extend(
        [
            "## Decision",
            "",
            "```",
            "Action Type: Causal Evidence Research (associational)",
            "Prediction Mutation: FORBIDDEN",
            "Use: context for Knowledge / Shadow design — not product wiring",
            "```",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write() -> dict[str, Any]:
    report = CausalEvidenceResearch().analyze()
    docs = repo_root() / "docs" / "research"
    docs.mkdir(parents=True, exist_ok=True)
    write_causal_md(report, docs / "v21-causal-evidence.md")
    write_condition_effects_md(report, docs / "v21-condition-effects.md")
    write_context_map_md(report, docs / "v21-context-map.md")
    json_path = evidence_root() / "reports" / "v21-causal-evidence.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    # trim horse_rows if any leaked
    export = dict(report)
    if "interactions" in export and isinstance(export["interactions"], dict):
        export["interactions"] = {
            k: v
            for k, v in export["interactions"].items()
            if k != "horse_rows"
        }
    json_path.write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {
        "causal": str(docs / "v21-causal-evidence.md"),
        "effects": str(docs / "v21-condition-effects.md"),
        "context": str(docs / "v21-context-map.md"),
        "json": str(json_path),
    }
    return report
