# -*- coding: utf-8
"""
CLI — Research Evidence Collector (Version10 sidecar).

Usage:
  python -m app.research.collector_runner --once
  python -m app.research.collector_runner --loop
  python -m app.research.collector_runner --weekly-report
  python -m app.research.collector_runner --analyze-evidence
  python -m app.research.collector_runner --reharvest-v103
  python -m app.research.analyzer_runner
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.collector.runner import ResearchCollectorRunner
from app.research.config import CollectorSettings
from app.research.weekly_report import generate_weekly_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Research Evidence Collector")
    parser.add_argument("--once", action="store_true", help="Poll + process one batch")
    parser.add_argument("--loop", action="store_true", help="Run until interrupted")
    parser.add_argument("--backfill", action="store_true", help="Drain all pending predictions")
    parser.add_argument("--weekly-report", action="store_true", help="Generate weekly report")
    parser.add_argument(
        "--analyze-evidence",
        action="store_true",
        help="V10.2 Evidence Analyzer (shadow; does not change Prediction)",
    )
    parser.add_argument(
        "--reharvest-v103",
        action="store_true",
        help="V10.3 re-collect horse/workout features for existing snapshots",
    )
    parser.add_argument(
        "--rank-evidence",
        action="store_true",
        help="V10.4 Evidence Ranking Engine (shadow; no Prediction change)",
    )
    parser.add_argument(
        "--shadow-resolver",
        action="store_true",
        help="V10.5 Shadow Tie Resolver (shadow; no Prediction change)",
    )
    parser.add_argument(
        "--resolver-governance",
        action="store_true",
        help="V10.6 Resolver Governance (shadow adoption gate only)",
    )
    parser.add_argument(
        "--resolver-governance-backfill",
        action="store_true",
        help="V10.7 Resolver Governance Backfill Replay (research-only)",
    )
    parser.add_argument(
        "--build-prediction-corpus",
        action="store_true",
        help="V11 Prediction Corpus Expansion (research-only; no Prediction change)",
    )
    parser.add_argument(
        "--historical-bundle-ingest",
        action="store_true",
        help="V11.1 Historical Bundle Ingest (research-only; no Prediction change)",
    )
    parser.add_argument(
        "--young-horse-intelligence",
        action="store_true",
        help="V12 Young Horse Intelligence Research (research-only; no Score/Resolver)",
    )
    parser.add_argument(
        "--young-horse-archetypes",
        action="store_true",
        help="V13 Young Horse Archetype Research (research-only; no Score/Resolver)",
    )
    parser.add_argument(
        "--evidence-reliability",
        action="store_true",
        help="V14 Evidence Reliability Research (research-only; no Prediction/Resolver)",
    )
    parser.add_argument(
        "--weakness-atlas",
        action="store_true",
        help="V15 Weakness Atlas (research quantification only; no product changes)",
    )
    parser.add_argument(
        "--metadata-completion",
        action="store_true",
        help="V16 Metadata Completion Research (fill unknowns; no product changes)",
    )
    parser.add_argument(
        "--evidence-discovery",
        action="store_true",
        help="V17 Evidence Discovery Research (racing research only; no product changes)",
    )
    parser.add_argument(
        "--knowledge-base",
        action="store_true",
        help="V18 Research Knowledge Base (V17 → Knowledge; no product changes)",
    )
    parser.add_argument(
        "--knowledge-validation",
        action="store_true",
        help="V19 Knowledge Validation Lab (shadow validate Candidates; no product changes)",
    )
    parser.add_argument(
        "--production-candidate-review",
        action="store_true",
        help="V20 Production Candidate Review (design review; no AI/Prediction changes)",
    )
    parser.add_argument(
        "--causal-evidence",
        action="store_true",
        help="V21 Causal Evidence Research (Feature→Condition→Outcome; no product changes)",
    )
    parser.add_argument(
        "--continuous-research",
        action="store_true",
        help="V22 Continuous Research Operation (orchestrate existing V10-21; no new modules)",
    )
    parser.add_argument(
        "--continuous-research-report-only",
        action="store_true",
        help="V22 assemble weekly docs from existing reports without re-running pipeline",
    )
    parser.add_argument(
        "--research-ops",
        action="store_true",
        help="Research Operations alias for --continuous-research (V10-23 platform ops)",
    )
    parser.add_argument(
        "--research-ops-report-only",
        action="store_true",
        help="Research Operations report-only alias",
    )
    parser.add_argument(
        "--corpus-growth",
        action="store_true",
        help="Research Corpus Growth cycle (harvest+rebuild+report; no product changes)",
    )
    parser.add_argument(
        "--corpus-growth-report-only",
        action="store_true",
        help="Corpus Growth report from existing artifacts only",
    )
    parser.add_argument(
        "--world-boundary",
        action="store_true",
        help="V22 Existing World Boundary Research (no new Worlds; no product changes)",
    )
    parser.add_argument(
        "--world-activation",
        action="store_true",
        help="V24 World Activation Research (why Worlds fire; no new Worlds; no product changes)",
    )
    parser.add_argument(
        "--world-signal-instrumentation",
        action="store_true",
        help="V25 World Signal Instrumentation (persist signals to Research Snapshot; no judgment)",
    )
    parser.add_argument(
        "--world-signal-no-core",
        action="store_true",
        help="V25: bundle labels only (skip Core meta score copy)",
    )
    parser.add_argument(
        "--world-signal-limit",
        type=int,
        default=0,
        help="V25: optional snapshot limit for instrumentation backfill",
    )
    parser.add_argument(
        "--world-fitness",
        action="store_true",
        help="V26 World Fitness Analysis (midupper → existing Worlds; research only)",
    )
    parser.add_argument(
        "--chaos-signal-trace",
        action="store_true",
        help="V26 Chaos/World Signal Trace audit (no product changes)",
    )
    parser.add_argument(
        "--world-trigger-saturation",
        action="store_true",
        help="V27 World Trigger Saturation Research (margins/bottlenecks; no Trigger changes)",
    )
    parser.add_argument(
        "--difficulty-signal-audit",
        action="store_true",
        help="V28 Difficulty Signal Audit (distribution/components; research only)",
    )
    parser.add_argument(
        "--signal-lineage-audit",
        action="store_true",
        help="V29 World Signal Lineage Audit (Production vs Research path; audit only)",
    )
    parser.add_argument(
        "--wic-shadow-ab",
        action="store_true",
        help="V34 World Input Contract Shadow AB (research only; no Production/Signal Service)",
    )
    args = parser.parse_args()

    if args.weekly_report:
        report = generate_weekly_report()
        print(json.dumps({"ok": True, "week_id": report.get("week_id"), "path": report.get("path")}, ensure_ascii=False))
        return 0

    if args.analyze_evidence:
        from app.research.analyzer import run_and_write

        report = run_and_write()
        print(
            json.dumps(
                {
                    "ok": True,
                    "n_races": report["corpus"]["n_races"],
                    "outputs": report.get("_outputs"),
                    "ranking": report.get("ranking"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "rank_evidence", False):
        from app.research.ranking_engine import run_and_write as rank_and_write

        report = rank_and_write()
        print(
            json.dumps(
                {
                    "ok": True,
                    "n_tie_races": report["corpus"]["n_tie_races"],
                    "tiers": report["tiers"],
                    "evidence_priority": report["evidence_priority"],
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "shadow_resolver", False):
        from app.research.shadow_resolver import run_and_write as resolver_run_and_write

        report = resolver_run_and_write()
        print(
            json.dumps(
                {
                    "ok": True,
                    "n_tie_races": report["corpus"]["n_tie_races"],
                    "summary": report["summary"],
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "resolver_governance", False):
        from app.research.resolver_governance import (
            run_and_write as governance_run_and_write,
        )

        report = governance_run_and_write()
        print(
            json.dumps(
                {
                    "ok": True,
                    "current_status": report["dashboard"]["current_status"],
                    "eligible": report["dashboard"]["eligible"],
                    "summary": report["cumulative"],
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "resolver_governance_backfill", False):
        from app.research.resolver_governance_backfill import (
            run_and_write as backfill_run_and_write,
        )

        report = backfill_run_and_write()
        print(
            json.dumps(
                {
                    "ok": True,
                    "tie_races_evaluated": report.get("tie_races_evaluated"),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "build_prediction_corpus", False):
        from app.research.prediction_corpus import (
            run_and_write as corpus_run_and_write,
        )

        report = corpus_run_and_write()
        print(
            json.dumps(
                {
                    "ok": True,
                    "prediction_count": report.get("prediction_count"),
                    "tie_count": report.get("tie_count"),
                    "young_horse_count": report.get("young_horse_count"),
                    "gap": report.get("gap"),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "historical_bundle_ingest", False):
        from app.research.historical_bundle_ingest import (
            run_and_write as ingest_run_and_write,
        )

        report = ingest_run_and_write(rebuild_corpus=True)
        print(
            json.dumps(
                {
                    "ok": True,
                    "unique_races_with_bundle": report.get("unique_races_with_bundle"),
                    "unique_tie_races": report.get("unique_tie_races"),
                    "unique_unrecoverable_races": report.get("unique_unrecoverable_races"),
                    "corpus_before": report.get("_corpus_before"),
                    "corpus_after": report.get("_corpus_after"),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "young_horse_intelligence", False):
        from app.research.young_horse_intelligence import (
            run_and_write as yh_run_and_write,
        )

        report = yh_run_and_write()
        sample = report.get("sample") or {}
        print(
            json.dumps(
                {
                    "ok": True,
                    "young_races": sample.get("young_races_with_evidence"),
                    "debut": sample.get("debut_2yo_newcomer"),
                    "tie_races": sample.get("tie_races_ge2"),
                    "top_features": [
                        r.get("feature_id") for r in (report.get("ranking") or [])[:5]
                    ],
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "young_horse_archetypes", False):
        from app.research.young_horse_archetypes import (
            run_and_write as arch_run_and_write,
        )

        report = arch_run_and_write()
        sample = report.get("sample") or {}
        print(
            json.dumps(
                {
                    "ok": True,
                    "young_races": sample.get("young_races"),
                    "debut_races": sample.get("debut_races"),
                    "archetypes": len(report.get("archetypes") or []),
                    "top": [
                        {
                            "label": t.get("label"),
                            "win_rate": t.get("win_rate"),
                            "place_rate": t.get("place_rate"),
                            "roi": t.get("roi"),
                        }
                        for t in (report.get("ranking") or [])[:5]
                    ],
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "evidence_reliability", False):
        from app.research.evidence_reliability import (
            run_and_write as rel_run_and_write,
        )

        report = rel_run_and_write()
        print(
            json.dumps(
                {
                    "ok": True,
                    "sample": report.get("sample"),
                    "top_reliability": [
                        {
                            "feature": f.get("label"),
                            "score": f.get("reliability_score"),
                            "coverage": f.get("coverage"),
                            "leak_risk": f.get("leak_risk"),
                        }
                        for f in (report.get("features") or [])[:5]
                    ],
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "weakness_atlas", False):
        from app.research.weakness_atlas import (
            run_and_write as atlas_run_and_write,
        )

        report = atlas_run_and_write()
        print(
            json.dumps(
                {
                    "ok": True,
                    "sample": report.get("sample"),
                    "top_priority": [
                        {
                            "axis": t.get("axis"),
                            "segment": t.get("segment"),
                            "weakness_index": t.get("weakness_index"),
                            "priority_score": t.get("priority_score"),
                        }
                        for t in (report.get("priority_map") or [])[:5]
                    ],
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "metadata_completion", False):
        from app.research.metadata_completion import (
            run_and_write as meta_run_and_write,
        )

        report = meta_run_and_write()
        print(
            json.dumps(
                {
                    "ok": True,
                    "run_id": report.get("run_id"),
                    "mean_coverage_before": (report.get("summary") or {}).get(
                        "mean_coverage_before"
                    ),
                    "mean_coverage_after": (report.get("summary") or {}).get(
                        "mean_coverage_after"
                    ),
                    "improvement": report.get("improvement"),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "evidence_discovery", False):
        from app.research.evidence_discovery import (
            run_and_write as discovery_run_and_write,
        )

        report = discovery_run_and_write()
        disc = report.get("evidence_discovery") or {}
        print(
            json.dumps(
                {
                    "ok": True,
                    "sample": report.get("sample"),
                    "confident": (disc.get("counts") or {}).get("confident"),
                    "exploratory": (disc.get("counts") or {}).get("exploratory"),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "knowledge_base", False):
        from app.research.knowledge_base import (
            run_and_write as kb_run_and_write,
        )

        report = kb_run_and_write()
        print(
            json.dumps(
                {
                    "ok": True,
                    "week_id": report.get("week_id"),
                    "summary": report.get("summary"),
                    "weekly_diff": (report.get("weekly_diff") or {}).get("counts"),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "knowledge_validation", False):
        from app.research.knowledge_validation import (
            run_and_write as kv_run_and_write,
        )

        report = kv_run_and_write()
        print(
            json.dumps(
                {
                    "ok": True,
                    "run_id": report.get("run_id"),
                    "summary": report.get("summary"),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "production_candidate_review", False):
        from app.research.production_candidate_review import (
            run_and_write as pcr_run_and_write,
        )

        report = pcr_run_and_write()
        print(
            json.dumps(
                {
                    "ok": True,
                    "run_id": report.get("run_id"),
                    "summary": report.get("summary"),
                    "v21_ids": [
                        r.get("knowledge_id")
                        for r in (report.get("v21_candidates") or [])
                    ],
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "causal_evidence", False):
        from app.research.causal_evidence import (
            run_and_write as causal_run_and_write,
        )

        report = causal_run_and_write()
        print(
            json.dumps(
                {
                    "ok": True,
                    "sample": report.get("sample"),
                    "n_condition_effects": len(report.get("condition_effects") or []),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if (
        getattr(args, "continuous_research", False)
        or getattr(args, "continuous_research_report_only", False)
        or getattr(args, "research_ops", False)
        or getattr(args, "research_ops_report_only", False)
    ):
        from app.research.continuous_research_operation import (
            run_and_write as cro_run_and_write,
        )

        report_only = bool(
            getattr(args, "continuous_research_report_only", False)
            or getattr(args, "research_ops_report_only", False)
        )
        report = cro_run_and_write(report_only=report_only)
        print(
            json.dumps(
                {
                    "ok": True,
                    "week_id": report.get("week_id"),
                    "mission": report.get("mission"),
                    "review_queue_n": len(report.get("review_queue") or []),
                    "review_queue_delta": (
                        (report.get("governance") or {}).get("review_queue_delta")
                    ),
                    "notifications_n": len(report.get("notifications") or []),
                    "knowledge_diff": (report.get("knowledge_diff") or {}).get("counts"),
                    "corpus_kpi": {
                        k: (report.get("corpus_kpi") or {}).get(k)
                        for k in (
                            "prediction",
                            "evidence",
                            "knowledge",
                            "tie",
                            "young_horse",
                        )
                    },
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "corpus_growth", False) or getattr(
        args, "corpus_growth_report_only", False
    ):
        from app.research.corpus_growth import (
            run_and_write as growth_run_and_write,
        )

        report = growth_run_and_write(
            report_only=bool(getattr(args, "corpus_growth_report_only", False))
        )
        after = report.get("after") or {}
        print(
            json.dumps(
                {
                    "ok": True,
                    "week_id": report.get("week_id"),
                    "Prediction": after.get("prediction"),
                    "Evidence": after.get("evidence"),
                    "Knowledge": after.get("knowledge"),
                    "Coverage": after.get("coverage"),
                    "Confidence": after.get("confidence"),
                    "cycle_diff": (report.get("cycle_diff") or {}).get("scalar"),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "world_boundary", False):
        from app.research.world_boundary_research import (
            run_and_write as world_run_and_write,
        )

        report = world_run_and_write()
        print(
            json.dumps(
                {
                    "ok": True,
                    "sample": report.get("sample"),
                    "natural_membership_rate": (
                        (report.get("assignment") or {}).get("natural_membership_rate")
                    ),
                    "refinement_n": len(
                        ((report.get("refinement") or {}).get("proposals") or [])
                    ),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "world_activation", False):
        from app.research.world_activation_research import (
            run_and_write as activation_run_and_write,
        )

        report = activation_run_and_write()
        am = report.get("activation_map") or {}
        print(
            json.dumps(
                {
                    "ok": True,
                    "sample": report.get("sample"),
                    "activation_rates": {
                        w: (am.get(w) or {}).get("activation_rate")
                        for w in (report.get("existing_worlds") or [])
                    },
                    "inactive_n": len(report.get("inactive_analysis") or []),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "world_signal_instrumentation", False):
        from app.research.world_signal_instrumentation import (
            run_and_write as world_signal_run_and_write,
        )

        limit = int(getattr(args, "world_signal_limit", 0) or 0) or None
        report = world_signal_run_and_write(
            try_core=not bool(getattr(args, "world_signal_no_core", False)),
            limit=limit,
        )
        cov = report.get("coverage_scan") or {}
        print(
            json.dumps(
                {
                    "ok": True,
                    "snapshots_updated": report.get("snapshots_updated"),
                    "instrumentation_coverage": cov.get("instrumentation_coverage"),
                    "persistence_rate_mean": cov.get("persistence_rate_mean")
                    or report.get("persistence_rate_mean"),
                    "null_rate_mean": cov.get("null_rate_mean")
                    or report.get("null_rate_mean"),
                    "product_mutation": report.get("product_mutation"),
                    "judgment_changed": report.get("judgment_changed"),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "world_fitness", False):
        from app.research.world_fitness_research import (
            run_and_write as world_fitness_run_and_write,
        )

        report = world_fitness_run_and_write()
        print(
            json.dumps(
                {
                    "ok": True,
                    "midupper_n": (report.get("sample") or {}).get("midupper_assigned_n"),
                    "near_miss_n": (report.get("sample") or {}).get("near_miss_n"),
                    "mean_trigger_fitness": report.get("mean_trigger_fitness"),
                    "best_fit_distribution": report.get("best_fit_distribution"),
                    "product_mutation": report.get("product_mutation"),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "chaos_signal_trace", False):
        from app.research.chaos_signal_trace import (
            run_and_write as chaos_trace_run_and_write,
        )

        report = chaos_trace_run_and_write()
        live = report.get("live") or {}
        print(
            json.dumps(
                {
                    "ok": True,
                    "audit_only": True,
                    "live_ok": live.get("ok"),
                    "race_id": live.get("race_id"),
                    "last_present_point": live.get("last_present_point"),
                    "null_from_here": live.get("null_from_here"),
                    "diagnostic_chaos": live.get("diagnostic_chaos"),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "world_trigger_saturation", False):
        from app.research.world_trigger_saturation import (
            run_and_write as trigger_saturation_run_and_write,
        )

        report = trigger_saturation_run_and_write()
        print(
            json.dumps(
                {
                    "ok": True,
                    "n": (report.get("sample") or {}).get("n_labeled_canonical"),
                    "observed_share": report.get("observed_share"),
                    "design_gap_summary": report.get("design_gap_summary"),
                    "near_activation_counts": report.get("near_activation_counts"),
                    "product_mutation": report.get("product_mutation"),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "difficulty_signal_audit", False):
        from app.research.difficulty_signal_audit import (
            run_and_write as difficulty_audit_run_and_write,
        )

        report = difficulty_audit_run_and_write()
        dr = report.get("design_review") or {}
        print(
            json.dumps(
                {
                    "ok": True,
                    "n_present": (report.get("distribution") or {}).get("n_present"),
                    "mean": (report.get("distribution") or {}).get("mean"),
                    "std": (report.get("distribution") or {}).get("std"),
                    "unique_n": (report.get("variance") or {}).get("unique_n"),
                    "pass_ge_0_50": ((report.get("saturation") or {}).get(">=0.50") or {}).get(
                        "pass_rate"
                    ),
                    "dominated_by_default_0_5": (report.get("variance") or {}).get(
                        "dominated_by_default_0_5"
                    ),
                    "design_flags": {
                        "discriminability": dr.get("sufficient_discriminability"),
                        "information": dr.get("sufficient_information"),
                        "saturated_at_0_50": dr.get("saturated_at_0_50"),
                        "collapsed": dr.get("collapsed_to_constant"),
                    },
                    "product_mutation": report.get("product_mutation"),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "signal_lineage_audit", False):
        from app.research.signal_lineage_audit import (
            run_and_write as signal_lineage_run_and_write,
        )

        report = signal_lineage_run_and_write()
        live = report.get("live") or {}
        print(
            json.dumps(
                {
                    "ok": True,
                    "audit_only": True,
                    "live_ok": live.get("ok"),
                    "ce_meta_difficulty": live.get("ce_meta_race_leg_difficulty"),
                    "ce_world": live.get("ce_world"),
                    "default_on_production_core": (live.get("proof") or {}).get(
                        "default_0_5_applies_on_production_core"
                    ),
                    "research_not_sole_consumer": (live.get("proof") or {}).get(
                        "research_not_sole_consumer"
                    ),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "wic_shadow_ab", False):
        from app.research.wic_shadow_ab import run_and_write as wic_shadow_run_and_write

        report = wic_shadow_run_and_write()
        print(
            json.dumps(
                {
                    "ok": True,
                    "research_only": True,
                    "n_races": report.get("n_races"),
                    "governance_non_inferiority": report.get("governance_non_inferiority"),
                    "roi_proof_status": (report.get("roi_proof") or {}).get("status"),
                    "allow_v35": (report.get("v35_gate") or {}).get(
                        "allow_signal_service_design_v35"
                    ),
                    "world_changed_n": (report.get("world_transition") or {}).get("n_changed"),
                    "hit_delta": (report.get("delta") or {}).get("hit"),
                    "outputs": report.get("_outputs"),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if getattr(args, "reharvest_v103", False):
        settings = CollectorSettings.from_env()
        runner = ResearchCollectorRunner(settings)
        out = runner.reharvest(batch_size=3, limit=200)
        print(json.dumps(out, ensure_ascii=False))
        return 0

    settings = CollectorSettings.from_env()
    runner = ResearchCollectorRunner(settings)

    if args.backfill:
        out = runner.backfill(batch_size=20, max_rounds=40)
        print(json.dumps(out, ensure_ascii=False))
        return 0

    if args.loop:
        while True:
            out = runner.run_once()
            print(json.dumps(out, ensure_ascii=False))
            time.sleep(settings.poll_interval_sec)
        return 0

    out = runner.run_once()
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
