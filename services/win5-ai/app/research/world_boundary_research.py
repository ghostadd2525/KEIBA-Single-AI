# -*- coding: utf-8 -*-
"""
Version22 Existing World Boundary Research

Study whether Evidence features improve assignment fitness to
EXISTING Worlds only. No new Worlds. No product mutations.

FORBIDDEN:
  Prediction / PE / CE / AI / Challenge / Resolver /
  ResultAutomation / Production
  Creating new Worlds
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .analyzer import unique_top_pick
from .config import evidence_root, repo_root
from .evidence_discovery import (
    FEATURE_LABELS,
    HORSE_FEATURES,
    EvidenceDiscoveryResearch,
)
from .ranking_engine import CATEGORICAL_FEATURES
from .weakness_atlas import _distance_bucket, _field_bucket
from .young_horse_archetypes import discretize_horse
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-existing-world-boundary/1.0"

# Canonical existing Worlds — DO NOT EXTEND
EXISTING_WORLDS: tuple[str, ...] = (
    "core_world",
    "midupper_world",
    "midhole_world",
    "rank7_world",
    "bug_world",
    "mixed_world",
)

# Existing SubWorld labels observed / defined by classifier (not new Worlds)
EXISTING_SUBWORLDS: tuple[str, ...] = (
    "core_top",
    "core_under",
    "midupper_route",
    "midupper_spread",
    "midupper_corelike",
    "rank7_transition",
    "rank7_residual",
    "fallback_standard",
)

PROFILE_FEATURES: tuple[str, ...] = (
    "popularity",
    "win_odds",
    "trainer",
    "sire",
    "damsire",
    "breeder",
    "owner",
    "oikiri_rating",
    "surface",
    "distance_bucket",
    "going",
    "weather",
    "field_bucket",
)

LAPLACE = 0.5
AMBIGUITY_MARGIN = 0.15  # normalized score gap
MIN_N_PROFILE = 3
MIN_N_REFINE = 5


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def extract_world_label(bundle: dict[str, Any]) -> tuple[str | None, str | None]:
    """Read-only world/sub_world from Prediction Bundle evaluation."""
    if not isinstance(bundle, dict):
        return None, None
    ev = bundle.get("evaluation") if isinstance(bundle.get("evaluation"), dict) else {}
    world = ev.get("world")
    sub = ev.get("sub_world")
    if not world and isinstance(bundle.get("prediction"), dict):
        pred = bundle["prediction"]
        pev = pred.get("evaluation") if isinstance(pred.get("evaluation"), dict) else {}
        world = pev.get("world") or pred.get("world")
        sub = pev.get("sub_world") or pred.get("sub_world") or sub
    if not world and isinstance(bundle.get("world"), str):
        world = bundle.get("world")
        sub = bundle.get("sub_world") or sub
    if world is None:
        return None, None
    w = str(world)
    s = str(sub) if sub else None
    # exclude non-canonical / test labels from EXISTING analysis set
    if w not in EXISTING_WORLDS:
        return w, s  # caller may filter
    return w, s


def _entropy(probs: list[float]) -> float:
    h = 0.0
    for p in probs:
        if p > 0:
            h -= p * math.log(p + 1e-12)
    return h


def _race_dist_features(runners: list[dict[str, Any]]) -> dict[str, Any]:
    probs = []
    for r in runners:
        try:
            probs.append(max(0.0, float(r.get("win_prob") or 0.0)))
        except (TypeError, ValueError):
            continue
    if not probs:
        return {
            "top1_prob": None,
            "top2_sum": None,
            "gap12": None,
            "entropy": None,
        }
    probs = sorted(probs, reverse=True)
    s = sum(probs) or 1.0
    norm = [p / s for p in probs]
    top1 = norm[0]
    top2 = norm[0] + (norm[1] if len(norm) > 1 else 0.0)
    gap = norm[0] - (norm[1] if len(norm) > 1 else 0.0)
    return {
        "top1_prob": round(top1, 4),
        "top2_sum": round(top2, 4),
        "gap12": round(gap, 4),
        "entropy": round(_entropy(norm), 4),
    }


def _confidence_level(n: int, *, exploratory: bool = False) -> str:
    if exploratory or n < MIN_N_PROFILE:
        return "Exploratory"
    if n >= 40:
        return "High"
    if n >= 15:
        return "Medium"
    if n >= MIN_N_PROFILE:
        return "Low"
    return "Exploratory"


class ExistingWorldBoundaryResearch:
    """Characterize / assign / bound EXISTING worlds using Evidence features."""

    def __init__(self) -> None:
        migrate()
        self.root = repo_root()
        self.evidence = evidence_root()
        self.discovery = EvidenceDiscoveryResearch()

    def _load_world_labels(self) -> dict[str, dict[str, str]]:
        """race_id -> {world, sub_world, source} from predictions + PI files."""
        out: dict[str, dict[str, str]] = {}
        conn = connect()
        try:
            for row in conn.execute(
                "SELECT race_id, bundle_json FROM predictions"
            ):
                try:
                    b = json.loads(row["bundle_json"] or "{}")
                except Exception:
                    continue
                w, s = extract_world_label(b)
                if not w:
                    continue
                out[str(row["race_id"])] = {
                    "world": w,
                    "sub_world": s or "",
                    "source": "predictions",
                }
        finally:
            conn.close()

        pi_dir = self.root / "public" / "data" / "predictions"
        if pi_dir.exists():
            for path in pi_dir.glob("*.pi.json"):
                try:
                    b = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                rid = None
                if isinstance(b.get("race_info"), dict):
                    rid = b["race_info"].get("race_id")
                rid = rid or b.get("race_id") or path.stem.replace(".pi", "")
                w, s = extract_world_label(b)
                if not w or not rid:
                    continue
                # prefer DB label if present
                if str(rid) not in out:
                    out[str(rid)] = {
                        "world": w,
                        "sub_world": s or "",
                        "source": "pi_file",
                    }
        return out

    def _cat_priors(self, races: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
        """Reuse ranking feature_score style priors from evidence analyzer path."""
        # Build simple win-rate priors across labeled+corpus horses with evidence
        priors: dict[str, dict[str, list[int]]] = {
            f: defaultdict(lambda: [0, 0]) for f in CATEGORICAL_FEATURES
        }
        for race in races:
            feat_maps = race.get("feat_maps") or {}
            winner = race.get("winner")
            runners = race.get("runners") or []
            for r in runners:
                try:
                    hn = int(r.get("horse_number"))
                except (TypeError, ValueError):
                    continue
                won = int(hn == winner)
                for fid in CATEGORICAL_FEATURES:
                    fmap = feat_maps.get(fid) or {}
                    raw = fmap.get(hn)
                    if raw is None or str(raw).strip() in {"", "-", "null", "None"}:
                        continue
                    key = str(raw).strip()
                    priors[fid][key][0] += won
                    priors[fid][key][1] += 1
        out: dict[str, dict[str, float]] = {}
        for fid, mp in priors.items():
            out[fid] = {}
            for k, (w, n) in mp.items():
                out[fid][k] = float((w + LAPLACE) / (n + 2 * LAPLACE))
        return out

    def _attach_features(
        self, races: list[dict[str, Any]], labels: dict[str, dict[str, str]]
    ) -> list[dict[str, Any]]:
        """Join corpus races with world labels + discretized pick features."""
        # Ensure feat_maps via discovery analyzer on races that have snapshots
        # load_corpus already may not include feat_maps — build from snapshots
        enriched = self.discovery.load_corpus()
        for race in enriched:
            sid = race.get("snapshot_id")
            if not sid:
                race["feat_maps"] = {}
                continue
            try:
                conn = connect()
                try:
                    rows = conn.execute(
                        """
                        SELECT horse_number, feature_id, value_text, value_num
                        FROM research_snapshot_features
                        WHERE snapshot_id=?
                        """,
                        (sid,),
                    ).fetchall()
                finally:
                    conn.close()
                maps: dict[str, dict[int, Any]] = defaultdict(dict)
                for fr in rows:
                    fid = str(fr["feature_id"])
                    try:
                        hn = int(fr["horse_number"])
                    except (TypeError, ValueError):
                        continue
                    val = fr["value_text"]
                    if val is None or str(val).strip() == "":
                        val = fr["value_num"]
                    maps[fid][hn] = val
                race["feat_maps"] = dict(maps)
            except Exception:
                race["feat_maps"] = {}

        priors = self._cat_priors(enriched)
        out: list[dict[str, Any]] = []
        for race in enriched:
            rid = str(race["race_id"])
            lab = labels.get(rid)
            runners = race.get("runners") or []
            pick = race.get("pick") or unique_top_pick(runners)
            dist = _race_dist_features(runners)
            feat_maps = race.get("feat_maps") or {}
            values: dict[str, Any] = {}
            if pick is not None:
                for fid in HORSE_FEATURES:
                    values[fid] = (feat_maps.get(fid) or {}).get(int(pick))
            oikiri_times: list[float] = []
            for hn, v in (feat_maps.get("oikiri_time") or {}).items():
                try:
                    oikiri_times.append(float(v))
                except (TypeError, ValueError):
                    pass
            bins = discretize_horse(
                values=values, cat_priors=priors, race_oikiri_times=oikiri_times
            )
            bins["surface"] = str(race.get("surface") or "unknown")
            bins["distance_bucket"] = str(
                race.get("distance_bucket")
                or _distance_bucket(race.get("distance"))
                or "unknown"
            )
            bins["going"] = str(race.get("going") or "unknown")
            bins["weather"] = str(race.get("weather") or "unknown")
            bins["field_bucket"] = str(
                race.get("field_bucket")
                or _field_bucket(race.get("field_size") or len(runners))
            )

            world = lab["world"] if lab else None
            sub = lab["sub_world"] if lab else None
            canonical = bool(world and world in EXISTING_WORLDS)
            out.append(
                {
                    "race_id": rid,
                    "world": world,
                    "sub_world": sub or None,
                    "canonical_world": canonical,
                    "label_source": (lab or {}).get("source"),
                    "has_evidence": bool(race.get("snapshot_id")),
                    "bins": bins,
                    "dist": dist,
                    "surface": bins["surface"],
                    "pick": pick,
                }
            )
        # Also include labeled races not in corpus winner set
        for rid, lab in labels.items():
            if any(x["race_id"] == rid for x in out):
                continue
            out.append(
                {
                    "race_id": rid,
                    "world": lab["world"],
                    "sub_world": lab.get("sub_world") or None,
                    "canonical_world": lab["world"] in EXISTING_WORLDS,
                    "label_source": lab.get("source"),
                    "has_evidence": False,
                    "bins": {},
                    "dist": {},
                    "surface": "unknown",
                    "pick": None,
                    "label_only": True,
                }
            )
        return out

    def _profiles(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        by_world: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            if r.get("canonical_world") and r.get("bins"):
                by_world[str(r["world"])].append(r)

        profiles: dict[str, Any] = {}
        for w in EXISTING_WORLDS:
            items = by_world.get(w) or []
            n = len(items)
            feat_dist: dict[str, dict[str, int]] = {}
            for fid in PROFILE_FEATURES:
                c = Counter()
                for it in items:
                    val = (it.get("bins") or {}).get(fid)
                    if val is None or str(val).endswith("_MISS"):
                        continue
                    c[str(val)] += 1
                feat_dist[fid] = dict(c.most_common(12))
            dist_stats = {
                "mean_top1": _safe_div(
                    sum((it.get("dist") or {}).get("top1_prob") or 0 for it in items),
                    n,
                ),
                "mean_entropy": _safe_div(
                    sum((it.get("dist") or {}).get("entropy") or 0 for it in items),
                    n,
                ),
                "mean_gap12": _safe_div(
                    sum((it.get("dist") or {}).get("gap12") or 0 for it in items),
                    n,
                ),
            }
            # mode summary
            modes = {}
            for fid, dist in feat_dist.items():
                if dist:
                    modes[fid] = max(dist.items(), key=lambda x: x[1])[0]
            profiles[w] = {
                "n": n,
                "n_with_evidence": sum(1 for it in items if it.get("has_evidence")),
                "confidence": _confidence_level(n, exploratory=n < MIN_N_PROFILE),
                "feature_distributions": feat_dist,
                "modes": modes,
                "dist_stats": dist_stats,
            }
        return profiles

    def _build_likelihood_tables(
        self, rows: list[dict[str, Any]]
    ) -> dict[str, dict[str, dict[str, float]]]:
        """P(bin|world) with Laplace for canonical labeled rows with bins."""
        counts: dict[str, dict[str, Counter]] = {
            w: defaultdict(Counter) for w in EXISTING_WORLDS
        }
        world_n: Counter = Counter()
        vocab: dict[str, set[str]] = defaultdict(set)
        for r in rows:
            if not r.get("canonical_world") or not r.get("bins"):
                continue
            w = str(r["world"])
            world_n[w] += 1
            for fid in PROFILE_FEATURES:
                val = (r.get("bins") or {}).get(fid)
                if val is None or str(val).endswith("_MISS"):
                    continue
                counts[w][fid][str(val)] += 1
                vocab[fid].add(str(val))

        tables: dict[str, dict[str, dict[str, float]]] = {}
        for w in EXISTING_WORLDS:
            tables[w] = {}
            n_w = world_n[w]
            for fid in PROFILE_FEATURES:
                vset = vocab[fid] or {"__none__"}
                tables[w][fid] = {}
                for v in vset:
                    c = counts[w][fid][v]
                    tables[w][fid][v] = (c + LAPLACE) / (n_w + LAPLACE * len(vset))
        tables["_world_n"] = {w: {"n": float(world_n[w])} for w in EXISTING_WORLDS}  # type: ignore
        return tables

    def _score_worlds(
        self,
        bins: dict[str, str],
        tables: dict[str, dict[str, dict[str, float]]],
        world_n: dict[str, int],
        total_n: int,
    ) -> dict[str, float]:
        """Log posterior proxy (fitness, not hit)."""
        scores: dict[str, float] = {}
        for w in EXISTING_WORLDS:
            if world_n.get(w, 0) <= 0:
                scores[w] = float("-inf")
                continue
            # prior
            ll = math.log((world_n[w] + LAPLACE) / (total_n + LAPLACE * len(EXISTING_WORLDS)))
            for fid in PROFILE_FEATURES:
                val = bins.get(fid)
                if val is None or str(val).endswith("_MISS"):
                    continue
                p = (tables.get(w) or {}).get(fid, {}).get(str(val))
                if p is None:
                    # unseen bin
                    p = LAPLACE / (world_n[w] + LAPLACE * 8)
                ll += math.log(max(p, 1e-12))
            scores[w] = ll
        # normalize to soft fitness 0-1 via softmax over finite
        finite = {k: v for k, v in scores.items() if math.isfinite(v)}
        if not finite:
            return {w: 0.0 for w in EXISTING_WORLDS}
        mx = max(finite.values())
        exps = {k: math.exp(v - mx) for k, v in finite.items()}
        z = sum(exps.values()) or 1.0
        out = {w: 0.0 for w in EXISTING_WORLDS}
        for k, e in exps.items():
            out[k] = round(e / z, 4)
        return out

    def _assignment(
        self, rows: list[dict[str, Any]], tables: dict[str, Any]
    ) -> dict[str, Any]:
        world_n = {
            w: int(((tables.get("_world_n") or {}).get(w) or {}).get("n") or 0)
            for w in EXISTING_WORLDS
        }
        total_n = sum(world_n.values())
        labeled = [
            r
            for r in rows
            if r.get("canonical_world") and r.get("bins")
        ]
        results = []
        fit_ok = 0
        ambiguous = 0
        for r in labeled:
            soft = self._score_worlds(r["bins"], tables, world_n, total_n)
            ranked = sorted(soft.items(), key=lambda x: -x[1])
            best_w, best_s = ranked[0]
            second_s = ranked[1][1] if len(ranked) > 1 else 0.0
            margin = best_s - second_s
            assigned = str(r["world"])
            assigned_fit = soft.get(assigned, 0.0)
            natural = best_w == assigned
            if natural:
                fit_ok += 1
            is_amb = margin < AMBIGUITY_MARGIN
            if is_amb:
                ambiguous += 1
            results.append(
                {
                    "race_id": r["race_id"],
                    "assigned_world": assigned,
                    "sub_world": r.get("sub_world"),
                    "best_fit_world": best_w,
                    "fitness_assigned": assigned_fit,
                    "fitness_best": best_s,
                    "margin": round(margin, 4),
                    "natural_membership": natural,
                    "ambiguous": is_amb,
                    "soft": soft,
                }
            )

        # LOO-ish feature contribution: drop feature, measure drop in assigned fitness
        feature_conf: dict[str, Any] = {}
        for fid in PROFILE_FEATURES:
            drops = []
            for r in labeled:
                soft_full = self._score_worlds(r["bins"], tables, world_n, total_n)
                soft_drop = self._score_worlds_drop(
                    r["bins"], tables, world_n, total_n, drop_fid=fid
                )
                aw = str(r["world"])
                drops.append(
                    (soft_full.get(aw, 0.0) or 0.0) - (soft_drop.get(aw, 0.0) or 0.0)
                )
            mean_drop = _safe_div(sum(drops), len(drops)) if drops else None
            feature_conf[fid] = {
                "label": FEATURE_LABELS.get(fid, fid),
                "mean_fitness_contribution": round(mean_drop, 4)
                if mean_drop is not None
                else None,
                "n": len(drops),
                "confidence": _confidence_level(len(drops)),
            }

        return {
            "n_labeled": len(labeled),
            "natural_membership_rate": _safe_div(fit_ok, len(labeled)),
            "ambiguous_rate": _safe_div(ambiguous, len(labeled)),
            "mean_assigned_fitness": _safe_div(
                sum(x["fitness_assigned"] for x in results), len(results)
            ),
            "results": results[:80],
            "feature_confidence": feature_conf,
            "note": (
                "Fitness = soft membership from feature likelihood tables; "
                "NOT hit rate. natural_membership = argmax soft == assigned world."
            ),
        }

    def _score_worlds_drop(
        self,
        bins: dict[str, str],
        tables: dict[str, dict[str, dict[str, float]]],
        world_n: dict[str, int],
        total_n: int,
        *,
        drop_fid: str,
    ) -> dict[str, float]:
        bins2 = {k: v for k, v in bins.items() if k != drop_fid}
        return self._score_worlds(bins2, tables, world_n, total_n)

    def _boundaries(
        self, profiles: dict[str, Any], assignment: dict[str, Any]
    ) -> dict[str, Any]:
        # Ambiguous races
        amb = [r for r in assignment.get("results") or [] if r.get("ambiguous")]
        # Overlapping modes across worlds with n>0
        worlds_with = [
            w for w, p in profiles.items() if int((p or {}).get("n") or 0) > 0
        ]
        overlaps = []
        unexplained = []
        for fid in PROFILE_FEATURES:
            modes = {}
            for w in worlds_with:
                m = ((profiles[w] or {}).get("modes") or {}).get(fid)
                if m:
                    modes[w] = m
            # same mode shared by >=2 worlds => overlap signal
            inv: dict[str, list[str]] = defaultdict(list)
            for w, m in modes.items():
                inv[m].append(w)
            for mode, ws in inv.items():
                if len(ws) >= 2:
                    overlaps.append(
                        {
                            "feature": fid,
                            "bin": mode,
                            "worlds": ws,
                            "type": "shared_mode",
                        }
                    )
            # unexplained: feature missing from all profiles (no mode)
            if not modes and worlds_with:
                unexplained.append(
                    {
                        "feature": fid,
                        "reason": "no_stable_mode_in_labeled_worlds",
                    }
                )

        # Sparse worlds
        sparse = [
            {"world": w, "n": (profiles.get(w) or {}).get("n"), "status": "insufficient_label"}
            for w in EXISTING_WORLDS
            if int((profiles.get(w) or {}).get("n") or 0) < MIN_N_PROFILE
        ]

        return {
            "ambiguous_n": len(amb),
            "ambiguous_examples": amb[:20],
            "overlapping_boundaries": overlaps[:40],
            "unexplained_features": unexplained,
            "sparse_worlds": sparse,
            "ambiguity_margin_threshold": AMBIGUITY_MARGIN,
        }

    def _refinement(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Propose subtypes ONLY within existing worlds (map to existing sub_world)."""
        proposals = []
        by_world: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            if r.get("canonical_world") and r.get("bins"):
                by_world[str(r["world"])].append(r)

        for w, items in by_world.items():
            # group by existing sub_world label
            by_sub: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for it in items:
                sub = it.get("sub_world") or "unspecified"
                by_sub[str(sub)].append(it)
            if len(items) < MIN_N_REFINE:
                continue
            sub_profiles = []
            for sub, sub_items in by_sub.items():
                if len(sub_items) < 2:
                    continue
                modes = {}
                for fid in PROFILE_FEATURES:
                    c = Counter(
                        str((it.get("bins") or {}).get(fid))
                        for it in sub_items
                        if (it.get("bins") or {}).get(fid)
                        and not str((it.get("bins") or {}).get(fid)).endswith("_MISS")
                    )
                    if c:
                        modes[fid] = c.most_common(1)[0][0]
                existing = sub in EXISTING_SUBWORLDS
                sub_profiles.append(
                    {
                        "parent_world": w,
                        "type_id": f"{w}__{sub}",
                        "label": f"{w} / {sub}",
                        "n": len(sub_items),
                        "maps_to_existing_subworld": existing,
                        "existing_subworld": sub if existing else None,
                        "modes": modes,
                        "confidence": _confidence_level(len(sub_items)),
                        "proposal": (
                            "Keep as internal subtype of existing World "
                            f"(NOT a new World). Prefer existing sub_world `{sub}`."
                            if existing
                            else (
                                "Descriptive internal cluster only; "
                                "do NOT promote to new World. "
                                "Consider mapping onto nearest existing sub_world."
                            )
                        ),
                    }
                )
            # stable feature-split candidates inside world (e.g. surface)
            for fid in ("surface", "distance_bucket", "popularity", "going"):
                groups: dict[str, list] = defaultdict(list)
                for it in items:
                    val = (it.get("bins") or {}).get(fid)
                    if not val or str(val).endswith("_MISS"):
                        continue
                    groups[str(val)].append(it)
                stable = {k: v for k, v in groups.items() if len(v) >= MIN_N_REFINE}
                if len(stable) >= 2:
                    proposals.append(
                        {
                            "parent_world": w,
                            "axis": fid,
                            "types": [
                                {
                                    "type_id": f"{w}__{fid}__{k}",
                                    "label": f"{w} / {FEATURE_LABELS.get(fid, fid)}={k}",
                                    "n": len(v),
                                    "new_world_forbidden": True,
                                }
                                for k, v in sorted(
                                    stable.items(), key=lambda x: -len(x[1])
                                )
                            ],
                            "note": (
                                "Internal細分類候補 only — World count unchanged"
                            ),
                        }
                    )
            for sp in sub_profiles:
                proposals.append(
                    {
                        "parent_world": w,
                        "kind": "existing_subworld_profile",
                        **sp,
                    }
                )

        return {
            "new_worlds_created": 0,
            "new_worlds_forbidden": True,
            "proposals": proposals[:40],
        }

    def analyze(self) -> dict[str, Any]:
        labels = self._load_world_labels()
        rows = self._attach_features([], labels)
        label_counts = Counter(
            lab["world"] for lab in labels.values() if lab.get("world")
        )
        canonical_counts = Counter(
            lab["world"]
            for lab in labels.values()
            if lab.get("world") in EXISTING_WORLDS
        )
        profiles = self._profiles(rows)
        tables = self._build_likelihood_tables(rows)
        assignment = self._assignment(rows, tables)
        boundaries = self._boundaries(profiles, assignment)
        refinement = self._refinement(rows)

        sample = {
            "corpus_races": len(rows),
            "labeled_total": len(labels),
            "labeled_canonical": sum(canonical_counts.values()),
            "labeled_with_bins": sum(
                1 for r in rows if r.get("canonical_world") and r.get("bins")
            ),
            "labeled_with_evidence": sum(
                1
                for r in rows
                if r.get("canonical_world") and r.get("has_evidence") and r.get("bins")
            ),
            "by_world_raw": dict(label_counts),
            "by_world_canonical": dict(canonical_counts),
            "existing_worlds": list(EXISTING_WORLDS),
            "exploratory": sum(canonical_counts.values()) < 100
            or len([w for w, n in canonical_counts.items() if n >= MIN_N_PROFILE]) < 3,
        }

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "shadow_only": True,
            "new_worlds_forbidden": True,
            "product_mutation": False,
            "sample": sample,
            "characterization": profiles,
            "assignment": assignment,
            "boundaries": boundaries,
            "refinement": refinement,
            "guardrails": {
                "existing_worlds_only": True,
                "hit_rate_not_used_for_fitness": True,
                "subtypes_only_inside_existing_worlds": True,
            },
        }


