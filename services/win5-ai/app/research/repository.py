# -*- coding: utf-8 -*-
"""Research Evidence DB repository."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from ..data.db import connect, migrate


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _deadline(prediction_created_at: str, minutes: int) -> str:
    pred = datetime.fromisoformat(prediction_created_at.replace("Z", "+00:00"))
    if pred.tzinfo is None:
        pred = pred.replace(tzinfo=timezone.utc)
    return (pred + timedelta(minutes=minutes)).isoformat()


class ResearchEvidenceRepository:
    def __init__(self) -> None:
        migrate()

    def list_predictions_without_snapshot(self, *, limit: int = 50) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT p.id AS prediction_id, p.race_id, p.created_at AS prediction_created_at
                FROM predictions p
                LEFT JOIN research_prediction_snapshots s ON s.prediction_id = p.id
                LEFT JOIN research_collect_jobs j ON j.prediction_id = p.id
                WHERE s.prediction_id IS NULL
                  AND (j.prediction_id IS NULL OR j.status IN ('failed', 'cancelled'))
                ORDER BY p.id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def requeue_failed_jobs(self) -> int:
        """Reset failed/cancelled jobs (without snapshots) back to pending."""
        conn = connect()
        try:
            conn.execute(
                """
                UPDATE research_collect_jobs
                SET status = 'pending',
                    started_at = NULL,
                    finished_at = NULL,
                    last_error = NULL,
                    attempt = 0
                WHERE status IN ('failed', 'cancelled')
                  AND prediction_id NOT IN (
                    SELECT prediction_id FROM research_prediction_snapshots
                  )
                """
            )
            n = conn.total_changes
            conn.commit()
            return int(n or 0)
        finally:
            conn.close()

    def enqueue_job(
        self,
        *,
        prediction_id: int,
        race_id: str,
        prediction_created_at: str,
        max_attempts: int = 5,
        deadline_minutes: int = 15,
    ) -> dict[str, Any]:
        job_id = str(uuid.uuid4())
        now = _now()
        conn = connect()
        try:
            existing = conn.execute(
                "SELECT * FROM research_collect_jobs WHERE prediction_id = ?",
                (prediction_id,),
            ).fetchone()
            if existing:
                st = str(existing["status"] or "")
                if st in ("failed", "cancelled"):
                    conn.execute(
                        """
                        UPDATE research_collect_jobs
                        SET status = 'pending',
                            attempt = 0,
                            started_at = NULL,
                            finished_at = NULL,
                            last_error = NULL,
                            enqueued_at = ?,
                            deadline_at = ?,
                            max_attempts = ?
                        WHERE prediction_id = ?
                        """,
                        (
                            now,
                            _deadline(prediction_created_at, deadline_minutes),
                            max_attempts,
                            prediction_id,
                        ),
                    )
                    conn.commit()
                row = conn.execute(
                    "SELECT * FROM research_collect_jobs WHERE prediction_id = ?",
                    (prediction_id,),
                ).fetchone()
                return dict(row) if row else {}

            conn.execute(
                """
                INSERT INTO research_collect_jobs(
                  job_id, prediction_id, race_id, prediction_created_at,
                  status, attempt, max_attempts, enqueued_at, deadline_at
                ) VALUES (?,?,?,?, 'pending', 0, ?, ?, ?)
                """,
                (
                    job_id,
                    prediction_id,
                    race_id,
                    prediction_created_at,
                    max_attempts,
                    now,
                    _deadline(prediction_created_at, deadline_minutes),
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM research_collect_jobs WHERE prediction_id = ?",
                (prediction_id,),
            ).fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()

    def index_snapshot_features(
        self,
        *,
        snapshot_id: str,
        prediction_id: int,
        race_id: str,
        payload: dict[str, Any],
    ) -> None:
        """Denormalize runners → research_snapshot_features + quality."""
        now = _now()
        runners = list(payload.get("runners") or [])
        sources = list(payload.get("sources") or [])
        asof = 1 if any(s.get("asof_clamped") for s in sources) else 0
        from .config import PHASE1_FEATURES

        feature_ids = tuple(PHASE1_FEATURES)
        source_by_feature = {
            "popularity": "jra_odds_api",
            "win_odds": "jra_odds_api",
            "expected_popularity": "derived_expected_pop",
            "trainer": "netkeiba_shutuba",
            "sire": "netkeiba_pedigree_ajax",
            "damsire": "netkeiba_pedigree_ajax",
            "breeder": "netkeiba_horse_db",
            "owner": "netkeiba_horse_db",
            "sale_price": "netkeiba_horse_db",
            "oikiri_time": "netkeiba_oikiri",
            "oikiri_rating": "netkeiba_oikiri",
        }
        source_feature_map = {
            "popularity": "market_bundle",
            "win_odds": "market_bundle",
            "expected_popularity": "market_bundle",
            "trainer": "trainer",
            "sire": "pedigree",
            "damsire": "pedigree",
            "breeder": "horse_profile",
            "owner": "horse_profile",
            "sale_price": "horse_profile",
            "oikiri_time": "oikiri",
            "oikiri_rating": "oikiri",
        }
        fill: dict[str, int] = {f: 0 for f in feature_ids}
        conn = connect()
        try:
            conn.execute(
                "DELETE FROM research_snapshot_features WHERE snapshot_id = ?",
                (snapshot_id,),
            )
            for row in runners:
                hn = int(row.get("horse_number") or 0)
                missing_map = {
                    m.get("field"): m.get("reason")
                    for m in (row.get("missing") or [])
                    if m.get("field")
                }
                for fid in feature_ids:
                    val = row.get(fid)
                    if val is not None:
                        fill[fid] += 1
                    obs = None
                    want = source_feature_map.get(fid)
                    for s in sources:
                        if want and s.get("feature_id") == want:
                            obs = s.get("observed_at")
                            break
                    conn.execute(
                        """
                        INSERT INTO research_snapshot_features(
                          snapshot_id, prediction_id, race_id, horse_number,
                          feature_id, value_json, source_id, observed_at,
                          missing_reason, asof_clamped, created_at
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            snapshot_id,
                            prediction_id,
                            race_id,
                            hn,
                            fid,
                            json.dumps(val, ensure_ascii=False) if val is not None else None,
                            source_by_feature.get(fid),
                            obs,
                            missing_map.get(fid),
                            asof,
                            now,
                        ),
                    )
            runner_count = len(runners)
            coverage = float((payload.get("quality") or {}).get("field_coverage") or 0)
            conn.execute(
                """
                INSERT OR REPLACE INTO research_snapshot_quality(
                  snapshot_id, prediction_id, race_id, capture_status,
                  field_coverage, completeness, consistency,
                  anti_leak_violations, asof_clamped, runner_count,
                  feature_fill_json, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    snapshot_id,
                    prediction_id,
                    race_id,
                    str(payload.get("capture_status") or ""),
                    coverage,
                    coverage,
                    None,
                    int((payload.get("quality") or {}).get("anti_leak_violations") or 0),
                    asof,
                    runner_count,
                    json.dumps(fill, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def claim_pending_jobs(self, *, limit: int = 10) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM research_collect_jobs
                WHERE status = 'pending'
                  AND attempt < max_attempts
                ORDER BY enqueued_at ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            claimed: list[dict[str, Any]] = []
            now = _now()
            for row in rows:
                job = dict(row)
                conn.execute(
                    """
                    UPDATE research_collect_jobs
                    SET status = 'running', started_at = ?, attempt = attempt + 1
                    WHERE job_id = ? AND status = 'pending'
                    """,
                    (now, job["job_id"]),
                )
                if conn.total_changes:
                    job["status"] = "running"
                    job["attempt"] = int(job.get("attempt") or 0) + 1
                    claimed.append(job)
            conn.commit()
            return claimed
        finally:
            conn.close()

    def finish_job(
        self,
        *,
        job_id: str,
        status: str,
        last_error: str | None = None,
        retry: bool = False,
    ) -> None:
        conn = connect()
        try:
            if retry:
                conn.execute(
                    """
                    UPDATE research_collect_jobs
                    SET status = 'pending',
                        finished_at = NULL,
                        last_error = ?,
                        retry_count = retry_count + 1
                    WHERE job_id = ?
                    """,
                    (last_error, job_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE research_collect_jobs
                    SET status = ?, finished_at = ?, last_error = ?
                    WHERE job_id = ?
                    """,
                    (status, _now(), last_error, job_id),
                )
            conn.commit()
        finally:
            conn.close()

    def delete_snapshot_for_prediction(self, prediction_id: int) -> None:
        """Remove snapshot + features + quality for a prediction (reharvest)."""
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT snapshot_id FROM research_prediction_snapshots WHERE prediction_id = ?",
                (prediction_id,),
            ).fetchall()
            for r in rows:
                sid = r["snapshot_id"]
                conn.execute(
                    "DELETE FROM research_snapshot_features WHERE snapshot_id = ?",
                    (sid,),
                )
                conn.execute(
                    "DELETE FROM research_snapshot_quality WHERE snapshot_id = ?",
                    (sid,),
                )
            conn.execute(
                "DELETE FROM research_prediction_snapshots WHERE prediction_id = ?",
                (prediction_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def list_predictions_for_reharvest(self, *, limit: int = 200) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT p.id AS prediction_id, p.race_id, p.created_at AS prediction_created_at,
                       s.snapshot_id, s.capture_status
                FROM predictions p
                JOIN research_prediction_snapshots s ON s.prediction_id = p.id
                WHERE p.race_id NOT LIKE '2099%'
                  AND p.race_id NOT LIKE '%福島%'
                  AND p.race_id NOT LIKE '%sapporo%'
                ORDER BY p.id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def save_snapshot(
        self,
        *,
        snapshot_id: str,
        prediction_id: int,
        race_id: str,
        race_date: str | None,
        capture_status: str,
        field_coverage: float,
        anti_leak_violations: int,
        payload: dict[str, Any],
        json_path: str | None,
    ) -> None:
        conn = connect()
        try:
            # Replace by prediction_id (UNIQUE) — clear old snapshot_id rows first
            old = conn.execute(
                "SELECT snapshot_id FROM research_prediction_snapshots WHERE prediction_id = ?",
                (prediction_id,),
            ).fetchall()
            for r in old:
                old_sid = r["snapshot_id"]
                if old_sid != snapshot_id:
                    conn.execute(
                        "DELETE FROM research_snapshot_features WHERE snapshot_id = ?",
                        (old_sid,),
                    )
                    conn.execute(
                        "DELETE FROM research_snapshot_quality WHERE snapshot_id = ?",
                        (old_sid,),
                    )
            conn.execute(
                "DELETE FROM research_prediction_snapshots WHERE prediction_id = ?",
                (prediction_id,),
            )
            conn.execute(
                """
                INSERT INTO research_prediction_snapshots(
                  snapshot_id, schema_version, prediction_id, race_id, race_date,
                  captured_at, capture_status, field_coverage, anti_leak_violations,
                  payload_json, json_path, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    snapshot_id,
                    payload.get("schema_version"),
                    prediction_id,
                    race_id,
                    race_date,
                    payload.get("captured_at") or _now(),
                    capture_status,
                    field_coverage,
                    anti_leak_violations,
                    json.dumps(payload, ensure_ascii=False),
                    json_path,
                    _now(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_snapshot(self, prediction_id: int) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT * FROM research_prediction_snapshots WHERE prediction_id = ?",
                (prediction_id,),
            ).fetchone()
            if not row:
                return None
            out = dict(row)
            out["payload"] = json.loads(out.pop("payload_json") or "{}")
            return out
        finally:
            conn.close()

    def log_source_event(
        self,
        *,
        job_id: str,
        prediction_id: int,
        feature_id: str,
        source_id: str,
        success: bool,
        observed_at: str | None,
        fetched_at: str,
        latency_ms: float | None,
        missing_reason: str | None = None,
        error_message: str | None = None,
    ) -> None:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO research_source_events(
                  job_id, prediction_id, feature_id, source_id, success,
                  observed_at, fetched_at, latency_ms, missing_reason,
                  error_message, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    job_id,
                    prediction_id,
                    feature_id,
                    source_id,
                    1 if success else 0,
                    observed_at,
                    fetched_at,
                    latency_ms,
                    missing_reason,
                    error_message,
                    _now(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def upsert_daily_metric(
        self,
        *,
        metric_date: str,
        feature_id: str,
        metrics: dict[str, Any],
    ) -> None:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO research_evidence_daily(
                  metric_date, feature_id, coverage, missing_rate,
                  freshness_p50_sec, completeness, consistency,
                  success_rate, retry_total, source_latency_p50_ms,
                  source_availability, sample_count, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(metric_date, feature_id) DO UPDATE SET
                  coverage = excluded.coverage,
                  missing_rate = excluded.missing_rate,
                  freshness_p50_sec = excluded.freshness_p50_sec,
                  completeness = excluded.completeness,
                  consistency = excluded.consistency,
                  success_rate = excluded.success_rate,
                  retry_total = excluded.retry_total,
                  source_latency_p50_ms = excluded.source_latency_p50_ms,
                  source_availability = excluded.source_availability,
                  sample_count = excluded.sample_count,
                  updated_at = excluded.updated_at
                """,
                (
                    metric_date,
                    feature_id,
                    metrics.get("coverage"),
                    metrics.get("missing_rate"),
                    metrics.get("freshness_p50_sec"),
                    metrics.get("completeness"),
                    metrics.get("consistency"),
                    metrics.get("success_rate"),
                    int(metrics.get("retry_total") or 0),
                    metrics.get("source_latency_p50_ms"),
                    metrics.get("source_availability"),
                    int(metrics.get("sample_count") or 0),
                    _now(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def collector_stats(self) -> dict[str, Any]:
        conn = connect()
        try:
            jobs = conn.execute(
                """
                SELECT status, COUNT(*) AS n FROM research_collect_jobs GROUP BY status
                """
            ).fetchall()
            snapshots = conn.execute(
                "SELECT capture_status, COUNT(*) AS n FROM research_prediction_snapshots GROUP BY capture_status"
            ).fetchall()
            events = conn.execute(
                """
                SELECT
                  COUNT(*) AS total,
                  SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS ok,
                  AVG(latency_ms) AS avg_latency_ms
                FROM research_source_events
                WHERE created_at >= datetime('now', '-7 days')
                """
            ).fetchone()
            retries = conn.execute(
                "SELECT COALESCE(SUM(retry_count), 0) FROM research_collect_jobs"
            ).fetchone()
            return {
                "jobs_by_status": {r["status"]: r["n"] for r in jobs},
                "snapshots_by_status": {r["capture_status"]: r["n"] for r in snapshots},
                "source_events_7d": dict(events) if events else {},
                "retry_total": int((retries or [0])[0] or 0),
            }
        finally:
            conn.close()
