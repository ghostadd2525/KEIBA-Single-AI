# -*- coding: utf-8 -*-
"""Ops monitoring for Research Evidence Collector."""
from __future__ import annotations

from typing import Any

from ..data.db import connect, migrate
from .config import CollectorSettings, PHASE1_FEATURES
from .repository import ResearchEvidenceRepository


def collect_evidence_monitoring() -> dict[str, Any]:
    migrate()
    settings = CollectorSettings.from_env()
    repo = ResearchEvidenceRepository()
    stats = repo.collector_stats()

    conn = connect()
    try:
        total_preds = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        snap_total = conn.execute(
            "SELECT COUNT(*) FROM research_prediction_snapshots"
        ).fetchone()[0]
        snap_complete = conn.execute(
            """
            SELECT COUNT(*) FROM research_prediction_snapshots
            WHERE capture_status = 'complete'
            """
        ).fetchone()[0]
        snap_partial = conn.execute(
            """
            SELECT COUNT(*) FROM research_prediction_snapshots
            WHERE capture_status = 'partial'
            """
        ).fetchone()[0]
        anti_leak = conn.execute(
            """
            SELECT COALESCE(SUM(anti_leak_violations), 0)
            FROM research_prediction_snapshots
            """
        ).fetchone()[0]

        feature_cov: dict[str, Any] = {}
        for fid in PHASE1_FEATURES:
            row = conn.execute(
                """
                SELECT AVG(
                  CASE
                    WHEN payload_json LIKE ?
                    THEN 1.0 ELSE 0.0
                  END
                ) AS cov
                FROM research_prediction_snapshots
                """,
                (f'%"field": "{fid}"%',),
            ).fetchone()
            # Better: parse JSON in Python for accuracy — lightweight estimate here
            feature_cov[fid] = {"coverage_est": row["cov"] if row else 0.0}

        events = stats.get("source_events_7d") or {}
        total_ev = int(events.get("total") or 0)
        ok_ev = int(events.get("ok") or 0)
        success_rate = round(ok_ev / total_ev, 4) if total_ev else None
        missing_rate = round(1.0 - (snap_complete / snap_total), 4) if snap_total else None

        return {
            "collector_status": "enabled" if settings.enabled else "disabled",
            "success_rate": success_rate,
            "missing_rate": missing_rate,
            "retry_count": stats.get("retry_total", 0),
            "source_latency_ms_avg": events.get("avg_latency_ms"),
            "source_availability": success_rate,
            "evidence_coverage": {
                "predictions_total": total_preds,
                "snapshots_total": snap_total,
                "snapshots_complete": snap_complete,
                "snapshots_partial": snap_partial,
                "snapshot_rate": round(snap_total / total_preds, 4) if total_preds else 0.0,
                "by_feature": feature_cov,
            },
            "jobs_by_status": stats.get("jobs_by_status", {}),
            "snapshots_by_status": stats.get("snapshots_by_status", {}),
            "anti_leak_violations_total": int(anti_leak or 0),
            "pi_base_url_configured": bool(settings.pi_base_url),
        }
    finally:
        conn.close()
