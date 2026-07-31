# -*- coding: utf-8 -*-
"""
Version22 Continuous Research Operation

Orchestrate existing V10–21 Research Platform weekly.
Does NOT add discovery modules or mutate product surfaces.

FORBIDDEN to mutate:
  Prediction / PE / CE / AI Score / Challenge / Resolver /
  Shadow / ResultAutomation / Production

FORBIDDEN:
  New research discovery modules
"""
from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .config import evidence_root, repo_root

SCHEMA_VERSION = "expect-continuous-research-operation/1.0"

# Knowledge maturity → human Review Queue only (no AI implementation)
MATURITY_GATE = {
    "confidence": "High",
    "min_n": 100,
    "min_coverage": 0.90,
    "min_reliability": 80.0,
    "max_leak_risk_pass": 0.55,  # below V20 warn → PASS
    "wilson_min_low": 0.12,  # Wilson 95% lower bound floor
    "require_wilson": True,
    "governance_pass": True,
}

CONFIDENCE_ORDER = {"Exploratory": 0, "Low": 1, "Medium": 2, "High": 3}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _week_id(dt: datetime | None = None) -> str:
    d = dt or datetime.now(timezone.utc)
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_float(v: Any, default: float | None = None) -> float | None:
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _pct(v: Any) -> str:
    if v is None:
        return "N/A"
    try:
        return f"{100.0 * float(v):.1f}%"
    except (TypeError, ValueError):
        return "N/A"


# ---------------------------------------------------------------------------
# Maturity / Review Queue (pure helpers — no product side effects)
# ---------------------------------------------------------------------------


