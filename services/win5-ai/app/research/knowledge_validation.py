# -*- coding: utf-8 -*-
"""
Version19 Knowledge Validation Lab

Validate V18 Knowledge entries with recommended_action=Candidate
via Research Shadow experiments (feature flags). Does NOT mutate
Prediction / PE / CE / AI / Challenge / Resolver / ResultAutomation / Production.

State machine:
  Research → Candidate → Validated → Production_Candidate → Rejected
"""
from __future__ import annotations

import json
import re
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .analyzer import extract_runners, soft_hit, strict_hit, tie_group, unique_top_pick
from .config import evidence_root, repo_root
from .evidence_discovery import (
    CONFIDENT_MIN_N,
    EvidenceDiscoveryResearch,
    FEATURE_LABELS,
    HORSE_FEATURES,
    research_category,
    wilson_ci,
)
from .knowledge_base import _load_json, _week_id
from .ranking_engine import CATEGORICAL_FEATURES, feature_score, resolve_by_score
from .young_horse_archetypes import discretize_horse
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-knowledge-validation/1.0"

STATES = (
    "Research",
    "Candidate",
    "Validated",
    "Production_Candidate",
    "Rejected",
)

VALIDATION_GATE = {
    "min_n": 20,
    "min_strict_rate": 0.18,
    "min_strict_improvement_vs_baseline": 0.0,
    "min_wilson_ci_low": 0.12,
    "min_coverage": 0.40,
    "min_reliability": 50.0,
    "max_knowledge_drift": 0.20,
    "min_shadow_win_rate": 0.15,
    "production_candidate_min_strict": 0.25,
    "production_candidate_top_n": 3,
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_pattern(pattern: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in str(pattern or "").split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _shadow_flag_key(knowledge_id: str) -> str:
    return f"shadow.knowledge.{knowledge_id}"


class KnowledgeValidationLab:
    def __init__(self) -> None:
        migrate()
        self.root = repo_root()
        self.evidence = evidence_root()
        self.discovery = EvidenceDiscoveryResearch()

    def _load_kb(self) -> list[dict[str, Any]]:
        path = self.evidence / "reports" / "v18-knowledge-base.json"
        data = _load_json(path)
        entries = data.get("entries") or []
        if not entries:
            # rebuild from DB
            conn = connect()
            try:
                rows = conn.execute(
                    """
                    SELECT knowledge_id, knowledge_type, observation, evidence_json,
                           hypothesis, confidence, limitations_json, recommended_action,
                           graph_json, source_key, meta_json
                    FROM research_knowledge_entries
                    ORDER BY knowledge_id
                    """
                ).fetchall()
                for r in rows:
                    entries.append(
                        {
                            "knowledge_id": r["knowledge_id"],
                            "knowledge_type": r["knowledge_type"],
                            "observation": r["observation"],
                            "evidence": json.loads(r["evidence_json"] or "{}"),
                            "hypothesis": r["hypothesis"],
                            "confidence": r["confidence"],
                            "limitations": json.loads(r["limitations_json"] or "[]"),
                            "recommended_action": r["recommended_action"],
                            "graph": json.loads(r["graph_json"] or "{}"),
                            "source_key": r["source_key"],
                            "meta": json.loads(r["meta_json"] or "{}"),
                        }
                    )
            finally:
                conn.close()
        return entries

    def _load_reliability(self) -> dict[str, float]:
        data = _load_json(self.evidence / "reports" / "v14-evidence-reliability.json")
        return {
            str(f.get("feature_id")): float(f.get("reliability_score") or 50.0)
            for f in data.get("features") or []
            if f.get("feature_id")
        }

    def _get_state(self, conn, knowledge_id: str) -> str:
        row = conn.execute(
            "SELECT state FROM research_knowledge_states WHERE knowledge_id=?",
            (knowledge_id,),
        ).fetchone()
        if row:
            return str(row["state"])
        return "Candidate"

    def _set_state(
        self,
        conn,
        knowledge_id: str,
        state: str,
        action: str,
        now: str,
    ) -> None:
        conn.execute(
            """
            INSERT INTO research_knowledge_states(
              knowledge_id, state, recommended_action, updated_at, meta_json
            ) VALUES (?,?,?,?,?)
            ON CONFLICT(knowledge_id) DO UPDATE SET
              state=excluded.state,
              recommended_action=excluded.recommended_action,
              updated_at=excluded.updated_at
            """,
            (
                knowledge_id,
                state,
                action,
                now,
                json.dumps({"last_validation": now}, ensure_ascii=False),
            ),
        )

    def generate_shadow_flag(self, entry: dict[str, Any]) -> dict[str, Any]:
        kid = entry["knowledge_id"]
        ktype = entry["knowledge_type"]
        graph = entry.get("graph") or {}
        meta = entry.get("meta") or {}
        source = entry.get("source_key") or ""

        flag: dict[str, Any] = {
            "flag_key": _shadow_flag_key(kid),
            "knowledge_id": kid,
            "knowledge_type": ktype,
            "enabled": True,
            "scope": "research_shadow_only",
            "mutates_production": False,
            "mutates_prediction": False,
            "mutates_resolver": False,
        }

        if ktype == "feature":
            m = re.match(r"feature:([^:]+):(.+)", source)
            segment = m.group(1) if m else "ALL"
            fid = m.group(2) if m else (graph.get("features") or ["unknown"])[0]
            flag.update(
                {
                    "mode": "field_best_feature",
                    "feature_id": fid,
                    "segment": segment,
                    "label": FEATURE_LABELS.get(fid, fid),
                }
            )
        elif ktype == "interaction":
            pattern = ""
            if "mined_2way:" in source:
                pattern = source.split("mined_2way:", 1)[1]
            elif "mined_3way:" in source:
                pattern = source.split("mined_3way:", 1)[1]
            elif entry.get("meta", {}).get("interaction_type") == "cascade":
                pattern = "×".join(graph.get("features") or [])
            else:
                inter = (graph.get("interactions") or [""])[0]
                pattern = inter
            flag.update(
                {
                    "mode": "pattern_match_pick",
                    "pattern": pattern,
                    "rules": _parse_pattern(pattern),
                }
            )
        elif ktype == "winner":
            parts = source.split(":")
            flag.update(
                {
                    "mode": "slice_validation",
                    "axis": parts[1] if len(parts) > 2 else "category",
                    "segment": parts[2] if len(parts) > 2 else parts[-1],
                }
            )
        else:
            flag.update({"mode": "observational", "source_key": source})

        return flag

    def _laplace_prior(self, wins: Counter, apps: Counter) -> dict[str, float]:
        out: dict[str, float] = {}
        for k, a in apps.items():
            out[k] = (wins.get(k, 0) + 1.0) / (a + 2.0)
        return out

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
        return self._laplace_prior(wins, apps)

    def _race_matches_segment(self, race: dict[str, Any], segment: str) -> bool:
        if segment in {"", "ALL"}:
            return True
        return race.get("category") == segment

    def _shadow_pick_feature(
        self,
        race: dict[str, Any],
        fmap: dict[str, dict[str, dict[int, Any]]],
        feature_id: str,
        cat_priors: dict[str, float] | None,
    ) -> int | None:
        runners = race["runners"]
        snap = str(race.get("snapshot_id") or "")
        values = (fmap.get(snap) or {}).get(feature_id) or {}
        scores = {
            int(r.get("horse_number") or 0): feature_score(
                feature_id, values.get(int(r.get("horse_number") or 0)), cat_prior=cat_priors
            )
            for r in runners
        }
        pick, status = resolve_by_score(runners, scores)
        return pick if status == "resolved" else None

    def _shadow_pick_pattern(
        self,
        race: dict[str, Any],
        fmap: dict[str, dict[str, dict[int, Any]]],
        rules: dict[str, str],
        races: list[dict[str, Any]],
        idx: int,
    ) -> int | None:
        snap = str(race.get("snapshot_id") or "")
        feat_maps = fmap.get(snap) or {}
        cat_priors = {
            fid: self._cat_priors_loo(races, fmap, idx, fid)
            for fid in HORSE_FEATURES
            if fid in CATEGORICAL_FEATURES
        }
        oikiri_times = []
        for v in (feat_maps.get("oikiri_time") or {}).values():
            try:
                oikiri_times.append(float(v))
            except (TypeError, ValueError):
                pass
        matches: list[int] = []
        for r in race["runners"]:
            hn = int(r.get("horse_number") or 0)
            values = {fid: (feat_maps.get(fid) or {}).get(hn) for fid in HORSE_FEATURES}
            bins = discretize_horse(
                values=values, cat_priors=cat_priors, race_oikiri_times=oikiri_times
            )
            bins["surface"] = race.get("surface")
            bins["distance_bucket"] = race.get("distance_bucket")
            bins["going"] = race.get("going")
            ok = True
            for k, v in rules.items():
                if bins.get(k) != v:
                    ok = False
                    break
            if ok:
                matches.append(hn)
        if not matches:
            return None
        if len(matches) == 1:
            return matches[0]
        # tie-break by popularity
        pop = feat_maps.get("popularity") or {}
        scored = []
        for hn in matches:
            try:
                scored.append((int(float(pop.get(hn, 99))), hn))
            except (TypeError, ValueError):
                scored.append((99, hn))
        scored.sort()
        return scored[0][1]

    def _roi_for_pick(
        self, race: dict[str, Any], pick: int | None, winner: int
    ) -> tuple[int, float]:
        if pick is None:
            return 0, 0.0
        stake = 100
        if pick != winner:
            return stake, 0.0
        # odds fallback from snapshot
        snap = str(race.get("snapshot_id") or "")
        # simple 250 fallback
        return stake, 250.0

    def validate_candidate(
        self,
        entry: dict[str, Any],
        flag: dict[str, Any],
        races: list[dict[str, Any]],
        fmap: dict[str, dict[str, dict[int, Any]]],
        reliability_map: dict[str, float],
    ) -> dict[str, Any]:
        kid = entry["knowledge_id"]
        ktype = entry["knowledge_type"]
        discovery_ev = entry.get("evidence") or {}
        discovery_rate = discovery_ev.get("hit_rate")

        applicable: list[dict[str, Any]] = []
        for idx, race in enumerate(races):
            if not race.get("has_snapshot"):
                continue
            if ktype == "feature":
                seg = flag.get("segment") or "ALL"
                if self._race_matches_segment(race, seg):
                    applicable.append({**race, "_idx": idx})
            elif ktype == "interaction":
                rules = flag.get("rules") or {}
                pick = self._shadow_pick_pattern(race, fmap, rules, races, idx)
                if pick is not None:
                    applicable.append({**race, "_idx": idx, "_shadow_pick": pick})
            elif ktype == "winner":
                axis = flag.get("axis") or ""
                seg = flag.get("segment") or ""
                val = race.get(axis) if axis in race else race.get("category")
                if str(val) == str(seg):
                    applicable.append({**race, "_idx": idx})

        baseline_strict = 0
        baseline_soft = 0
        shadow_strict = 0
        shadow_soft = 0
        shadow_win = 0
        shadow_lose = 0
        shadow_draw = 0
        stakes = 0
        returns = 0.0
        coverage_cells = 0
        coverage_filled = 0
        evaluated = 0

        fid = flag.get("feature_id")
        rel_vals = []
        if fid:
            rel_vals.append(reliability_map.get(fid))
        for f in (entry.get("graph") or {}).get("features") or []:
            if f in reliability_map:
                rel_vals.append(reliability_map[f])
        reliability = (
            sum(v for v in rel_vals if v is not None) / len(rel_vals)
            if rel_vals
            else discovery_ev.get("reliability")
        )

        for race in applicable:
            winner = int(race["winner"])
            runners = race["runners"]
            baseline_strict += int(race.get("strict") or 0)
            baseline_soft += int(race.get("soft") or 0)

            idx = race.get("_idx", 0)
            if ktype == "feature":
                cat_prior = None
                if fid in CATEGORICAL_FEATURES:
                    cat_prior = self._cat_priors_loo(races, fmap, idx, fid)
                shadow_pick = self._shadow_pick_feature(race, fmap, fid, cat_prior)
            elif ktype == "interaction":
                shadow_pick = race.get("_shadow_pick")
            else:
                shadow_pick = race.get("pick") or unique_top_pick(runners)
                try:
                    shadow_pick = int(shadow_pick) if shadow_pick is not None else None
                except (TypeError, ValueError):
                    shadow_pick = None

            if shadow_pick is None:
                continue

            evaluated += 1
            coverage_cells += 1
            snap = str(race.get("snapshot_id") or "")
            if ktype == "feature" and fid:
                v = (fmap.get(snap) or {}).get(fid, {}).get(shadow_pick)
                if v is not None:
                    coverage_filled += 1
            else:
                coverage_filled += 1

            s_hit = shadow_pick == winner
            g = tie_group(runners)
            g_nums = {int(r.get("horse_number") or 0) for r in g}
            so_hit = s_hit or (shadow_pick in g_nums and winner in g_nums)

            if s_hit:
                shadow_strict += 1
                shadow_win += 1
            elif so_hit:
                shadow_soft += 1
                shadow_draw += 1
            else:
                shadow_lose += 1

            st, ret = self._roi_for_pick(race, shadow_pick, winner)
            stakes += st
            returns += ret

        n = evaluated

        strict_rate = _safe_div(shadow_strict, n)
        soft_rate = _safe_div(shadow_soft, n)
        base_strict_rate = _safe_div(baseline_strict, len(applicable) or 1)
        roi = _safe_div(returns - stakes, stakes) if stakes else None
        lo, hi = wilson_ci(shadow_strict, n) if n else (0.0, 1.0)
        coverage = _safe_div(coverage_filled, coverage_cells) if coverage_cells else None

        drift = None
        if discovery_rate is not None and strict_rate is not None:
            drift = round(abs(float(strict_rate) - float(discovery_rate)), 4)

        metrics = {
            "n": n,
            "applicable_races": len(applicable),
            "strict": shadow_strict,
            "soft": shadow_soft,
            "strict_rate": strict_rate,
            "soft_rate": soft_rate,
            "baseline_strict_rate": base_strict_rate,
            "strict_improvement": round((strict_rate or 0) - (base_strict_rate or 0), 4)
            if strict_rate is not None
            else None,
            "roi": roi,
            "wilson_ci": {"low": round(lo, 4), "high": round(hi, 4)},
            "coverage": coverage,
            "reliability": reliability,
            "shadow_outcomes": {
                "win": shadow_win,
                "lose": shadow_lose,
                "draw": shadow_draw,
            },
            "knowledge_drift": drift,
            "discovery_hit_rate": discovery_rate,
        }
        return metrics

    def evaluate_governance(
        self, metrics: dict[str, Any], entry: dict[str, Any]
    ) -> dict[str, Any]:
        n = int(metrics.get("n") or 0)
        strict_rate = metrics.get("strict_rate")
        lo = (metrics.get("wilson_ci") or {}).get("low")
        coverage = metrics.get("coverage")
        reliability = metrics.get("reliability")
        drift = metrics.get("knowledge_drift")
        improvement = metrics.get("strict_improvement")
        win_n = (metrics.get("shadow_outcomes") or {}).get("win", 0)

        checks = {
            "min_n": n >= VALIDATION_GATE["min_n"],
            "min_strict_rate": (strict_rate or 0) >= VALIDATION_GATE["min_strict_rate"],
            "min_strict_improvement": (improvement or 0)
            >= VALIDATION_GATE["min_strict_improvement_vs_baseline"],
            "min_wilson_ci_low": (lo or 0) >= VALIDATION_GATE["min_wilson_ci_low"],
            "min_coverage": (coverage or 0) >= VALIDATION_GATE["min_coverage"]
            if coverage is not None
            else n < VALIDATION_GATE["min_n"],
            "min_reliability": (reliability or 50) >= VALIDATION_GATE["min_reliability"]
            if reliability is not None
            else True,
            "max_knowledge_drift": (drift or 0) <= VALIDATION_GATE["max_knowledge_drift"]
            if drift is not None
            else True,
            "min_shadow_win_rate": _safe_div(win_n, n) >= VALIDATION_GATE["min_shadow_win_rate"]
            if n
            else False,
        }
        passed = all(checks.values())
        # hard reject if enough n but worse than baseline by margin
        hard_fail = (
            n >= VALIDATION_GATE["min_n"]
            and improvement is not None
            and improvement < -0.05
        )
        return {
            "passed": passed and not hard_fail,
            "hard_fail": hard_fail,
            "checks": checks,
            "gate": VALIDATION_GATE,
        }

    def _rank_score(self, metrics: dict[str, Any], governance: dict[str, Any]) -> float:
        n = float(metrics.get("n") or 0)
        sr = float(metrics.get("strict_rate") or 0)
        imp = float(metrics.get("strict_improvement") or 0)
        rel = float(metrics.get("reliability") or 50) / 100.0
        drift_pen = float(metrics.get("knowledge_drift") or 0)
        pass_bonus = 1.0 if governance.get("passed") else 0.0
        return round(
            pass_bonus * 0.4
            + sr * 0.25
            + max(imp, 0) * 0.15
            + min(n / 50.0, 1.0) * 0.10
            + rel * 0.10
            - drift_pen * 0.10,
            4,
        )

    def run(self) -> dict[str, Any]:
        started = _now()
        week = _week_id()
        run_id = f"kv-{uuid.uuid4().hex[:12]}"
        entries = self._load_kb()
        candidates = [
            e for e in entries if e.get("recommended_action") == "Candidate"
        ]
        races = self.discovery.load_corpus()
        evidence_races = [r for r in races if r.get("has_snapshot")]
        snap_ids = [str(r["snapshot_id"]) for r in evidence_races]
        fmap = self.discovery.analyzer.load_feature_map(snap_ids)
        reliability_map = self._load_reliability()

        validations: list[dict[str, Any]] = []
        flags: list[dict[str, Any]] = []
        history: list[dict[str, Any]] = []
        now = _now()

        conn = connect()
        try:
            for entry in candidates:
                kid = entry["knowledge_id"]
                flag = self.generate_shadow_flag(entry)
                flag_id = f"flag-{uuid.uuid4().hex[:12]}"
                flag["flag_id"] = flag_id
                flags.append(flag)

                conn.execute(
                    """
                    INSERT INTO research_shadow_feature_flags(
                      flag_id, knowledge_id, flag_key, flag_json, created_at, updated_at
                    ) VALUES (?,?,?,?,?,?)
                    ON CONFLICT(flag_key) DO UPDATE SET
                      flag_json=excluded.flag_json,
                      updated_at=excluded.updated_at
                    """,
                    (
                        flag_id,
                        kid,
                        flag["flag_key"],
                        json.dumps(flag, ensure_ascii=False),
                        now,
                        now,
                    ),
                )

                state_before = self._get_state(conn, kid)
                metrics = self.validate_candidate(
                    entry, flag, evidence_races, fmap, reliability_map
                )
                governance = self.evaluate_governance(metrics, entry)
                rank_score = self._rank_score(metrics, governance)

                if governance.get("hard_fail"):
                    state_after = "Rejected"
                elif governance.get("passed"):
                    state_after = "Validated"
                elif int(metrics.get("n") or 0) < VALIDATION_GATE["min_n"]:
                    state_after = "Candidate"
                else:
                    state_after = "Rejected"

                self._set_state(conn, kid, state_after, entry.get("recommended_action", "Candidate"), now)

                vid = f"val-{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO research_knowledge_validations(
                      validation_id, run_id, knowledge_id, shadow_flag_id,
                      metrics_json, governance_json, passed, state_before, state_after,
                      knowledge_drift, rank_score, created_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        vid,
                        run_id,
                        kid,
                        flag_id,
                        json.dumps(metrics, ensure_ascii=False),
                        json.dumps(governance, ensure_ascii=False),
                        int(bool(governance.get("passed"))),
                        state_before,
                        state_after,
                        metrics.get("knowledge_drift"),
                        rank_score,
                        now,
                    ),
                )

                hist_id = f"hist-{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO research_knowledge_validation_history(
                      history_id, knowledge_id, run_id, week_id, event,
                      state_before, state_after, detail_json, created_at
                    ) VALUES (?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        hist_id,
                        kid,
                        run_id,
                        week,
                        "shadow_validation",
                        state_before,
                        state_after,
                        json.dumps(
                            {"metrics": metrics, "governance": governance, "flag_key": flag["flag_key"]},
                            ensure_ascii=False,
                        ),
                        now,
                    ),
                )

                validations.append(
                    {
                        "validation_id": vid,
                        "knowledge_id": kid,
                        "knowledge_type": entry["knowledge_type"],
                        "source_key": entry.get("source_key"),
                        "observation": entry.get("observation"),
                        "hypothesis": entry.get("hypothesis"),
                        "shadow_flag": flag,
                        "metrics": metrics,
                        "governance": governance,
                        "passed": governance.get("passed"),
                        "state_before": state_before,
                        "state_after": state_after,
                        "rank_score": rank_score,
                    }
                )
                history.append(
                    {
                        "knowledge_id": kid,
                        "week_id": week,
                        "state_before": state_before,
                        "state_after": state_after,
                        "passed": governance.get("passed"),
                    }
                )

            # Promote top Validated → Production_Candidate (label only, no prod deploy)
            validated = sorted(
                [v for v in validations if v["state_after"] == "Validated"],
                key=lambda x: (-x["rank_score"], -(x["metrics"].get("strict_rate") or 0)),
            )
            prod_n = VALIDATION_GATE["production_candidate_top_n"]
            for v in validated[:prod_n]:
                if (v["metrics"].get("strict_rate") or 0) >= VALIDATION_GATE[
                    "production_candidate_min_strict"
                ]:
                    self._set_state(
                        conn, v["knowledge_id"], "Production_Candidate", "Candidate", now
                    )
                    v["state_after"] = "Production_Candidate"
                    conn.execute(
                        """
                        INSERT INTO research_knowledge_validation_history(
                          history_id, knowledge_id, run_id, week_id, event,
                          state_before, state_after, detail_json, created_at
                        ) VALUES (?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            f"hist-{uuid.uuid4().hex[:12]}",
                            v["knowledge_id"],
                            run_id,
                            week,
                            "promote_production_candidate",
                            "Validated",
                            "Production_Candidate",
                            json.dumps({"rank_score": v["rank_score"]}, ensure_ascii=False),
                            now,
                        ),
                    )

            summary = {
                "week_id": week,
                "candidates": len(candidates),
                "passed": sum(1 for v in validations if v.get("passed")),
                "validated": sum(1 for v in validations if v["state_after"] in {"Validated", "Production_Candidate"}),
                "rejected": sum(1 for v in validations if v["state_after"] == "Rejected"),
                "production_candidate": sum(
                    1 for v in validations if v["state_after"] == "Production_Candidate"
                ),
                "by_type": dict(Counter(v["knowledge_type"] for v in validations)),
                "flags_generated": len(flags),
            }
            finished = _now()
            conn.execute(
                """
                INSERT INTO research_knowledge_validation_runs(
                  run_id, week_id, schema_version, started_at, finished_at,
                  status, summary_json, created_at
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    run_id,
                    week,
                    SCHEMA_VERSION,
                    started,
                    finished,
                    "ok",
                    json.dumps(summary, ensure_ascii=False),
                    finished,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        ranking = sorted(validations, key=lambda x: (-x["rank_score"], -(x["metrics"].get("n") or 0)))

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": finished,
            "run_id": run_id,
            "week_id": week,
            "prediction_mutation": "FORBIDDEN",
            "resolver_mutation": "FORBIDDEN",
            "production_mutation": "FORBIDDEN",
            "summary": summary,
            "validations": validations,
            "ranking": ranking,
            "shadow_flags": flags,
            "history": history,
            "validation_gate": VALIDATION_GATE,
        }


def write_validation_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    s = report.get("summary") or {}
    lines = [
        "# Version19 Research - Knowledge Validation",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"**Run:** `{report.get('run_id')}`  ",
        f"**Week:** `{report.get('week_id')}`  ",
        "**Scope:** Shadow validation only / Prediction FORBIDDEN  ",
        "",
        "## Summary",
        "",
        f"- Candidates validated: `{s.get('candidates')}`",
        f"- Passed governance: `{s.get('passed')}`",
        f"- Validated: `{s.get('validated')}`",
        f"- Rejected: `{s.get('rejected')}`",
        f"- Production Candidate (label only): `{s.get('production_candidate')}`",
        f"- Shadow flags generated: `{s.get('flags_generated')}`",
        "",
        "## Governance gate",
        "",
        f"```json\n{json.dumps(report.get('validation_gate') or {}, ensure_ascii=False, indent=2)}\n```",
        "",
        "## Results",
        "",
        "| ID | Type | N | Strict | Soft | ROI | Drift | Passed | State |",
        "|----|------|--:|-------:|-----:|----:|------:|--------|-------|",
    ]
    for v in report.get("validations") or []:
        m = v.get("metrics") or {}
        lines.append(
            f"| `{v.get('knowledge_id')}` | {v.get('knowledge_type')} | {m.get('n')} | "
            f"{_pct(m.get('strict_rate'))} | {_pct(m.get('soft_rate'))} | "
            f"{_pct(m.get('roi')) if m.get('roi') is not None else 'N/A'} | "
            f"{m.get('knowledge_drift')} | {v.get('passed')} | {v.get('state_after')} |"
        )
    lines.extend(
        [
            "",
            "## Shadow feature flags (sample)",
            "",
        ]
    )
    for f in (report.get("shadow_flags") or [])[:10]:
        lines.append(f"- `{f.get('flag_key')}` mode=`{f.get('mode')}`")
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- Shadow flags are research-only; do not enable in Production",
            "- Resolver unchanged",
            "- Production_Candidate is a research label, not deployment",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_ranking_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Version19 Research - Candidate Ranking",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "| Rank | ID | Score | Strict | Δ vs Base | N | State | Flag |",
        "|-----:|----|------:|-------:|----------:|--:|-------|------|",
    ]
    for i, v in enumerate(report.get("ranking") or [], start=1):
        m = v.get("metrics") or {}
        flag = (v.get("shadow_flag") or {}).get("flag_key", "")
        lines.append(
            f"| {i} | `{v.get('knowledge_id')}` | {v.get('rank_score')} | "
            f"{_pct(m.get('strict_rate'))} | {m.get('strict_improvement')} | "
            f"{m.get('n')} | {v.get('state_after')} | `{flag}` |"
        )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_history_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Version19 Research - Validation History",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"**Run:** `{report.get('run_id')}`  ",
        "",
        "## State transitions",
        "",
        "| Knowledge ID | Before | After | Passed |",
        "|--------------|--------|-------|--------|",
    ]
    for h in report.get("history") or []:
        lines.append(
            f"| `{h.get('knowledge_id')}` | {h.get('state_before')} | "
            f"{h.get('state_after')} | {h.get('passed')} |"
        )
    lines.extend(
        [
            "",
            "## State machine",
            "",
            "```",
            "Research → Candidate → Validated → Production_Candidate → Rejected",
            "```",
            "",
            "## Decision",
            "",
            "```",
            "Action Type: Knowledge Validation Lab (Shadow)",
            "Prediction Mutation: FORBIDDEN",
            "Resolver Mutation: FORBIDDEN",
            "Production Mutation: FORBIDDEN",
            "```",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write() -> dict[str, Any]:
    report = KnowledgeValidationLab().run()
    docs = repo_root() / "docs" / "research"
    docs.mkdir(parents=True, exist_ok=True)
    write_validation_md(report, docs / "v19-knowledge-validation.md")
    write_ranking_md(report, docs / "v19-candidate-ranking.md")
    write_history_md(report, docs / "v19-validation-history.md")
    json_path = evidence_root() / "reports" / "v19-knowledge-validation.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {
        "validation": str(docs / "v19-knowledge-validation.md"),
        "ranking": str(docs / "v19-candidate-ranking.md"),
        "history": str(docs / "v19-validation-history.md"),
        "json": str(json_path),
    }
    return report
