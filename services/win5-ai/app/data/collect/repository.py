# -*- coding: utf-8 -*-
"""Collector repositories — Contract 1.1."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from ..db import connect, migrate
from . import state as sm
from .contracts.targets import CollectTarget, validate_collect_target


class JobIdempotencyError(ValueError):
    """Raised when (week_id, target_id, artifact_type) already exists."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row) -> dict[str, Any]:
    return dict(row) if row is not None else {}


class CollectRunRepository:
    def __init__(self) -> None:
        migrate()

    def create(
        self,
        *,
        week_id: str,
        calendar_version: str,
        planner_run_id: str | None = None,
    ) -> dict[str, Any]:
        run_id = planner_run_id or f"planner-{week_id}-{uuid.uuid4().hex[:8]}"
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO collect_runs(
                  planner_run_id, week_id, calendar_version, status,
                  targets_count, jobs_enqueued, started_at
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (run_id, week_id, calendar_version, "running", 0, 0, _now()),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM collect_runs WHERE planner_run_id = ?", (run_id,)
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()

    def finish(
        self,
        planner_run_id: str,
        *,
        status: str = "success",
        targets_count: int | None = None,
        jobs_enqueued: int | None = None,
        manifest_path: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        conn = connect()
        try:
            sets = ["status = ?", "finished_at = ?"]
            params: list[Any] = [status, _now()]
            if targets_count is not None:
                sets.append("targets_count = ?")
                params.append(targets_count)
            if jobs_enqueued is not None:
                sets.append("jobs_enqueued = ?")
                params.append(jobs_enqueued)
            if manifest_path is not None:
                sets.append("manifest_path = ?")
                params.append(manifest_path)
            if detail is not None:
                sets.append("detail_json = ?")
                params.append(json.dumps(detail, ensure_ascii=False))
            params.append(planner_run_id)
            conn.execute(
                f"UPDATE collect_runs SET {', '.join(sets)} WHERE planner_run_id = ?",
                params,
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM collect_runs WHERE planner_run_id = ?", (planner_run_id,)
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()

    def get(self, planner_run_id: str) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT * FROM collect_runs WHERE planner_run_id = ?", (planner_run_id,)
            ).fetchone()
            return _row_to_dict(row) if row else None
        finally:
            conn.close()


class CollectTargetRepository:
    def __init__(self) -> None:
        migrate()

    def insert_many(
        self,
        *,
        planner_run_id: str,
        targets: list[CollectTarget | dict[str, Any]],
    ) -> list[dict[str, Any]]:
        conn = connect()
        out: list[dict[str, Any]] = []
        try:
            for raw in targets:
                target = validate_collect_target(raw)
                conn.execute(
                    """
                    INSERT INTO collect_targets(
                      planner_run_id, week_id, calendar_version,
                      race_date, venue, race_no, race_id, public_race_id, created_at
                    ) VALUES (?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        planner_run_id,
                        target.week_id,
                        target.calendar_version,
                        target.race_date,
                        target.venue,
                        target.race_no,
                        target.race_id,
                        target.public_race_id,
                        _now(),
                    ),
                )
            conn.commit()
            rows = conn.execute(
                """
                SELECT * FROM collect_targets
                WHERE planner_run_id = ?
                ORDER BY race_date, venue, race_no
                """,
                (planner_run_id,),
            ).fetchall()
            out = [_row_to_dict(r) for r in rows]
            return out
        finally:
            conn.close()

    def get(self, target_id: int) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT * FROM collect_targets WHERE id = ?",
                (target_id,),
            ).fetchone()
            return _row_to_dict(row) if row else None
        finally:
            conn.close()

    def list_by_week(self, week_id: str) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM collect_targets
                WHERE week_id = ?
                ORDER BY race_date, venue, race_no
                """,
                (week_id,),
            ).fetchall()
            return [_row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def count_by_week(self, week_id: str) -> int:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM collect_targets WHERE week_id = ?",
                (week_id,),
            ).fetchone()
            return int(row["c"]) if row else 0
        finally:
            conn.close()


class CollectJobRepository:
    def __init__(self) -> None:
        migrate()

    def create(
        self,
        *,
        job_id: str,
        week_id: str,
        race_date: str,
        artifact_type: str,
        kind: str,
        priority: str,
        planner_run_id: str | None = None,
        target_id: int | None = None,
        race_id: str | None = None,
        status: str = sm.PENDING,
        budget_cost: int = 1,
        scheduled_for: str | None = None,
        require_target_id: bool = True,
    ) -> dict[str, Any]:
        if status not in sm.ALL_STATUSES:
            raise ValueError(f"invalid job status: {status}")
        if require_target_id and target_id is None:
            raise ValueError("target_id is required for idempotent job enqueue (Contract 1.1)")
        now = _now()
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO collect_jobs(
                  job_id, planner_run_id, target_id, week_id, race_date, race_id,
                  artifact_type, kind, priority, status, budget_cost,
                  scheduled_for, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    job_id,
                    planner_run_id,
                    target_id,
                    week_id,
                    race_date,
                    race_id,
                    artifact_type,
                    kind,
                    priority,
                    status,
                    budget_cost,
                    scheduled_for,
                    now,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM collect_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            return _row_to_dict(row)
        except sqlite3.IntegrityError as exc:
            if "uq_collect_jobs_week_target_artifact" in str(exc).lower() or "unique" in str(exc).lower():
                raise JobIdempotencyError(
                    f"duplicate job enqueue: week_id={week_id!r} target_id={target_id!r} "
                    f"artifact_type={artifact_type!r}"
                ) from exc
            raise
        finally:
            conn.close()

    def get(self, job_id: str) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT * FROM collect_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            return _row_to_dict(row) if row else None
        finally:
            conn.close()

    def get_by_target_artifact(
        self,
        *,
        week_id: str,
        target_id: int,
        artifact_type: str,
    ) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute(
                """
                SELECT * FROM collect_jobs
                WHERE week_id = ? AND target_id = ? AND artifact_type = ?
                """,
                (week_id, target_id, artifact_type),
            ).fetchone()
            return _row_to_dict(row) if row else None
        finally:
            conn.close()

    def transition(
        self,
        job_id: str,
        new_status: str,
        *,
        last_error: str | None = None,
        attempt: int | None = None,
        retry_after: str | None = None,
        validation_errors: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        job = self.get(job_id)
        if not job:
            raise KeyError(f"collect_job not found: {job_id}")
        current = str(job.get("status") or "")
        kind = str(job.get("kind") or "")
        sm.assert_transition(current, new_status, kind=kind)

        sets = ["status = ?", "updated_at = ?"]
        params: list[Any] = [new_status, _now()]

        if last_error is not None:
            sets.append("last_error = ?")
            params.append(last_error)
        if attempt is not None:
            sets.append("attempt = ?")
            params.append(int(attempt))
        if retry_after is not None:
            sets.append("retry_after = ?")
            params.append(retry_after)
        if validation_errors is not None:
            sets.append("validation_errors_json = ?")
            params.append(json.dumps(validation_errors, ensure_ascii=False))

        params.append(job_id)
        conn = connect()
        try:
            conn.execute(
                f"UPDATE collect_jobs SET {', '.join(sets)} WHERE job_id = ?",
                params,
            )
            conn.commit()
            return self.get(job_id) or {}
        finally:
            conn.close()

    def requeue_for_retry(self, job_id: str) -> dict[str, Any]:
        job = self.get(job_id)
        if not job:
            raise KeyError(f"collect_job not found: {job_id}")
        current = str(job.get("status") or "")
        kind = str(job.get("kind") or "")
        sm.assert_transition(current, sm.PENDING, kind=kind)

        conn = connect()
        try:
            conn.execute(
                """
                UPDATE collect_jobs
                SET status = ?, retry_after = NULL, updated_at = ?
                WHERE job_id = ?
                """,
                (sm.PENDING, _now(), job_id),
            )
            conn.commit()
            return self.get(job_id) or {}
        finally:
            conn.close()

    def link_artifact(self, job_id: str, artifact_uid: str) -> dict[str, Any]:
        """
        Bind collect_jobs.artifact_id (FK) to collect_artifacts row.
        Contract-only: verifies job_id consistency on both sides.
        """
        job = self.get(job_id)
        if not job:
            raise KeyError(f"collect_job not found: {job_id}")

        conn = connect()
        try:
            art = conn.execute(
                "SELECT * FROM collect_artifacts WHERE artifact_uid = ?",
                (artifact_uid,),
            ).fetchone()
            if not art:
                raise KeyError(f"collect_artifact not found: {artifact_uid}")
            art_d = _row_to_dict(art)
            if str(art_d.get("job_id") or "") != job_id:
                raise ValueError(
                    f"artifact {artifact_uid!r} job_id={art_d.get('job_id')!r} "
                    f"does not match job {job_id!r}"
                )
            conn.execute(
                """
                UPDATE collect_jobs
                SET artifact_id = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (art_d["id"], _now(), job_id),
            )
            conn.commit()
            return self.get(job_id) or {}
        finally:
            conn.close()

    def list_by_week(self, week_id: str, *, status: str | None = None) -> list[dict[str, Any]]:
        conn = connect()
        try:
            sql = "SELECT * FROM collect_jobs WHERE week_id = ?"
            params: list[Any] = [week_id]
            if status:
                sql += " AND status = ?"
                params.append(status)
            sql += " ORDER BY priority, kind, scheduled_for, attempt, job_id"
            rows = conn.execute(sql, params).fetchall()
            return [_row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def dequeue_pending(
        self,
        *,
        week_id: str,
        as_of_date: str,
        budget: Any,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM collect_jobs
                WHERE week_id = ?
                  AND status = ?
                  AND (scheduled_for IS NULL OR scheduled_for <= ?)
                ORDER BY
                  priority ASC,
                  CASE kind
                    WHEN 'STATIC_CORE' THEN 1
                    WHEN 'STATIC_PROFILE' THEN 2
                    WHEN 'STATIC_HISTORY' THEN 3
                    WHEN 'DYNAMIC' THEN 4
                    ELSE 9
                  END,
                  scheduled_for ASC,
                  attempt ASC,
                  job_id ASC
                """,
                (week_id, sm.PENDING, as_of_date),
            ).fetchall()
        finally:
            conn.close()

        selected: list[dict[str, Any]] = []
        for row in rows:
            job = _row_to_dict(row)
            cost = int(job.get("budget_cost") or 1)
            if not budget.can_afford(cost):
                break
            budget.consume(cost)
            selected.append(job)
            if limit is not None and len(selected) >= limit:
                break
        return selected

    def list_retry_due(
        self,
        *,
        week_id: str,
        as_of_date: str,
    ) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM collect_jobs
                WHERE week_id = ?
                  AND status IN (?, ?)
                  AND retry_after IS NOT NULL
                  AND retry_after <= ?
                ORDER BY retry_after ASC, job_id ASC
                """,
                (week_id, sm.PARTIAL, sm.FAILED, as_of_date),
            ).fetchall()
            return [_row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def count_by_status(self, week_id: str) -> dict[str, int]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS c
                FROM collect_jobs
                WHERE week_id = ?
                GROUP BY status
                """,
                (week_id,),
            ).fetchall()
            by_status = {str(r["status"]): int(r["c"]) for r in rows}
        finally:
            conn.close()

        retry = 0
        conn = connect()
        try:
            row = conn.execute(
                """
                SELECT COUNT(*) AS c FROM collect_jobs
                WHERE week_id = ?
                  AND status IN (?, ?)
                  AND retry_after IS NOT NULL
                """,
                (week_id, sm.PARTIAL, sm.FAILED),
            ).fetchone()
            retry = int(row["c"]) if row else 0
        finally:
            conn.close()

        return {
            "ready": by_status.get(sm.READY, 0),
            "partial": by_status.get(sm.PARTIAL, 0),
            "failed": by_status.get(sm.FAILED, 0),
            "retry": retry,
        }

    def count_race_meta_ready_races(self, week_id: str) -> int:
        conn = connect()
        try:
            row = conn.execute(
                """
                SELECT COUNT(*) AS c FROM collect_jobs
                WHERE week_id = ?
                  AND artifact_type = 'race_meta'
                  AND status = ?
                """,
                (week_id, sm.READY),
            ).fetchone()
            return int(row["c"]) if row else 0
        finally:
            conn.close()

    def list_dynamic_jobs(
        self,
        week_id: str,
        *,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        conn = connect()
        try:
            sql = """
                SELECT * FROM collect_jobs
                WHERE week_id = ? AND kind = ?
            """
            params: list[Any] = [week_id, sm.KIND_DYNAMIC]
            if status:
                sql += " AND status = ?"
                params.append(status)
            sql += " ORDER BY artifact_type, scheduled_for, job_id"
            rows = conn.execute(sql, params).fetchall()
            return [_row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def count_dynamic_status(self, week_id: str) -> dict[str, int]:
        """Count DYNAMIC jobs by coarse buckets for Manifest."""
        jobs = self.list_dynamic_jobs(week_id)
        ready = sum(1 for j in jobs if j.get("status") == sm.READY)
        stale = sum(1 for j in jobs if j.get("status") == sm.STALE_DYNAMIC)
        refreshing = sum(
            1
            for j in jobs
            if j.get("status") in (sm.PENDING, sm.RUNNING, sm.STALE_DYNAMIC, sm.PARTIAL, sm.FAILED)
        )
        return {
            "total": len(jobs),
            "ready": ready,
            "stale": stale,
            "refreshing": refreshing,
        }


class CollectArtifactRepository:
    def __init__(self) -> None:
        migrate()

    def create(
        self,
        *,
        artifact_uid: str,
        job_id: str,
        week_id: str,
        race_date: str,
        artifact_type: str,
        kind: str,
        race_id: str | None = None,
        status: str = sm.PENDING,
        raw_path: str | None = None,
        content_hash: str | None = None,
    ) -> dict[str, Any]:
        if status not in sm.ALL_STATUSES:
            raise ValueError(f"invalid artifact status: {status}")
        now = _now()
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO collect_artifacts(
                  artifact_uid, job_id, week_id, race_date, race_id,
                  artifact_type, kind, status, raw_path, content_hash,
                  created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    artifact_uid,
                    job_id,
                    week_id,
                    race_date,
                    race_id,
                    artifact_type,
                    kind,
                    status,
                    raw_path,
                    content_hash,
                    now,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM collect_artifacts WHERE artifact_uid = ?", (artifact_uid,)
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()

    def get(self, artifact_uid: str) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT * FROM collect_artifacts WHERE artifact_uid = ?", (artifact_uid,)
            ).fetchone()
            return _row_to_dict(row) if row else None
        finally:
            conn.close()

    def get_for_job(self, job_id: str) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT * FROM collect_artifacts WHERE job_id = ? ORDER BY id DESC LIMIT 1",
                (job_id,),
            ).fetchone()
            return _row_to_dict(row) if row else None
        finally:
            conn.close()

    def transition(
        self,
        artifact_uid: str,
        new_status: str,
        *,
        validation_errors: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        art = self.get(artifact_uid)
        if not art:
            raise KeyError(f"collect_artifact not found: {artifact_uid}")
        current = str(art.get("status") or "")
        kind = str(art.get("kind") or "")
        sm.assert_transition(current, new_status, kind=kind)

        sets = ["status = ?", "updated_at = ?"]
        params: list[Any] = [new_status, _now()]
        if validation_errors is not None:
            sets.append("validation_errors_json = ?")
            params.append(json.dumps(validation_errors, ensure_ascii=False))
        params.append(artifact_uid)

        conn = connect()
        try:
            conn.execute(
                f"UPDATE collect_artifacts SET {', '.join(sets)} WHERE artifact_uid = ?",
                params,
            )
            conn.commit()
            return self.get(artifact_uid) or {}
        finally:
            conn.close()