def evaluate_maturity(
    entry: dict[str, Any],
    *,
    leak_risk: float | None,
    governance_pass: bool,
    gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return per-criterion checks + overall mature flag."""
    g = gate or MATURITY_GATE
    ev = entry.get("evidence") or {}
    n = int(ev.get("n") or 0)
    coverage = _safe_float(ev.get("coverage"))
    reliability = _safe_float(ev.get("reliability"))
    wci = ev.get("wilson_ci") or {}
    lo = _safe_float(wci.get("low"))
    hi = _safe_float(wci.get("high"))
    conf = entry.get("confidence")

    checks = {
        "confidence_high": conf == g["confidence"],
        "evidence_n": n >= int(g["min_n"]),
        "wilson95": (
            lo is not None
            and hi is not None
            and lo >= float(g["wilson_min_low"])
            if g.get("require_wilson")
            else True
        ),
        "coverage": coverage is not None and coverage >= float(g["min_coverage"]),
        "leak_risk_pass": (
            leak_risk is not None and leak_risk < float(g["max_leak_risk_pass"])
        ),
        "reliability": (
            reliability is not None and reliability >= float(g["min_reliability"])
        ),
        "governance_pass": bool(governance_pass) if g.get("governance_pass") else True,
    }
    return {
        "knowledge_id": entry.get("knowledge_id"),
        "source_key": entry.get("source_key"),
        "observation": entry.get("observation"),
        "confidence": conf,
        "checks": checks,
        "mature": all(checks.values()),
        "evidence": {
            "n": n,
            "coverage": coverage,
            "reliability": reliability,
            "wilson_ci": {"low": lo, "high": hi},
            "leak_risk": leak_risk,
        },
        "governance_pass": governance_pass,
    }


def build_review_queue(
    entries: list[dict[str, Any]],
    *,
    leak_by_feature: dict[str, float],
    validation_by_id: dict[str, dict[str, Any]],
    review_by_id: dict[str, dict[str, Any]],
    resolver_status: str | None,
) -> list[dict[str, Any]]:
    """Human-only queue. Never triggers AI/Prediction implementation."""
    queue: list[dict[str, Any]] = []
    resolver_ok = resolver_status != "rejected"

    for entry in entries:
        kid = str(entry.get("knowledge_id") or "")
        features = ((entry.get("graph") or {}).get("features") or [])
        leak_vals = [
            leak_by_feature[f]
            for f in features
            if f in leak_by_feature and leak_by_feature[f] is not None
        ]
        leak = max(leak_vals) if leak_vals else None
        # fallback: unlabeled entries use global worst if features empty
        if leak is None and leak_by_feature:
            leak = max(leak_by_feature.values())

        vrow = validation_by_id.get(kid) or {}
        rrow = review_by_id.get(kid) or {}
        v_pass = bool(vrow.get("passed"))
        state = vrow.get("state_after")
        if rrow:
            gov = v_pass and rrow.get("overall_verdict") == "PASS" and resolver_ok
        elif state in {"Validated", "Production_Candidate"}:
            gov = v_pass and resolver_ok
        else:
            # High knowledge not yet in Candidate pipeline cannot clear Governance
            gov = False

        result = evaluate_maturity(entry, leak_risk=leak, governance_pass=gov)
        if result["mature"]:
            result["review_status"] = "human_pending"
            result["ai_implementation"] = False
            result["state_after"] = state
            result["v20_verdict"] = rrow.get("overall_verdict")
            queue.append(result)
    return queue


def weakness_rank_changes(
    prev_map: list[dict[str, Any]],
    curr_map: list[dict[str, Any]],
    *,
    top_n: int = 30,
) -> list[dict[str, Any]]:
    def key(row: dict[str, Any]) -> str:
        return f"{row.get('axis')}|{row.get('segment')}"

    prev = {key(r): r for r in prev_map if r.get("priority_rank") is not None}
    curr = {key(r): r for r in curr_map if r.get("priority_rank") is not None}
    changes = []
    for k, c in curr.items():
        p = prev.get(k)
        if not p:
            continue
        pr = int(p.get("priority_rank") or 0)
        cr = int(c.get("priority_rank") or 0)
        if pr != cr:
            changes.append(
                {
                    "key": k,
                    "axis": c.get("axis"),
                    "segment": c.get("segment"),
                    "rank_before": pr,
                    "rank_after": cr,
                    "delta": pr - cr,  # positive = improved (rank number down)
                    "weakness_index": c.get("weakness_index"),
                }
            )
    changes.sort(key=lambda x: (-abs(x["delta"]), x["rank_after"]))
    return changes[:top_n]


def candidate_transitions(
    prev_states: dict[str, str],
    curr_states: dict[str, str],
) -> dict[str, list[dict[str, str]]]:
    promote: list[dict[str, str]] = []
    demote: list[dict[str, str]] = []
    order = {
        "Research": 0,
        "Candidate": 1,
        "Validated": 2,
        "Production_Candidate": 3,
        "Rejected": -1,
    }
    all_ids = set(prev_states) | set(curr_states)
    for kid in all_ids:
        before = prev_states.get(kid)
        after = curr_states.get(kid)
        if not after or before == after:
            continue
        b = order.get(before or "Research", 0)
        a = order.get(after, 0)
        row = {"knowledge_id": kid, "before": before or "None", "after": after}
        if after == "Rejected" or (before and a < b):
            demote.append(row)
        elif a > b:
            promote.append(row)
    return {"promote": promote, "demote": demote}


def collect_notifications(
    *,
    weekly_diff: dict[str, Any],
    weakness_changes: list[dict[str, Any]],
    candidate_delta: dict[str, list[dict[str, str]]],
    data_quality: dict[str, Any],
) -> list[dict[str, Any]]:
    """Only the five notification classes requested."""
    notes: list[dict[str, Any]] = []
    for a in weekly_diff.get("added") or []:
        if a.get("confidence") == "High":
            notes.append(
                {
                    "type": "new_high_knowledge",
                    "source_key": a.get("source_key"),
                    "observation": a.get("observation"),
                }
            )
    for ch in weekly_diff.get("changed") or []:
        dconf = (ch.get("deltas") or {}).get("confidence") or {}
        if dconf.get("after") == "High" and dconf.get("before") != "High":
            notes.append(
                {
                    "type": "new_high_knowledge",
                    "source_key": ch.get("source_key"),
                    "knowledge_id": ch.get("knowledge_id"),
                    "via": "confidence_upgrade",
                }
            )
    for w in weakness_changes:
        if abs(int(w.get("delta") or 0)) >= 1:
            notes.append(
                {
                    "type": "weakness_rank_change",
                    "key": w.get("key"),
                    "rank_before": w.get("rank_before"),
                    "rank_after": w.get("rank_after"),
                    "delta": w.get("delta"),
                }
            )
    for p in candidate_delta.get("promote") or []:
        notes.append({"type": "candidate_promote", **p})
    for d in candidate_delta.get("demote") or []:
        notes.append({"type": "candidate_demote", **d})
    if data_quality.get("quality_drop"):
        notes.append(
            {
                "type": "data_quality_drop",
                "detail": data_quality.get("drop_detail"),
                "coverage_before": data_quality.get("coverage_before"),
                "coverage_after": data_quality.get("coverage_after"),
                "reliability_delta": data_quality.get("reliability_delta"),
            }
        )
    return notes


def assess_data_quality(
    *,
    meta_summary: dict[str, Any],
    prev_ops: dict[str, Any],
    reliability_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    cov_after = _safe_float(meta_summary.get("mean_coverage_after"))
    cov_before = _safe_float(meta_summary.get("mean_coverage_before"))
    prev_cov = _safe_float((prev_ops.get("coverage") or {}).get("mean_after"))
    mean_rel = None
    if reliability_rows:
        vals = [
            _safe_float(r.get("reliability_score"))
            for r in reliability_rows
            if r.get("reliability_score") is not None
        ]
        vals = [v for v in vals if v is not None]
        if vals:
            mean_rel = sum(vals) / len(vals)
    prev_rel = _safe_float((prev_ops.get("reliability") or {}).get("mean_score"))
    rel_delta = None
    if mean_rel is not None and prev_rel is not None:
        rel_delta = mean_rel - prev_rel

    drop_reasons = []
    # WoW coverage drop vs previous ops snapshot
    if prev_cov is not None and cov_after is not None and cov_after < prev_cov - 0.03:
        drop_reasons.append("coverage_wow_drop")
    # Within-run meta completion regression (should be rare)
    if (
        cov_before is not None
        and cov_after is not None
        and cov_after + 1e-9 < cov_before
    ):
        drop_reasons.append("coverage_completion_regression")
    if rel_delta is not None and rel_delta < -3.0:
        drop_reasons.append("reliability_wow_drop")

    return {
        "coverage_before": cov_before,
        "coverage_after": cov_after,
        "prev_ops_coverage": prev_cov,
        "mean_reliability": mean_rel,
        "reliability_delta": rel_delta,
        "quality_drop": bool(drop_reasons),
        "drop_detail": drop_reasons,
    }


# ---------------------------------------------------------------------------
# Pipeline — existing modules only
# ---------------------------------------------------------------------------

PipelineStep = tuple[str, Callable[[], Any]]


def _step_prediction_harvest() -> dict[str, Any]:
    """Drain pending predictions into research snapshots (existing collector)."""
    from app.research.collector.runner import ResearchCollectorRunner
    from app.research.config import CollectorSettings

    settings = CollectorSettings.from_env()
    return ResearchCollectorRunner(settings).backfill(batch_size=20, max_rounds=40)


def _step_harvest() -> dict[str, Any]:
    from app.research.collector.runner import ResearchCollectorRunner
    from app.research.config import CollectorSettings

    settings = CollectorSettings.from_env()
    runner = ResearchCollectorRunner(settings)
    once = runner.run_once()
    return {"once": once}


def _step_corpus() -> dict[str, Any]:
    from app.research.prediction_corpus import run_and_write

    return run_and_write()


def _step_corpus_kpi() -> dict[str, Any]:
    """Reuse V23 Corpus Growth reporter (no new research module)."""
    from app.research.corpus_growth import run_and_write

    return run_and_write(report_only=True)


def _step_reliability() -> dict[str, Any]:
    from app.research.evidence_reliability import run_and_write

    return run_and_write()


def _step_metadata() -> dict[str, Any]:
    from app.research.metadata_completion import run_and_write

    return run_and_write()


def _step_discovery() -> dict[str, Any]:
    from app.research.evidence_discovery import run_and_write

    return run_and_write()


def _step_knowledge() -> dict[str, Any]:
    from app.research.knowledge_base import run_and_write

    return run_and_write()


def _step_validation() -> dict[str, Any]:
    from app.research.knowledge_validation import run_and_write

    return run_and_write()


def _step_weakness() -> dict[str, Any]:
    from app.research.weakness_atlas import run_and_write

    return run_and_write()


def _step_pcr() -> dict[str, Any]:
    from app.research.production_candidate_review import run_and_write

    return run_and_write()


def _step_governance() -> dict[str, Any]:
    from app.research.resolver_governance import run_and_write

    return run_and_write()


def _step_weekly_report() -> dict[str, Any]:
    from app.research.weekly_report import generate_weekly_report

    return generate_weekly_report()


DEFAULT_PIPELINE: list[PipelineStep] = [
    ("1_prediction_harvest", _step_prediction_harvest),
    ("2_evidence_harvest", _step_harvest),
    ("3_prediction_corpus", _step_corpus),
    ("4_evidence_reliability", _step_reliability),
    ("5_metadata_completion", _step_metadata),
    ("6_evidence_discovery", _step_discovery),
    ("7_knowledge_update", _step_knowledge),
    ("8_knowledge_validation", _step_validation),
    ("9_weakness_atlas", _step_weakness),
    ("10_governance", _step_governance),
    ("11_production_candidate_review", _step_pcr),
    ("12_corpus_kpi", _step_corpus_kpi),
    ("13_weekly_research_report", _step_weekly_report),
]


class ContinuousResearchOperation:
    """Weekly ops over existing Research Platform artifacts."""

    def __init__(self) -> None:
        self.root = repo_root()
        self.evidence = evidence_root()
        self.reports = self.evidence / "reports"
        self.ops_dir = self.evidence / "ops" / "weekly"
        self.docs = self.root / "docs" / "research"

    def _prev_ops_snapshot(self, week: str) -> dict[str, Any]:
        self.ops_dir.mkdir(parents=True, exist_ok=True)
        files = sorted(self.ops_dir.glob("*.json"))
        # Prefer previous week file, else last non-current
        candidates = [p for p in files if p.stem != week]
        if not candidates:
            return {}
        return _load_json(candidates[-1])

    def _index_reliability_leaks(self) -> tuple[list[dict[str, Any]], dict[str, float]]:
        rel = _load_json(self.reports / "v14-evidence-reliability.json")
        rows = rel.get("reliability") or rel.get("features") or []
        by_label: dict[str, float] = {}
        for r in rows:
            label = str(r.get("label") or r.get("feature_id") or "")
            leak = _safe_float(r.get("leak_risk"))
            if label and leak is not None:
                by_label[label] = leak
            fid = str(r.get("feature_id") or "")
            if fid and leak is not None:
                by_label[fid] = leak
        return rows, by_label

    def _validation_index(self) -> dict[str, dict[str, Any]]:
        v19 = _load_json(self.reports / "v19-knowledge-validation.json")
        out: dict[str, dict[str, Any]] = {}
        for v in v19.get("validations") or []:
            kid = str(v.get("knowledge_id") or "")
            if kid:
                out[kid] = v
        return out

    def _review_index(self) -> dict[str, dict[str, Any]]:
        v20 = _load_json(self.reports / "v20-production-candidate-review.json")
        out: dict[str, dict[str, Any]] = {}
        for r in (v20.get("reviews") or []) + (v20.get("held") or []) + (
            v20.get("v21_candidates") or []
        ):
            kid = str(r.get("knowledge_id") or "")
            if kid:
                out[kid] = r
        return out

    def _candidate_state_map(self, report: dict[str, Any] | None = None) -> dict[str, str]:
        v19 = report or _load_json(self.reports / "v19-knowledge-validation.json")
        states: dict[str, str] = {}
        for v in v19.get("validations") or []:
            kid = str(v.get("knowledge_id") or "")
            if kid and v.get("state_after"):
                states[kid] = str(v["state_after"])
        return states

    def run_pipeline(
        self,
        *,
        report_only: bool = False,
        skip_steps: set[str] | None = None,
    ) -> dict[str, Any]:
        skip = skip_steps or set()
        step_results: dict[str, Any] = {}
        errors: list[dict[str, str]] = []

        if not report_only:
            for name, fn in DEFAULT_PIPELINE:
                if name in skip:
                    step_results[name] = {"skipped": True}
                    continue
                try:
                    out = fn()
                    # Keep summaries small in ops JSON
                    if isinstance(out, dict):
                        slim = {
                            k: out.get(k)
                            for k in (
                                "ok",
                                "week_id",
                                "run_id",
                                "summary",
                                "sample",
                                "path",
                                "current_status",
                                "eligible",
                                "_outputs",
                            )
                            if k in out
                        }
                        if not slim:
                            slim = {"ok": True, "keys": list(out.keys())[:20]}
                        step_results[name] = slim
                    else:
                        step_results[name] = {"ok": True}
                except Exception as exc:  # noqa: BLE001 — continue weekly ops
                    errors.append(
                        {
                            "step": name,
                            "error": str(exc),
                            "trace": traceback.format_exc()[-800:],
                        }
                    )
                    step_results[name] = {"ok": False, "error": str(exc)}

        return self.assemble_report(step_results=step_results, errors=errors)

    def assemble_report(
        self,
        *,
        step_results: dict[str, Any] | None = None,
        errors: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        now = _now()
        week = _week_id()
        prev_ops = self._prev_ops_snapshot(week)

        kb = _load_json(self.reports / "v18-knowledge-base.json")
        entries = kb.get("entries") or []
        weekly_diff = kb.get("weekly_diff") or {"counts": {}, "added": [], "changed": []}

        meta = _load_json(self.reports / "v16-metadata-completion.json")
        meta_summary = meta.get("summary") or {}

        atlas = _load_json(self.reports / "v15-weakness-atlas.json")
        if not atlas.get("priority_map"):
            atlas = _load_json(self.reports / "v16-weakness-atlas.json")
        curr_priority = atlas.get("priority_map") or []
        prev_priority = (prev_ops.get("weakness") or {}).get("priority_map") or []
        # First ops week: no baseline → no rank-change notifications
        w_changes = (
            weakness_rank_changes(prev_priority, curr_priority)
            if prev_priority
            else []
        )

        rel_rows, leak_by = self._index_reliability_leaks()
        v_idx = self._validation_index()
        r_idx = self._review_index()
        gov = _load_json(self.reports / "v106-resolver-governance.json")
        resolver_status = str(
            gov.get("current_status")
            or ((gov.get("summary") or {}).get("gate") or {}).get("status")
            or ((gov.get("cumulative") or {}).get("gate") or {}).get("status")
            or ""
        )
        if not resolver_status:
            # tolerate alternate shapes from older runs
            for key in ("gate", "adoption_gate"):
                block = gov.get(key) or {}
                if isinstance(block, dict) and block.get("status"):
                    resolver_status = str(block["status"])
                    break

        # Preserve last pipeline detail when assembling report-only
        prev_v22 = _load_json(self.reports / "v22-continuous-research.json")
        report_only_flag = not bool(step_results)
        merged_steps = step_results or (
            (prev_v22.get("pipeline") or {}).get("steps") or {}
        )

        v19 = _load_json(self.reports / "v19-knowledge-validation.json")
        v20 = _load_json(self.reports / "v20-production-candidate-review.json")
        curr_states = self._candidate_state_map(v19)
        prev_states = (prev_ops.get("candidates") or {}).get("states") or {}
        # First ops week: no baseline → suppress promote/demote noise
        if prev_states:
            cand_delta = candidate_transitions(prev_states, curr_states)
        else:
            cand_delta = {"promote": [], "demote": []}

        dq = assess_data_quality(
            meta_summary=meta_summary,
            prev_ops=prev_ops,
            reliability_rows=rel_rows,
        )

        review_queue = build_review_queue(
            entries,
            leak_by_feature=leak_by,
            validation_by_id=v_idx,
            review_by_id=r_idx,
            resolver_status=resolver_status or None,
        )

        notifications = collect_notifications(
            weekly_diff=weekly_diff,
            weakness_changes=w_changes,
            candidate_delta=cand_delta,
            data_quality=dq,
        )

        conf_counts = {"High": 0, "Medium": 0, "Low": 0, "Exploratory": 0}
        for e in entries:
            c = e.get("confidence")
            if c in conf_counts:
                conf_counts[c] += 1

        conf_changes = [
            ch
            for ch in (weekly_diff.get("changed") or [])
            if "confidence" in (ch.get("deltas") or {})
        ]

        # Corpus KPI from V23 reporter / v11 corpus (existing artifacts only)
        corpus_json = _load_json(self.evidence / "corpus" / "v11-prediction-corpus.json")
        growth_json = _load_json(self.reports / "v23-corpus-growth.json")
        growth_after = (growth_json.get("after") or {}) if growth_json else {}
        corpus_kpi = {
            "prediction": growth_after.get("prediction")
            or corpus_json.get("prediction_count"),
            "evidence": growth_after.get("evidence")
            or ((corpus_json.get("coverage") or {}).get("with_evidence_snapshot")),
            "knowledge": len(entries),
            "tie": growth_after.get("tie") or corpus_json.get("tie_count"),
            "young_horse": growth_after.get("young_horse")
            or corpus_json.get("young_horse_count"),
            "coverage": growth_after.get("coverage") or corpus_json.get("coverage"),
            "confidence": conf_counts,
            "cycle_diff": (growth_json.get("cycle_diff") or {}).get("scalar"),
            "wow_diff": (growth_json.get("wow_diff") or {}).get("scalar"),
            "gap": growth_after.get("gap") or corpus_json.get("gap"),
            "segments": (growth_after.get("segments") or {}),
        }

        prev_rq = prev_ops.get("review_queue_n")
        review_queue_delta = {
            "before": prev_rq,
            "after": len(review_queue),
            "delta": (
                None
                if prev_rq is None
                else len(review_queue) - int(prev_rq)
            ),
        }

        report = {
            "schema_version": SCHEMA_VERSION,
            "week_id": week,
            "generated_at": now,
            "mission": "Research Operations (V10–23 platform; no new modules)",
            "causal_claim": "OPERATIONS_ONLY",
            "product_mutation": False,
            "ai_implementation": False,
            "improvement_implementation": False,
            "maturity_gate": MATURITY_GATE,
            "pipeline": {
                "steps": merged_steps,
                "errors": errors or [],
                "report_only": report_only_flag,
            },
            "sample": {
                "knowledge_entries": len(entries),
                "confidence_counts": conf_counts,
                "evidence_snapshots": (
                    (_load_json(self.reports / "v17-evidence-discovery.json").get("sample")
                     or {})
                ),
            },
            "knowledge_diff": {
                "counts": weekly_diff.get("counts") or {},
                "added": weekly_diff.get("added") or [],
                "removed": weekly_diff.get("removed") or [],
                "changed": weekly_diff.get("changed") or [],
                "confidence_changes": conf_changes,
                "new_high": [
                    a
                    for a in (weekly_diff.get("added") or [])
                    if a.get("confidence") == "High"
                ],
            },
            "coverage": {
                "mean_before": meta_summary.get("mean_coverage_before"),
                "mean_after": meta_summary.get("mean_coverage_after"),
                "prev_ops_mean_after": (prev_ops.get("coverage") or {}).get("mean_after"),
            },
            "corpus_kpi": corpus_kpi,
            "weakness": {
                "top": curr_priority[:15],
                "rank_changes": w_changes,
                "priority_map": [
                    {
                        "axis": r.get("axis"),
                        "segment": r.get("segment"),
                        "priority_rank": r.get("priority_rank"),
                        "weakness_index": r.get("weakness_index"),
                        "n_eval": r.get("n_eval"),
                    }
                    for r in curr_priority[:80]
                ],
            },
            "candidates": {
                "summary_v19": v19.get("summary") or {},
                "summary_v20": v20.get("summary") or {},
                "states": curr_states,
                "promote": cand_delta["promote"],
                "demote": cand_delta["demote"],
            },
            "governance": {
                "resolver_status": resolver_status,
                "resolver_eligible": (
                    gov.get("eligible")
                    if gov.get("eligible") is not None
                    else (gov.get("dashboard") or {}).get("eligible")
                ),
                "maturity_gate": MATURITY_GATE,
                "review_queue_n": len(review_queue),
                "review_queue_delta": review_queue_delta,
                "note": (
                    "Governance PASS for Review Queue requires "
                    "V19 passed (+ V20 PASS if reviewed) and resolver not rejected"
                ),
            },
            "reliability": {
                "mean_score": dq.get("mean_reliability"),
                "n_features": len(rel_rows),
            },
            "data_quality": dq,
            "review_queue": review_queue,
            "notifications": notifications,
            "notification_policy": [
                "new_high_knowledge",
                "weakness_rank_change",
                "candidate_promote",
                "candidate_demote",
                "data_quality_drop",
            ],
        }

        # Persist ops snapshot for next WoW
        self.ops_dir.mkdir(parents=True, exist_ok=True)
        snap = {
            "week_id": week,
            "generated_at": now,
            "coverage": report["coverage"],
            "reliability": report["reliability"],
            "weakness": {"priority_map": report["weakness"]["priority_map"]},
            "candidates": {"states": curr_states, "summary_v19": report["candidates"]["summary_v19"]},
            "confidence_counts": conf_counts,
            "review_queue_n": len(review_queue),
            "corpus_kpi": {
                "prediction": corpus_kpi.get("prediction"),
                "evidence": corpus_kpi.get("evidence"),
                "knowledge": corpus_kpi.get("knowledge"),
            },
        }
        (self.ops_dir / f"{week}.json").write_text(
            json.dumps(snap, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        report["_ops_snapshot"] = str(self.ops_dir / f"{week}.json")
        return report


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def write_weekly_md(report: dict[str, Any], path: Path) -> None:
    kd = report.get("knowledge_diff") or {}
    cov = report.get("coverage") or {}
    weak = report.get("weakness") or {}
    cand = report.get("candidates") or {}
    dq = report.get("data_quality") or {}
    notes = report.get("notifications") or []
    ck = report.get("corpus_kpi") or {}
    rq_delta = ((report.get("governance") or {}).get("review_queue_delta") or {})
    lines = [
        "# Research Operations — Weekly Report",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"**Week:** `{report.get('week_id')}`  ",
        "**Scope:** V10–23 Research Platform ops / Improvement implementation FORBIDDEN  ",
        "",
        "## Mission",
        "",
        "Continue operating the existing Research Platform to mature research materials.",
        "No new research modules. No Prediction / PE / CE / AI changes.",
        "",
        "## Pipeline",
        "",
    ]
    pipe = report.get("pipeline") or {}
    for name, res in (pipe.get("steps") or {}).items():
        if res.get("skipped"):
            status = "skipped"
        elif res.get("error"):
            status = f"ok=False error=`{res.get('error')}`"
        elif res.get("ok") is False:
            status = "ok=False"
        else:
            status = "ok=True"
        lines.append(f"- `{name}`: {status}")
    if pipe.get("errors"):
        lines += ["", "### Errors", ""]
        for e in pipe["errors"]:
            lines.append(f"- `{e.get('step')}`: {e.get('error')}")

    lines += [
        "",
        "## 1. 今週追加された Knowledge",
        "",
        f"- Added/Removed/Changed: `{json.dumps(kd.get('counts') or {}, ensure_ascii=False)}`",
        "",
    ]
    added = kd.get("added") or []
    if not added:
        lines.append("- (none)")
    else:
        for a in added[:30]:
            lines.append(
                f"- [{a.get('confidence')}/{a.get('action')}] `{a.get('source_key')}`"
            )

    lines += [
        "",
        "## 2. Confidence 変化",
        "",
        f"- Current: `{json.dumps((report.get('sample') or {}).get('confidence_counts') or {}, ensure_ascii=False)}`",
        f"- Changes: `{len(kd.get('confidence_changes') or [])}`",
        "",
    ]
    chs = kd.get("confidence_changes") or []
    if not chs:
        lines.append("- (none)")
    else:
        for ch in chs[:30]:
            d = (ch.get("deltas") or {}).get("confidence") or {}
            lines.append(
                f"- `{ch.get('knowledge_id')}`: {d.get('before')} → {d.get('after')}"
            )

    lines += [
        "",
        "## 3. Coverage 変化",
        "",
        f"- Metadata mean: `{_pct(cov.get('mean_before'))}` → `{_pct(cov.get('mean_after'))}`",
        f"- Prev ops mean_after: `{_pct(cov.get('prev_ops_mean_after'))}`",
        f"- Data quality drop: `{dq.get('quality_drop')}` `{dq.get('drop_detail')}`",
        "",
        "## 4. Corpus Growth",
        "",
        f"- Prediction: `{ck.get('prediction')}`",
        f"- Evidence: `{ck.get('evidence')}`",
        f"- Knowledge: `{ck.get('knowledge')}`",
        f"- Tie: `{ck.get('tie')}`",
        f"- Young Horse: `{ck.get('young_horse')}`",
        f"- Cycle Δ: `{json.dumps(ck.get('cycle_diff') or {}, ensure_ascii=False)}`",
        f"- WoW Δ: `{json.dumps(ck.get('wow_diff') or {}, ensure_ascii=False)}`",
        f"- Gap: `{json.dumps(ck.get('gap') or {}, ensure_ascii=False)}`",
        "",
        "## 5. Review Queue 変化",
        "",
        f"- Queue N: `{rq_delta.get('before')}` → `{rq_delta.get('after')}` (Δ `{rq_delta.get('delta')}`)",
        f"- Mature entries now: `{(report.get('governance') or {}).get('review_queue_n')}`",
        "- Human review only — AI implementation forbidden",
        "",
        "## Other deltas",
        "",
        f"- Weakness rank changes: `{len(weak.get('rank_changes') or [])}`",
        f"- Candidate promote/demote: `{len(cand.get('promote') or [])}` / `{len(cand.get('demote') or [])}`",
        f"- Resolver governance: `{(report.get('governance') or {}).get('resolver_status')}`",
        "",
        "## Notifications (emitted)",
        "",
    ]
    if not notes:
        lines.append("- (none)")
    else:
        for n in notes[:40]:
            lines.append(f"- `{n.get('type')}`: {json.dumps(n, ensure_ascii=False)}")

    lines += [
        "",
        "## Guardrails",
        "",
        "- Prediction / PE / CE / AI / Resolver / Shadow / ResultAutomation / Production unchanged",
        "- No new research discovery modules",
        "- Improvement implementation forbidden",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_research_ops_md(report: dict[str, Any], path: Path) -> None:
    """Ops-focused one-pager (same data as weekly; explicit Research Operations title)."""
    write_weekly_md(report, path)


def write_knowledge_diff_md(report: dict[str, Any], path: Path) -> None:
    kd = report.get("knowledge_diff") or {}
    lines = [
        "# Version22 — Knowledge Diff",
        "",
        f"**Week:** `{report.get('week_id')}`  ",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        f"Counts: `{json.dumps(kd.get('counts') or {}, ensure_ascii=False)}`",
        "",
        "## New High Knowledge",
        "",
    ]
    highs = kd.get("new_high") or []
    if not highs:
        lines.append("- (none)")
    else:
        for a in highs:
            lines.append(
                f"- `{a.get('source_key')}` — {a.get('observation')}"
            )

    lines += ["", "## Added", ""]
    for a in (kd.get("added") or [])[:30]:
        lines.append(
            f"- [{a.get('confidence')}/{a.get('action')}] `{a.get('source_key')}`"
        )
    if not kd.get("added"):
        lines.append("- (none)")

    lines += ["", "## Confidence changes", ""]
    chs = kd.get("confidence_changes") or []
    if not chs:
        lines.append("- (none)")
    else:
        for ch in chs[:40]:
            d = (ch.get("deltas") or {}).get("confidence") or {}
            lines.append(
                f"- `{ch.get('knowledge_id')}`: {d.get('before')} → {d.get('after')}"
            )

    lines += ["", "## Other changes", ""]
    for ch in (kd.get("changed") or [])[:40]:
        lines.append(
            f"- `{ch.get('knowledge_id')}` deltas=`{json.dumps(ch.get('deltas') or {}, ensure_ascii=False)}`"
        )
    if not kd.get("changed"):
        lines.append("- (none)")

    cov = report.get("coverage") or {}
    weak = report.get("weakness") or {}
    cand = report.get("candidates") or {}
    lines += [
        "",
        "## Coverage change",
        "",
        f"- Mean: `{_pct(cov.get('mean_before'))}` → `{_pct(cov.get('mean_after'))}`",
        f"- Prev ops mean_after: `{_pct(cov.get('prev_ops_mean_after'))}`",
        "",
        "## Weakness rank changes",
        "",
    ]
    if not weak.get("rank_changes"):
        lines.append("- (none — first ops snapshot or unchanged)")
    else:
        lines.append("| Key | Before | After | Δ |")
        lines.append("|-----|-------:|------:|--:|")
        for w in weak["rank_changes"][:25]:
            lines.append(
                f"| `{w.get('key')}` | {w.get('rank_before')} | {w.get('rank_after')} | {w.get('delta')} |"
            )

    lines += [
        "",
        "## Production Candidate changes",
        "",
        f"- V19 summary: `{json.dumps(cand.get('summary_v19') or {}, ensure_ascii=False)}`",
        f"- V20 summary: `{json.dumps(cand.get('summary_v20') or {}, ensure_ascii=False)}`",
        "",
        "### Promote",
        "",
    ]
    for p in cand.get("promote") or []:
        lines.append(f"- `{p.get('knowledge_id')}`: {p.get('before')} → {p.get('after')}")
    if not cand.get("promote"):
        lines.append("- (none)")
    lines += ["", "### Demote", ""]
    for d in cand.get("demote") or []:
        lines.append(f"- `{d.get('knowledge_id')}`: {d.get('before')} → {d.get('after')}")
    if not cand.get("demote"):
        lines.append("- (none)")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_governance_md(report: dict[str, Any], path: Path) -> None:
    gov = report.get("governance") or {}
    gate = report.get("maturity_gate") or MATURITY_GATE
    dq = report.get("data_quality") or {}
    lines = [
        "# Version22 — Governance Summary",
        "",
        f"**Week:** `{report.get('week_id')}`  ",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "## Resolver Governance (V10.6)",
        "",
        f"- Status: `{gov.get('resolver_status')}`",
        f"- Eligible: `{gov.get('resolver_eligible')}`",
        "",
        "## Knowledge Maturity Gate (Review Queue)",
        "",
        "All criteria required:",
        "",
        f"- Confidence = `{gate.get('confidence')}`",
        f"- Evidence N ≥ `{gate.get('min_n')}`",
        f"- Wilson95% lower ≥ `{gate.get('wilson_min_low')}`",
        f"- Coverage ≥ `{_pct(gate.get('min_coverage'))}`",
        f"- Leak Risk PASS (leak_risk < `{gate.get('max_leak_risk_pass')}`)",
        f"- Reliability ≥ `{gate.get('min_reliability')}`",
        f"- Governance PASS (V19 passed; V20 PASS if reviewed; resolver ≠ rejected)",
        "",
        f"- Review Queue size: `{gov.get('review_queue_n')}`",
        "",
        "## Data Quality",
        "",
        f"- Coverage: `{_pct(dq.get('coverage_before'))}` → `{_pct(dq.get('coverage_after'))}`",
        f"- Mean reliability: `{dq.get('mean_reliability')}` (Δ `{dq.get('reliability_delta')}`)",
        f"- Quality drop: `{dq.get('quality_drop')}` `{dq.get('drop_detail')}`",
        "",
        "## Notifications policy",
        "",
    ]
    for t in report.get("notification_policy") or []:
        lines.append(f"- `{t}`")
    lines += [
        "",
        "## Hard lock",
        "",
        "- AI implementation: **forbidden**",
        "- Prediction / PE / CE / Shadow Resolver: **unchanged**",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_review_queue_md(report: dict[str, Any], path: Path) -> None:
    q = report.get("review_queue") or []
    lines = [
        "# Version22 — Review Queue",
        "",
        f"**Week:** `{report.get('week_id')}`  ",
        f"**Date:** {report.get('generated_at')}  ",
        "",
        "Human review only. **Do not implement into AI / Prediction.**",
        "",
        f"Queued: `{len(q)}`",
        "",
    ]
    if not q:
        lines += [
            "No knowledge entry meets all maturity criteria.",
            "",
            "Typical blockers on current corpus: Evidence N < 100, Coverage < 90%, "
            "Reliability < 80, or Governance not PASS.",
            "",
        ]
    else:
        lines.append("| Knowledge | N | Coverage | Rel | Leak | Wilson lo | State |")
        lines.append("|-----------|--:|---------:|----:|-----:|----------:|-------|")
        for item in q:
            ev = item.get("evidence") or {}
            w = ev.get("wilson_ci") or {}
            lines.append(
                f"| `{item.get('knowledge_id')}` | {ev.get('n')} | "
                f"{_pct(ev.get('coverage'))} | {ev.get('reliability')} | "
                f"{ev.get('leak_risk')} | {w.get('low')} | {item.get('state_after')} |"
            )
        lines += ["", "### Details", ""]
        for item in q:
            lines.append(f"### `{item.get('knowledge_id')}`")
            lines.append(f"- {item.get('observation')}")
            lines.append(f"- checks: `{json.dumps(item.get('checks') or {}, ensure_ascii=False)}`")
            lines.append(f"- ai_implementation: `{item.get('ai_implementation')}`")
            lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write(*, report_only: bool = False) -> dict[str, Any]:
    ops = ContinuousResearchOperation()
    report = ops.run_pipeline(report_only=report_only)

    docs = ops.docs
    docs.mkdir(parents=True, exist_ok=True)
    weekly = docs / "v22-weekly-research.md"
    ops_md = docs / "v22-research-ops.md"
    kdiff = docs / "v22-knowledge-diff.md"
    gov = docs / "v22-governance-summary.md"
    queue = docs / "v22-review-queue.md"
    write_weekly_md(report, weekly)
    write_research_ops_md(report, ops_md)
    write_knowledge_diff_md(report, kdiff)
    write_governance_md(report, gov)
    write_review_queue_md(report, queue)

    json_path = ops.reports / "v22-continuous-research.json"
    ops.reports.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report["_outputs"] = {
        "weekly": str(weekly),
        "research_ops": str(ops_md),
        "knowledge_diff": str(kdiff),
        "governance": str(gov),
        "review_queue": str(queue),
        "json": str(json_path),
    }
    return report
