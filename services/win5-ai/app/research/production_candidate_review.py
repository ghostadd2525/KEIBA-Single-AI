# -*- coding: utf-8 -*-
"""
Version20 Production Candidate Review

Design-review Production_Candidate Knowledge before any AI implementation.
Research-only. Does NOT mutate Prediction / PE / CE / AI / Challenge /
Resolver / ResultAutomation / Production.

PASS-only candidates are labeled V21_Implementation_Candidate (research label).
"""
from __future__ import annotations

import json
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .config import evidence_root, repo_root
from .knowledge_base import _load_json, _week_id
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-production-candidate-review/1.0"

REVIEW_DIMENSIONS = (
    "leak_risk",
    "generalization",
    "pe_ce_alignment",
    "shadow_reproducibility",
    "corpus_drift",
    "knowledge_drift",
    "evidence_quality",
    "long_term_stability",
)

# Features already central to market PE / Candidate Evaluation (research note)
PE_CE_CORE_FEATURES = frozenset({"popularity", "win_odds", "expected_popularity"})

# Thresholds (research gates — not product adoption)
REVIEW_THRESHOLDS = {
    "leak_risk_fail": 0.85,
    "leak_risk_warn": 0.55,
    "min_n_pass": 40,
    "min_n_warn": 20,
    "min_segment_diversity": 2,
    "max_knowledge_drift_fail": 0.15,
    "max_knowledge_drift_warn": 0.08,
    "min_reliability_pass": 65.0,
    "min_reliability_warn": 55.0,
    "min_coverage_pass": 0.70,
    "min_coverage_warn": 0.40,
    "min_shadow_strict_pass": 0.25,
    "min_shadow_strict_warn": 0.18,
    "min_stability_pass": 0.55,
    "min_stability_warn": 0.40,
    "max_weekly_drift_fail": 0.35,
    "max_weekly_drift_warn": 0.20,
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _verdict_rank(v: str) -> int:
    return {"PASS": 0, "WARNING": 1, "FAIL": 2}.get(v, 3)


def _worst(*verdicts: str) -> str:
    return max(verdicts, key=_verdict_rank)


def _features_from_entry(entry: dict[str, Any], validation: dict[str, Any]) -> list[str]:
    feats = list((entry.get("graph") or {}).get("features") or [])
    flag = validation.get("shadow_flag") or {}
    if flag.get("feature_id"):
        feats.append(str(flag["feature_id"]))
    for k in (flag.get("rules") or {}):
        feats.append(str(k))
    source = str(validation.get("source_key") or entry.get("source_key") or "")
    m = re.search(r"feature:[^:]+:([a-z_]+)", source)
    if m:
        feats.append(m.group(1))
    # pattern features
    if "popularity=" in source or "popularity|" in source:
        feats.append("popularity")
    if "win_odds" in source:
        feats.append("win_odds")
    if "sire=" in source:
        feats.append("sire")
    out = []
    seen = set()
    for f in feats:
        if f and f not in seen and f not in {"surface", "distance_bucket", "going", "weather", "venue"}:
            # keep race axes separate but include for context
            seen.add(f)
            out.append(f)
    # also include race axes if in rules
    for f in feats:
        if f in {"surface", "distance_bucket", "going"} and f not in seen:
            seen.add(f)
            out.append(f)
    return out


class ProductionCandidateReview:
    def __init__(self) -> None:
        migrate()
        self.root = repo_root()
        self.evidence = evidence_root()

    def _load_v19(self) -> dict[str, Any]:
        return _load_json(self.evidence / "reports" / "v19-knowledge-validation.json")

    def _load_v18(self) -> dict[str, Any]:
        return _load_json(self.evidence / "reports" / "v18-knowledge-base.json")

    def _load_v17(self) -> dict[str, Any]:
        return _load_json(self.evidence / "reports" / "v17-evidence-discovery.json")

    def _load_v14(self) -> dict[str, Any]:
        return _load_json(self.evidence / "reports" / "v14-evidence-reliability.json")

    def _load_atlas(self) -> dict[str, Any]:
        for name in ("v16-weakness-atlas.json", "v15-weakness-atlas.json"):
            data = _load_json(self.evidence / "reports" / name)
            if data:
                return data
        return {}

    def _kb_index(self, v18: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return {e["knowledge_id"]: e for e in (v18.get("entries") or []) if e.get("knowledge_id")}

    def _reliability_index(self, v14: dict[str, Any]) -> dict[str, dict[str, Any]]:
        out = {}
        for f in v14.get("features") or []:
            fid = str(f.get("feature_id") or "")
            if fid:
                out[fid] = f
        return out

    def _production_candidates(
        self, v19: dict[str, Any]
    ) -> list[dict[str, Any]]:
        conn = connect()
        try:
            db_ids = {
                r[0]
                for r in conn.execute(
                    """
                    SELECT knowledge_id FROM research_knowledge_states
                    WHERE state='Production_Candidate'
                    """
                ).fetchall()
            }
        finally:
            conn.close()
        vals = []
        for v in v19.get("validations") or []:
            kid = v.get("knowledge_id")
            if v.get("state_after") == "Production_Candidate" or kid in db_ids:
                vals.append(v)
        # unique by knowledge_id
        seen = set()
        out = []
        for v in vals:
            kid = v.get("knowledge_id")
            if kid in seen:
                continue
            seen.add(kid)
            out.append(v)
        return out

    def _dim_leak_risk(
        self, features: list[str], rel_idx: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        risks = []
        asof = []
        for f in features:
            m = rel_idx.get(f) or {}
            if m.get("leak_risk") is not None:
                risks.append(float(m["leak_risk"]))
            # temporal / asof proxy from V14 fields if present
            if m.get("asof_clamped_rate") is not None:
                asof.append(float(m["asof_clamped_rate"]))
            elif m.get("temporal_bias") is not None:
                asof.append(float(m["temporal_bias"]))
        max_leak = max(risks) if risks else 0.7  # conservative floor from V14
        mean_asof = sum(asof) / len(asof) if asof else None
        th = REVIEW_THRESHOLDS
        if max_leak >= th["leak_risk_fail"]:
            verdict = "FAIL"
        elif max_leak >= th["leak_risk_warn"] or (mean_asof is not None and mean_asof >= 0.95):
            verdict = "WARNING"
        else:
            verdict = "PASS"
        return {
            "dimension": "leak_risk",
            "verdict": verdict,
            "max_leak_risk": round(max_leak, 4),
            "mean_asof_or_temporal": round(mean_asof, 4) if mean_asof is not None else None,
            "features": features,
            "note": (
                "V14 reports high asof_clamped / leak floor across Evidence features; "
                "market features may still be pre-race but require asof audit before PE/CE use."
            ),
        }

    def _dim_generalization(
        self,
        validation: dict[str, Any],
        entry: dict[str, Any],
        v17: dict[str, Any],
    ) -> dict[str, Any]:
        m = validation.get("metrics") or {}
        n = int(m.get("n") or 0)
        ktype = validation.get("knowledge_type") or entry.get("knowledge_type")
        segments = list((entry.get("graph") or {}).get("segments") or [])
        source = str(validation.get("source_key") or "")
        # ALL segment is broad; interaction patterns are narrower
        diversity = max(len(segments), 1 if "ALL" in source or ":ALL:" in source else 0)
        if ktype == "feature" and ":ALL:" in source:
            diversity = max(diversity, 3)  # global feature — broader
        th = REVIEW_THRESHOLDS
        if n < th["min_n_warn"]:
            verdict = "FAIL"
        elif n < th["min_n_pass"] or (ktype == "interaction" and n < 40):
            verdict = "WARNING"
        else:
            verdict = "PASS"
        # mined interaction with weak sire bin may overfit
        if "SIRE_WEAK" in source or "TRAINER_WEAK" in source:
            verdict = _worst(verdict, "WARNING")
        return {
            "dimension": "generalization",
            "verdict": verdict,
            "n": n,
            "knowledge_type": ktype,
            "segment_hints": segments,
            "diversity_proxy": diversity,
            "note": (
                "Small Evidence corpus (exploratory) limits out-of-sample claims; "
                "interaction patterns need multi-season confirmation."
            ),
        }

    def _dim_pe_ce_alignment(
        self, features: list[str], validation: dict[str, Any]
    ) -> dict[str, Any]:
        core = [f for f in features if f in PE_CE_CORE_FEATURES]
        novel = [f for f in features if f not in PE_CE_CORE_FEATURES]
        ktype = validation.get("knowledge_type")
        # Already-core market features: redundant with PE/CE if adopted as new AI score inputs
        if core and not novel:
            verdict = "WARNING"
            note = (
                "Candidate relies only on PE/CE-core market signals (popularity/odds). "
                "Implementing as new AI Score risks double-counting market prior; "
                "prefer Shadow monitoring or explicit PE integration design — not a new CE feature."
            )
        elif core and novel:
            verdict = "WARNING"
            note = (
                "Candidate mixes PE/CE-core market signals with non-core features. "
                "Design must define ownership (PE market layer vs CE feature) to avoid conflict."
            )
        elif novel:
            verdict = "PASS"
            note = (
                "Candidate features are outside PE/CE market core; "
                "still requires interface design before any product wiring."
            )
        else:
            verdict = "WARNING"
            note = "Feature set unclear relative to PE/CE; clarify ownership before V21."
        # winner-slice observational knowledge is not an implementable PE/CE feature
        if ktype == "winner":
            verdict = _worst(verdict, "WARNING")
            note += " Winner-slice knowledge is observational, not a direct PE/CE parameter."
        return {
            "dimension": "pe_ce_alignment",
            "verdict": verdict,
            "pe_ce_core_features": core,
            "non_core_features": novel,
            "note": note,
        }

    def _dim_shadow_reproducibility(self, validation: dict[str, Any]) -> dict[str, Any]:
        m = validation.get("metrics") or {}
        gov = validation.get("governance") or {}
        n = int(m.get("n") or 0)
        strict = float(m.get("strict_rate") or 0)
        improvement = m.get("strict_improvement")
        passed = bool(gov.get("passed") or validation.get("passed"))
        th = REVIEW_THRESHOLDS
        if not passed or n < th["min_n_warn"]:
            verdict = "FAIL"
        elif strict < th["min_shadow_strict_warn"]:
            verdict = "FAIL"
        elif strict < th["min_shadow_strict_pass"] or (
            improvement is not None and float(improvement) < 0
        ):
            verdict = "WARNING"
        else:
            verdict = "PASS"
        return {
            "dimension": "shadow_reproducibility",
            "verdict": verdict,
            "shadow_n": n,
            "strict_rate": strict,
            "strict_improvement": improvement,
            "governance_passed": passed,
            "shadow_outcomes": m.get("shadow_outcomes"),
            "note": "Shadow metrics come from V19 Knowledge Validation Lab (research-only flags).",
        }

    def _dim_corpus_drift(
        self, v17: dict[str, Any], atlas: dict[str, Any]
    ) -> dict[str, Any]:
        sample = v17.get("sample") or atlas.get("sample") or {}
        exploratory = bool(sample.get("exploratory"))
        with_evidence = int(sample.get("with_evidence") or sample.get("evaluable") or 0)
        unique = int(sample.get("unique_races") or sample.get("prediction_corpus") or 0)
        # unknown mass from atlas
        unk_share = 0.0
        for axis in ("age_group", "race_type", "class_family"):
            rows = (atlas.get("by_axis") or {}).get(axis) or []
            total = sum(int(r.get("n") or 0) for r in rows) or 1
            unk = next((r for r in rows if r.get("segment") == "unknown"), None)
            if unk:
                unk_share = max(unk_share, float(unk.get("n") or 0) / total)
        if exploratory and with_evidence < 80:
            verdict = "WARNING"
        elif unk_share >= 0.5:
            verdict = "WARNING"
        elif unique < 200:
            verdict = "WARNING"
        else:
            verdict = "PASS"
        if with_evidence < 30:
            verdict = "FAIL"
        return {
            "dimension": "corpus_drift",
            "verdict": verdict,
            "unique_races": unique,
            "with_evidence": with_evidence,
            "exploratory_corpus": exploratory,
            "max_unknown_share_proxy": round(unk_share, 4),
            "note": (
                "Corpus still exploratory; class/age unknown mass remains a drift risk "
                "for segment-conditioned Candidates."
            ),
        }

    def _dim_knowledge_drift(self, validation: dict[str, Any]) -> dict[str, Any]:
        m = validation.get("metrics") or {}
        drift = m.get("knowledge_drift")
        th = REVIEW_THRESHOLDS
        if drift is None:
            verdict = "WARNING"
        elif float(drift) >= th["max_knowledge_drift_fail"]:
            verdict = "FAIL"
        elif float(drift) >= th["max_knowledge_drift_warn"]:
            verdict = "WARNING"
        else:
            verdict = "PASS"
        return {
            "dimension": "knowledge_drift",
            "verdict": verdict,
            "knowledge_drift": drift,
            "discovery_hit_rate": m.get("discovery_hit_rate"),
            "shadow_strict_rate": m.get("strict_rate"),
            "note": "Drift = |discovery hit_rate − shadow strict_rate| from V19.",
        }

    def _dim_evidence_quality(
        self,
        features: list[str],
        validation: dict[str, Any],
        rel_idx: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        m = validation.get("metrics") or {}
        cov = m.get("coverage")
        rel_scores = []
        for f in features:
            meta = rel_idx.get(f) or {}
            if meta.get("reliability_score") is not None:
                rel_scores.append(float(meta["reliability_score"]))
        mean_rel = sum(rel_scores) / len(rel_scores) if rel_scores else (
            float(m["reliability"]) if m.get("reliability") is not None else None
        )
        th = REVIEW_THRESHOLDS
        verdict = "PASS"
        if mean_rel is not None and mean_rel < th["min_reliability_warn"]:
            verdict = "FAIL"
        elif mean_rel is not None and mean_rel < th["min_reliability_pass"]:
            verdict = "WARNING"
        if cov is not None:
            if float(cov) < th["min_coverage_warn"]:
                verdict = _worst(verdict, "FAIL")
            elif float(cov) < th["min_coverage_pass"]:
                verdict = _worst(verdict, "WARNING")
        return {
            "dimension": "evidence_quality",
            "verdict": verdict,
            "mean_reliability": round(mean_rel, 2) if mean_rel is not None else None,
            "shadow_coverage": cov,
            "feature_reliabilities": {
                f: (rel_idx.get(f) or {}).get("reliability_score") for f in features
            },
            "note": "Reliability from V14 Evidence Reliability Research.",
        }

    def _dim_long_term_stability(
        self,
        features: list[str],
        rel_idx: dict[str, dict[str, Any]],
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        stabilities = []
        weekly = []
        for f in features:
            meta = rel_idx.get(f) or {}
            if meta.get("stability") is not None:
                stabilities.append(float(meta["stability"]))
            if meta.get("weekly_drift") is not None:
                weekly.append(float(meta["weekly_drift"]))
        mean_stab = sum(stabilities) / len(stabilities) if stabilities else None
        max_wd = max(weekly) if weekly else None
        th = REVIEW_THRESHOLDS
        verdict = "PASS"
        if mean_stab is not None and mean_stab < th["min_stability_warn"]:
            verdict = "FAIL"
        elif mean_stab is not None and mean_stab < th["min_stability_pass"]:
            verdict = "WARNING"
        if max_wd is not None and max_wd >= th["max_weekly_drift_fail"]:
            verdict = _worst(verdict, "FAIL")
        elif max_wd is not None and max_wd >= th["max_weekly_drift_warn"]:
            verdict = _worst(verdict, "WARNING")
        # single validation week → limited history
        if mean_stab is None and max_wd is None:
            verdict = _worst(verdict, "WARNING")
        return {
            "dimension": "long_term_stability",
            "verdict": verdict,
            "mean_stability": round(mean_stab, 4) if mean_stab is not None else None,
            "max_weekly_drift": round(max_wd, 4) if max_wd is not None else None,
            "validation_weeks_observed": 1,
            "note": (
                "Long-term stability inferred mainly from V14 weekly_drift/stability; "
                "multi-week V19 revalidation history is still thin."
            ),
        }

    def review_one(
        self,
        validation: dict[str, Any],
        entry: dict[str, Any],
        *,
        rel_idx: dict[str, dict[str, Any]],
        v17: dict[str, Any],
        atlas: dict[str, Any],
    ) -> dict[str, Any]:
        features = _features_from_entry(entry, validation)
        dims = [
            self._dim_leak_risk(features, rel_idx),
            self._dim_generalization(validation, entry, v17),
            self._dim_pe_ce_alignment(features, validation),
            self._dim_shadow_reproducibility(validation),
            self._dim_corpus_drift(v17, atlas),
            self._dim_knowledge_drift(validation),
            self._dim_evidence_quality(features, validation, rel_idx),
            self._dim_long_term_stability(features, rel_idx, validation),
        ]
        overall = "PASS"
        for d in dims:
            overall = _worst(overall, d["verdict"])

        promote = overall == "PASS"
        risk = {
            "top_risks": [
                {
                    "dimension": d["dimension"],
                    "verdict": d["verdict"],
                    "note": d.get("note"),
                }
                for d in dims
                if d["verdict"] in {"FAIL", "WARNING"}
            ],
            "features": features,
            "forbid_product_mutation": True,
        }
        adoption = {
            "promote_v21": promote,
            "v21_label": "V21_Implementation_Candidate" if promote else None,
            "recommended_next": (
                "Eligible for Version21 design/implementation ticket (still no auto-deploy)."
                if promote
                else (
                    "Hold — address FAIL/WARNING dimensions before any AI wiring. "
                    "Remain Production_Candidate or demote to Watch/Research."
                )
            ),
            "pe_ce_note": next(
                (d.get("note") for d in dims if d["dimension"] == "pe_ce_alignment"),
                "",
            ),
        }
        return {
            "knowledge_id": validation.get("knowledge_id"),
            "knowledge_type": validation.get("knowledge_type"),
            "source_key": validation.get("source_key") or entry.get("source_key"),
            "observation": entry.get("observation") or validation.get("observation"),
            "hypothesis": entry.get("hypothesis") or validation.get("hypothesis"),
            "shadow_metrics": validation.get("metrics"),
            "rank_score": validation.get("rank_score"),
            "dimensions": {d["dimension"]: d for d in dims},
            "dimension_list": dims,
            "overall_verdict": overall,
            "promote_v21": promote,
            "risk": risk,
            "adoption": adoption,
        }

    def run(self) -> dict[str, Any]:
        started = _now()
        week = _week_id()
        run_id = f"pcr-{uuid.uuid4().hex[:12]}"
        v19 = self._load_v19()
        v18 = self._load_v18()
        v17 = self._load_v17()
        v14 = self._load_v14()
        atlas = self._load_atlas()
        kb = self._kb_index(v18)
        rel_idx = self._reliability_index(v14)
        candidates = self._production_candidates(v19)

        reviews = []
        for v in candidates:
            kid = v.get("knowledge_id")
            entry = kb.get(kid) or {
                "knowledge_id": kid,
                "knowledge_type": v.get("knowledge_type"),
                "source_key": v.get("source_key"),
                "observation": v.get("observation"),
                "hypothesis": v.get("hypothesis"),
                "graph": (v.get("shadow_flag") and {"features": []}) or {},
            }
            # enrich graph from flag
            if not entry.get("graph"):
                entry["graph"] = {}
            flag = v.get("shadow_flag") or {}
            if flag.get("feature_id"):
                entry.setdefault("graph", {}).setdefault("features", [])
                if flag["feature_id"] not in entry["graph"]["features"]:
                    entry["graph"]["features"].append(flag["feature_id"])
            reviews.append(
                self.review_one(v, entry, rel_idx=rel_idx, v17=v17, atlas=atlas)
            )

        reviews.sort(
            key=lambda r: (
                _verdict_rank(r["overall_verdict"]),
                -(r.get("rank_score") or 0),
            )
        )

        now = _now()
        conn = connect()
        try:
            for r in reviews:
                kid = r["knowledge_id"]
                rid = f"rev-{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO research_candidate_reviews(
                      review_id, run_id, knowledge_id, verdict, dimension_json,
                      risk_json, adoption_json, promote_v21, created_at
                    ) VALUES (?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        rid,
                        run_id,
                        kid,
                        r["overall_verdict"],
                        json.dumps(r["dimensions"], ensure_ascii=False),
                        json.dumps(r["risk"], ensure_ascii=False),
                        json.dumps(r["adoption"], ensure_ascii=False),
                        int(r["promote_v21"]),
                        now,
                    ),
                )
                if r["promote_v21"]:
                    conn.execute(
                        """
                        INSERT INTO research_knowledge_states(
                          knowledge_id, state, recommended_action, updated_at, meta_json
                        ) VALUES (?,?,?,?,?)
                        ON CONFLICT(knowledge_id) DO UPDATE SET
                          state=excluded.state,
                          updated_at=excluded.updated_at,
                          meta_json=excluded.meta_json
                        """,
                        (
                            kid,
                            "V21_Implementation_Candidate",
                            "Candidate",
                            now,
                            json.dumps(
                                {
                                    "review_run": run_id,
                                    "verdict": "PASS",
                                    "product_mutation": "FORBIDDEN_until_v21_ticket",
                                },
                                ensure_ascii=False,
                            ),
                        ),
                    )
                    # history
                    try:
                        conn.execute(
                            """
                            INSERT INTO research_knowledge_validation_history(
                              history_id, knowledge_id, run_id, week_id, event,
                              state_before, state_after, detail_json, created_at
                            ) VALUES (?,?,?,?,?,?,?,?,?)
                            """,
                            (
                                f"hist-{uuid.uuid4().hex[:12]}",
                                kid,
                                run_id,
                                week,
                                "v20_promote_v21_label",
                                "Production_Candidate",
                                "V21_Implementation_Candidate",
                                json.dumps(
                                    {"verdict": r["overall_verdict"]},
                                    ensure_ascii=False,
                                ),
                                now,
                            ),
                        )
                    except Exception:
                        pass
                else:
                    # keep Production_Candidate; annotate review fail/warn
                    conn.execute(
                        """
                        INSERT INTO research_knowledge_states(
                          knowledge_id, state, recommended_action, updated_at, meta_json
                        ) VALUES (?,?,?,?,?)
                        ON CONFLICT(knowledge_id) DO UPDATE SET
                          updated_at=excluded.updated_at,
                          meta_json=excluded.meta_json
                        """,
                        (
                            kid,
                            "Production_Candidate",
                            "Watch" if r["overall_verdict"] == "WARNING" else "Candidate",
                            now,
                            json.dumps(
                                {
                                    "review_run": run_id,
                                    "verdict": r["overall_verdict"],
                                    "promote_v21": False,
                                },
                                ensure_ascii=False,
                            ),
                        ),
                    )

            summary = {
                "week_id": week,
                "reviewed": len(reviews),
                "pass": sum(1 for r in reviews if r["overall_verdict"] == "PASS"),
                "warning": sum(1 for r in reviews if r["overall_verdict"] == "WARNING"),
                "fail": sum(1 for r in reviews if r["overall_verdict"] == "FAIL"),
                "promote_v21": sum(1 for r in reviews if r["promote_v21"]),
            }
            finished = _now()
            conn.execute(
                """
                INSERT INTO research_candidate_review_runs(
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

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": finished,
            "run_id": run_id,
            "week_id": week,
            "prediction_mutation": "FORBIDDEN",
            "ai_mutation": "FORBIDDEN",
            "production_mutation": "FORBIDDEN",
            "summary": summary,
            "thresholds": REVIEW_THRESHOLDS,
            "reviews": reviews,
            "v21_candidates": [r for r in reviews if r["promote_v21"]],
            "held": [r for r in reviews if not r["promote_v21"]],
        }


def write_review_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    s = report.get("summary") or {}
    lines = [
        "# Version20 Research - Production Candidate Review",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"**Run:** `{report.get('run_id')}`  ",
        f"**Week:** `{report.get('week_id')}`  ",
        "**Scope:** Design review only / AI & Prediction FORBIDDEN  ",
        "",
        "## Summary",
        "",
        f"- Reviewed: `{s.get('reviewed')}`",
        f"- PASS: `{s.get('pass')}` → V21 Implementation Candidate",
        f"- WARNING: `{s.get('warning')}` (hold)",
        f"- FAIL: `{s.get('fail')}` (hold)",
        f"- Promoted V21 label: `{s.get('promote_v21')}`",
        "",
        "## Review dimensions",
        "",
        "1. Leak Risk",
        "2. Generalization",
        "3. Existing PE/CE alignment",
        "4. Shadow reproducibility",
        "5. Corpus Drift",
        "6. Knowledge Drift",
        "7. Evidence Quality",
        "8. Long-term Stability",
        "",
        "## Candidates",
        "",
    ]
    for r in report.get("reviews") or []:
        lines.extend(
            [
                f"### `{r.get('knowledge_id')}` — **{r.get('overall_verdict')}**",
                "",
                f"- Type: `{r.get('knowledge_type')}`",
                f"- Source: `{r.get('source_key')}`",
                f"- Promote V21: `{r.get('promote_v21')}`",
                f"- Observation: {r.get('observation')}",
                "",
                "| Dimension | Verdict |",
                "|-----------|---------|",
            ]
        )
        for d in r.get("dimension_list") or []:
            lines.append(f"| `{d.get('dimension')}` | **{d.get('verdict')}** |")
        lines.append("")
    lines.extend(
        [
            "## Guardrails",
            "",
            "- No Prediction / PE / CE / AI / Resolver / Production changes",
            "- PASS-only → research label `V21_Implementation_Candidate`",
            "- Implementation remains a separate ticket",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_adoption_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Version20 Research - Adoption Review",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "## V21 Implementation Candidates (PASS only)",
        "",
    ]
    v21 = report.get("v21_candidates") or []
    if not v21:
        lines.append("_None passed all eight design-review dimensions in this run._")
        lines.append("")
    for r in v21:
        a = r.get("adoption") or {}
        lines.extend(
            [
                f"### `{r.get('knowledge_id')}`",
                "",
                f"- Next: {a.get('recommended_next')}",
                f"- PE/CE note: {a.get('pe_ce_note')}",
                f"- Shadow Strict: {_pct((r.get('shadow_metrics') or {}).get('strict_rate'))}",
                "",
            ]
        )
    lines.extend(
        [
            "## Held (WARNING / FAIL)",
            "",
            "| ID | Verdict | Next |",
            "|----|---------|------|",
        ]
    )
    for r in report.get("held") or []:
        a = r.get("adoption") or {}
        lines.append(
            f"| `{r.get('knowledge_id')}` | {r.get('overall_verdict')} | "
            f"{str(a.get('recommended_next') or '')[:80]} |"
        )
    lines.extend(
        [
            "",
            "## Adoption policy",
            "",
            "```",
            "PASS → V21_Implementation_Candidate (research label)",
            "WARNING/FAIL → hold (no AI wiring)",
            "Product mutation: FORBIDDEN in V20",
            "```",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_risk_md(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Version20 Research - Risk Analysis",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "## Thresholds",
        "",
        f"```json\n{json.dumps(report.get('thresholds') or {}, ensure_ascii=False, indent=2)}\n```",
        "",
        "## Per-candidate risks",
        "",
    ]
    for r in report.get("reviews") or []:
        lines.append(f"### `{r.get('knowledge_id')}` ({r.get('overall_verdict')})")
        lines.append("")
        risks = (r.get("risk") or {}).get("top_risks") or []
        if not risks:
            lines.append("- No WARNING/FAIL dimensions.")
        for x in risks:
            lines.append(
                f"- **{x.get('verdict')}** `{x.get('dimension')}` — {x.get('note')}"
            )
        lines.append("")
        # dimension detail snippets
        for d in r.get("dimension_list") or []:
            if d.get("verdict") == "PASS":
                continue
            lines.append(
                f"  - detail `{d.get('dimension')}`: "
                f"{json.dumps({k: v for k, v in d.items() if k not in {'note', 'dimension'}}, ensure_ascii=False)}"
            )
        lines.append("")
    lines.extend(
        [
            "## Cross-cutting risks",
            "",
            "- Evidence corpus remains exploratory (limited snapshot coverage).",
            "- V14 leak_risk / asof_clamped floor affects all Evidence features.",
            "- Market features (popularity/odds) already live in PE/CE — double-counting risk.",
            "- Interaction bins (e.g. SIRE_WEAK) may encode selection bias, not causal edge.",
            "",
            "## Decision",
            "",
            "```",
            "Action Type: Production Candidate Design Review (Research)",
            "AI Mutation: FORBIDDEN",
            "Prediction Mutation: FORBIDDEN",
            "PASS-only → Version21 implementation ticket input",
            "```",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write() -> dict[str, Any]:
    report = ProductionCandidateReview().run()
    docs = repo_root() / "docs" / "research"
    docs.mkdir(parents=True, exist_ok=True)
    write_review_md(report, docs / "v20-production-candidate-review.md")
    write_adoption_md(report, docs / "v20-adoption-review.md")
    write_risk_md(report, docs / "v20-risk-analysis.md")
    json_path = evidence_root() / "reports" / "v20-production-candidate-review.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {
        "review": str(docs / "v20-production-candidate-review.md"),
        "adoption": str(docs / "v20-adoption-review.md"),
        "risk": str(docs / "v20-risk-analysis.md"),
        "json": str(json_path),
    }
    return report
