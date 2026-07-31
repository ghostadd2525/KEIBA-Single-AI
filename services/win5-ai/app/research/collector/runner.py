# -*- coding: utf-8 -*-
"""Research Evidence collector runner (async sidecar)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..config import CollectorSettings
from ..repository import ResearchEvidenceRepository
from ..store import write_snapshot_file
from .assembler import assemble_snapshot
from .phase1 import fetch_and_collect
from .pi_client import ResearchPiClient


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ResearchCollectorRunner:
    def __init__(self, settings: CollectorSettings | None = None) -> None:
        self.settings = settings or CollectorSettings.from_env()
        self.repo = ResearchEvidenceRepository()
        self.client: ResearchPiClient | None = None
        if self.settings.pi_base_url:
            self.client = ResearchPiClient(
                base_url=self.settings.pi_base_url,
                timeout_sec=self.settings.pi_timeout_sec,
            )

    def poll_and_enqueue(self, *, limit: int = 50) -> int:
        if not self.settings.enabled:
            return 0
        self.repo.requeue_failed_jobs()
        pending = self.repo.list_predictions_without_snapshot(limit=limit)
        n = 0
        for row in pending:
            job = self.repo.enqueue_job(
                prediction_id=int(row["prediction_id"]),
                race_id=str(row["race_id"]),
                prediction_created_at=str(row["prediction_created_at"]),
                max_attempts=self.settings.max_attempts,
                deadline_minutes=self.settings.deadline_minutes,
            )
            if job:
                n += 1
        return n

    def process_jobs(self, *, limit: int = 10) -> list[dict[str, Any]]:
        if not self.settings.enabled:
            return []
        jobs = self.repo.claim_pending_jobs(limit=limit)
        results: list[dict[str, Any]] = []
        for job in jobs:
            results.append(self._process_one(job))
        return results

    def reharvest(
        self,
        *,
        batch_size: int = 5,
        limit: int = 200,
    ) -> dict[str, Any]:
        """
        Delete existing snapshots and re-collect with V10.3 horse/workout features.
        Does not mutate Prediction Bundle / PE / CE / AI.
        """
        targets = self.repo.list_predictions_for_reharvest(limit=limit)
        reset = 0
        for row in targets:
            pid = int(row["prediction_id"])
            self.repo.delete_snapshot_for_prediction(pid)
            # Reset job to pending so process_jobs can claim it
            self.repo.enqueue_job(
                prediction_id=pid,
                race_id=str(row["race_id"]),
                prediction_created_at=str(row["prediction_created_at"]),
                max_attempts=self.settings.max_attempts,
                deadline_minutes=self.settings.deadline_minutes,
            )
            # Force pending even if previously done
            conn_force = True
            reset += 1
            if conn_force:
                from app.data.db import connect

                c = connect()
                try:
                    c.execute(
                        """
                        UPDATE research_collect_jobs
                        SET status = 'pending',
                            started_at = NULL,
                            finished_at = NULL,
                            last_error = NULL,
                            attempt = 0
                        WHERE prediction_id = ?
                        """,
                        (pid,),
                    )
                    c.commit()
                finally:
                    c.close()

        rounds: list[dict[str, Any]] = []
        # Process until drained
        for _ in range(max(1, (len(targets) // batch_size) + 3)):
            processed = self.process_jobs(limit=batch_size)
            rounds.append({"processed": len(processed)})
            if not processed:
                break
        return {
            "targets": len(targets),
            "reset": reset,
            "rounds": rounds,
            "stats": self.repo.collector_stats(),
        }

    def backfill(self, *, batch_size: int = 20, max_rounds: int = 20) -> dict[str, Any]:
        """Enqueue + process until no pending work or rounds exhausted."""
        rounds: list[dict[str, Any]] = []
        for _ in range(max_rounds):
            enqueued = self.poll_and_enqueue(limit=batch_size)
            processed = self.process_jobs(limit=batch_size)
            rounds.append({"enqueued": enqueued, "processed": len(processed)})
            if enqueued == 0 and not processed:
                break
            # Also drain remaining pending claimed in previous loops
            while True:
                more = self.process_jobs(limit=batch_size)
                if not more:
                    break
                rounds.append({"enqueued": 0, "processed": len(more)})
        return {"rounds": rounds, "stats": self.repo.collector_stats()}

    def _process_one(self, job: dict[str, Any]) -> dict[str, Any]:
        job_id = str(job["job_id"])
        prediction_id = int(job["prediction_id"])
        race_id = str(job["race_id"])
        created_at = str(job["prediction_created_at"])

        if not self.client:
            self.repo.finish_job(
                job_id=job_id,
                status="failed",
                last_error="PI_BASE_URL unset",
                retry=False,
            )
            return {"job_id": job_id, "status": "failed", "error": "PI_BASE_URL unset"}

        runners, sources, violations, latency_ms, fetch_err = fetch_and_collect(
            client=self.client,
            race_id=race_id,
            prediction_created_at=created_at,
        )

        payload = assemble_snapshot(
            job=job,
            runners=runners,
            sources=sources,
            anti_leak_violations=violations,
            fetch_error=fetch_err,
            latency_ms=latency_ms,
        )

        # V25: persist World signals into Research Snapshot only (no product mutation)
        try:
            from app.research.world_signal_instrumentation import (
                attach_world_signals_to_payload,
            )

            attach_world_signals_to_payload(payload, try_core=True)
        except Exception:
            payload["research_world_signals"] = {
                "schema_version": "expect-world-signal-instrumentation/1.0",
                "attach_error": True,
                "score_mutated": False,
                "prediction_mutated": False,
                "world_trigger_changed": False,
                "judgment_changed": False,
            }

        for src in sources:
            self.repo.log_source_event(
                job_id=job_id,
                prediction_id=prediction_id,
                feature_id=str(src.get("feature_id") or "bundle"),
                source_id=str(src.get("source_id") or "unknown"),
                success=bool(src.get("success")),
                observed_at=src.get("observed_at"),
                fetched_at=str(src.get("fetched_at") or _now()),
                latency_ms=latency_ms,
                missing_reason=fetch_err,
            )

        if violations > 0:
            payload["quality"]["anti_leak_rejected_fields"] = violations

        json_path = None
        try:
            json_path = write_snapshot_file(
                race_date=str(payload.get("race_date") or "unknown-date"),
                race_id=race_id,
                prediction_id=prediction_id,
                payload=payload,
            )
        except OSError as exc:
            fetch_err = f"store_error:{exc}"
            payload["capture_status"] = "failed"

        self.repo.save_snapshot(
            snapshot_id=str(payload["snapshot_id"]),
            prediction_id=prediction_id,
            race_id=race_id,
            race_date=payload.get("race_date"),
            capture_status=str(payload["capture_status"]),
            field_coverage=float(payload["quality"]["field_coverage"]),
            anti_leak_violations=violations,
            payload=payload,
            json_path=json_path,
        )
        try:
            self.repo.index_snapshot_features(
                snapshot_id=str(payload["snapshot_id"]),
                prediction_id=prediction_id,
                race_id=race_id,
                payload=payload,
            )
        except Exception as exc:  # noqa: BLE001 — index is secondary
            payload["quality"]["index_error"] = str(exc)

        final = str(payload["capture_status"])
        retry = final in ("partial", "failed") and int(job.get("attempt") or 0) < int(
            job.get("max_attempts") or 1
        )
        if retry and fetch_err and (
            fetch_err == "timeout"
            or fetch_err.startswith("url_error")
            or fetch_err.startswith("http_5")
        ):
            self.repo.finish_job(job_id=job_id, status="pending", last_error=fetch_err, retry=True)
        else:
            self.repo.finish_job(
                job_id=job_id,
                status="done" if final != "failed" else "failed",
                last_error=fetch_err,
                retry=False,
            )

        return {
            "job_id": job_id,
            "prediction_id": prediction_id,
            "status": final,
            "json_path": json_path,
            "error": fetch_err,
        }

    def run_once(self) -> dict[str, Any]:
        enqueued = self.poll_and_enqueue()
        processed = self.process_jobs()
        return {"enqueued": enqueued, "processed": processed, "stats": self.repo.collector_stats()}