def write_characterization_md(report: dict[str, Any], path: Path) -> None:
    s = report.get("sample") or {}
    lines = [
        "# Version22 — Existing World Characterization",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Scope:** Existing Worlds only / New Worlds FORBIDDEN / Research only  ",
        "",
        "## Sample",
        "",
        f"- Corpus races: `{s.get('corpus_races')}`",
        f"- Labeled (canonical): `{s.get('labeled_canonical')}`",
        f"- Labeled with feature bins: `{s.get('labeled_with_bins')}`",
        f"- Labeled with Evidence: `{s.get('labeled_with_evidence')}`",
        f"- By world: `{json.dumps(s.get('by_world_canonical') or {}, ensure_ascii=False)}`",
        f"- Exploratory: `{s.get('exploratory')}`",
        "",
        "## Existing Worlds",
        "",
    ]
    for w in EXISTING_WORLDS:
        lines.append(f"- `{w}`")
    lines += ["", "## Feature profiles (field-best pick bins)", ""]
    char = report.get("characterization") or {}
    for w in EXISTING_WORLDS:
        p = char.get(w) or {}
        lines += [
            f"### `{w}`",
            "",
            f"- N: `{p.get('n')}` (Evidence `{p.get('n_with_evidence')}`)  ",
            f"- Confidence: `{p.get('confidence')}`  ",
            f"- Dist mean top1/entropy/gap12: "
            f"`{(p.get('dist_stats') or {}).get('mean_top1')}` / "
            f"`{(p.get('dist_stats') or {}).get('mean_entropy')}` / "
            f"`{(p.get('dist_stats') or {}).get('mean_gap12')}`",
            "",
            "| Feature | Mode |",
            "|---------|------|",
        ]
        for fid, mode in (p.get("modes") or {}).items():
            lines.append(f"| {FEATURE_LABELS.get(fid, fid)} | `{mode}` |")
        if not p.get("modes"):
            lines.append("| (insufficient labels) | — |")
        lines.append("")
    lines += [
        "## Note",
        "",
        "- Profiles describe **assigned** existing Worlds; they do not create Worlds.",
        "- Hit rate is intentionally omitted from characterization KPI.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_assignment_md(report: dict[str, Any], path: Path) -> None:
    a = report.get("assignment") or {}
    lines = [
        "# Version22 — Existing World Assignment (Fitness)",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "**Metric:** World membership fitness (NOT Hit rate)  ",
        "",
        "## Summary",
        "",
        f"- Labeled evaluated: `{a.get('n_labeled')}`",
        f"- Natural membership rate: `{_pct(a.get('natural_membership_rate'))}`",
        f"- Ambiguous rate: `{_pct(a.get('ambiguous_rate'))}`",
        f"- Mean assigned fitness: `{a.get('mean_assigned_fitness')}`",
        "",
        f"_{a.get('note')}_",
        "",
        "## Assignment Confidence by Feature",
        "",
        "| Feature | Mean Δ fitness if dropped | N | Conf |",
        "|---------|--------------------------:|--:|------|",
    ]
    for fid, row in (a.get("feature_confidence") or {}).items():
        lines.append(
            f"| {row.get('label')} | {row.get('mean_fitness_contribution')} | "
            f"{row.get('n')} | {row.get('confidence')} |"
        )
    lines += ["", "## Examples", ""]
    for r in (a.get("results") or [])[:25]:
        lines.append(
            f"- `{r.get('race_id')}` assigned=`{r.get('assigned_world')}` "
            f"best_fit=`{r.get('best_fit_world')}` "
            f"fit={r.get('fitness_assigned')} margin={r.get('margin')} "
            f"natural={r.get('natural_membership')} amb={r.get('ambiguous')}"
        )
    lines += [
        "",
        "## Guardrails",
        "",
        "- Soft membership uses EXISTING world likelihood tables only",
        "- Does not change Prediction / PE / CE / AI assignment in product",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_boundary_md(report: dict[str, Any], path: Path) -> None:
    b = report.get("boundaries") or {}
    lines = [
        "# Version22 — Existing World Boundary Analysis",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "## Ambiguous boundaries",
        "",
        f"- Count: `{b.get('ambiguous_n')}` (margin < `{b.get('ambiguity_margin_threshold')}`)",
        "",
    ]
    for ex in b.get("ambiguous_examples") or []:
        soft = ex.get("soft") or {}
        top = sorted(soft.items(), key=lambda x: -x[1])[:3]
        lines.append(
            f"- `{ex.get('race_id')}` assigned=`{ex.get('assigned_world')}` "
            f"top={top}"
        )
    if not b.get("ambiguous_examples"):
        lines.append("- (none or insufficient multi-world labels)")

    lines += ["", "## Overlapping boundaries", ""]
    for o in b.get("overlapping_boundaries") or []:
        lines.append(
            f"- `{o.get('feature')}`=`{o.get('bin')}` shared by {o.get('worlds')}"
        )
    if not b.get("overlapping_boundaries"):
        lines.append(
            "- Overlap detection limited: fewer than 2 Worlds have stable modes"
        )

    lines += ["", "## Unexplained features", ""]
    for u in b.get("unexplained_features") or []:
        lines.append(f"- `{u.get('feature')}`: {u.get('reason')}")
    if not b.get("unexplained_features"):
        lines.append("- (none flagged)")

    lines += ["", "## Sparse / unlabeled Worlds", ""]
    for sp in b.get("sparse_worlds") or []:
        lines.append(
            f"- `{sp.get('world')}` n=`{sp.get('n')}` status=`{sp.get('status')}`"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- Boundary quality is constrained by labeled Evidence supply.",
        "- Prefer accumulating labeled PredictionBundles for sparse Worlds "
        "before any product refinement.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_refinement_md(report: dict[str, Any], path: Path) -> None:
    r = report.get("refinement") or {}
    lines = [
        "# Version22 — Existing World Refinement (Subtypes only)",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        f"- New Worlds created: `{r.get('new_worlds_created')}`",
        f"- New Worlds forbidden: `{r.get('new_worlds_forbidden')}`",
        "",
        "## Internal細分類候補",
        "",
        "Format: `ParentWorld / Type` — World count unchanged.",
        "",
    ]
    props = r.get("proposals") or []
    if not props:
        lines.append("- (insufficient labeled volume for subtype proposals)")
    for p in props:
        if p.get("kind") == "existing_subworld_profile" or p.get("type_id"):
            lines += [
                f"### `{p.get('label') or p.get('type_id')}`",
                "",
                f"- Parent: `{p.get('parent_world')}`",
                f"- N: `{p.get('n')}`",
                f"- Maps to existing sub_world: `{p.get('maps_to_existing_subworld')}` "
                f"(`{p.get('existing_subworld')}`)",
                f"- Confidence: `{p.get('confidence')}`",
                f"- Proposal: {p.get('proposal')}",
                f"- Modes: `{json.dumps(p.get('modes') or {}, ensure_ascii=False)}`",
                "",
            ]
        elif p.get("types"):
            lines += [
                f"### `{p.get('parent_world')}` × `{p.get('axis')}`",
                "",
                f"- {p.get('note')}",
                "",
            ]
            for t in p.get("types") or []:
                lines.append(
                    f"- `{t.get('label')}` n=`{t.get('n')}` "
                    f"(new_world_forbidden=`{t.get('new_world_forbidden')}`)"
                )
            lines.append("")
    lines += [
        "## Rule",
        "",
        "- Only subtypes inside an existing World are allowed.",
        "- Example: `midupper_world` → Type `midupper_route` / `midupper_spread`.",
        "- Never introduce `world_7` or rename Worlds.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write() -> dict[str, Any]:
    report = ExistingWorldBoundaryResearch().analyze()
    docs = repo_root() / "docs" / "research"
    docs.mkdir(parents=True, exist_ok=True)
    char_p = docs / "v22-world-characterization.md"
    bound_p = docs / "v22-world-boundary.md"
    assign_p = docs / "v22-world-assignment.md"
    refine_p = docs / "v22-world-refinement.md"
    write_characterization_md(report, char_p)
    write_boundary_md(report, bound_p)
    write_assignment_md(report, assign_p)
    write_refinement_md(report, refine_p)
    json_path = evidence_root() / "reports" / "v22-world-boundary.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report["_outputs"] = {
        "characterization": str(char_p),
        "boundary": str(bound_p),
        "assignment": str(assign_p),
        "refinement": str(refine_p),
        "json": str(json_path),
    }
    return report
