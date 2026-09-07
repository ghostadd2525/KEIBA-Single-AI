# -*- coding: utf-8 -*-
"""Research Evidence HTTP handlers."""
from __future__ import annotations

from typing import Any

from .monitoring import collect_evidence_monitoring
from .repository import ResearchEvidenceRepository
from .prediction_corpus import PredictionCorpusBuilder
from .resolver_governance import ResolverGovernance
from .shadow_resolver import ShadowTieResolver


def get_prediction_snapshot(prediction_id: int) -> dict[str, Any] | None:
    row = ResearchEvidenceRepository().get_snapshot(prediction_id)
    if not row:
        return None
    return {
        "snapshot_id": row.get("snapshot_id"),
        "prediction_id": row.get("prediction_id"),
        "race_id": row.get("race_id"),
        "race_date": row.get("race_date"),
        "capture_status": row.get("capture_status"),
        "field_coverage": row.get("field_coverage"),
        "anti_leak_violations": row.get("anti_leak_violations"),
        "json_path": row.get("json_path"),
        "payload": row.get("payload"),
    }


def get_evidence_monitoring() -> dict[str, Any]:
    return collect_evidence_monitoring()


def get_resolver_dashboard() -> dict[str, Any]:
    return ShadowTieResolver().analyze().get("dashboard") or {}


def get_resolver_governance_dashboard() -> dict[str, Any]:
    return ResolverGovernance().analyze().get("dashboard") or {}


def get_prediction_corpus_summary() -> dict[str, Any]:
    """Read latest corpus run summary from DB (no rebuild)."""
    from ..data.db import connect, migrate

    migrate()
    conn = connect()
    try:
        run = conn.execute(
            """
            SELECT * FROM research_corpus_runs
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()
        if not run:
            # build once if empty
            return PredictionCorpusBuilder().build()
        out = dict(run)
        import json

        out["summary"] = json.loads(out.pop("summary_json") or "{}")
        counts = conn.execute(
            """
            SELECT
              COUNT(*) AS prediction_count,
              SUM(is_tie) AS tie_count,
              SUM(is_young_horse) AS young_horse_count
            FROM research_prediction_corpus
            """
        ).fetchone()
        out["live_counts"] = dict(counts) if counts else {}
        return out
    finally:
        conn.close()
