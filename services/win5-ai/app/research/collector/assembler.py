# -*- coding: utf-8 -*-
"""Assemble Prediction Snapshot payload."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ..config import JOB_SCHEMA_VERSION, PHASE1_FEATURES, SCHEMA_VERSION, P0_FEATURES


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _race_date_from_id(race_id: str) -> str | None:
    parts = str(race_id).split("-")
    if len(parts) >= 3 and len(parts[0]) == 4:
        return f"{parts[0]}-{parts[1]}-{parts[2]}"
    return None


def _field_coverage(runners: list[dict[str, Any]]) -> float:
    if not runners:
        return 0.0
    total = len(runners) * len(PHASE1_FEATURES)
    filled = 0
    for row in runners:
        for fid in PHASE1_FEATURES:
            if row.get(fid) is not None:
                filled += 1
    return round(filled / total, 4) if total else 0.0


def _capture_status(runners: list[dict[str, Any]], fetch_error: str | None) -> str:
    if fetch_error:
        return "failed"
    if not runners:
        return "partial"
    p0_ok = True
    for row in runners:
        for fid in P0_FEATURES:
            if row.get(fid) is None:
                p0_ok = False
                break
        if not p0_ok:
            break
    if p0_ok:
        return "complete"
    any_value = any(row.get(fid) is not None for row in runners for fid in PHASE1_FEATURES)
    return "partial" if any_value else "failed"


def assemble_snapshot(
    *,
    job: dict[str, Any],
    runners: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    anti_leak_violations: int,
    fetch_error: str | None = None,
    latency_ms: float | None = None,
) -> dict[str, Any]:
    race_id = str(job["race_id"])
    prediction_id = int(job["prediction_id"])
    created_at = str(job["prediction_created_at"])
    captured_at = _now()
    status = _capture_status(runners, fetch_error)

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": str(uuid.uuid4()),
        "prediction_id": prediction_id,
        "race_id": race_id,
        "race_date": _race_date_from_id(race_id),
        "prediction_created_at": created_at,
        "captured_at": captured_at,
        "capture_status": status,
        "job": {
            "job_id": job.get("job_id"),
            "schema_version": JOB_SCHEMA_VERSION,
            "attempt": job.get("attempt"),
        },
        "phase": "v10.3",
        "features": list(PHASE1_FEATURES),
        "runners": runners,
        "sources": sources,
        "quality": {
            "field_coverage": _field_coverage(runners),
            "anti_leak_violations": anti_leak_violations,
            "fetch_error": fetch_error,
            "source_latency_ms": latency_ms,
        },
        "score_mutated": False,
    }
    return payload
