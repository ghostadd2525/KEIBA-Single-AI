# -*- coding: utf-8 -*-
"""KeibaNet Collector — STATIC_CORE race_meta + entries_core (C-4)."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import quote, urlencode

from . import state as sm
from .contracts import entries_core as entries_core_contract
from .contracts import odds as odds_contract
from .contracts import race_meta as race_meta_contract
from .contracts import track as track_contract
from .contracts.retry import compute_retry_after
from .keibanet.client import KeibaNetClient, KeibaNetError
from .raw_store import write_entries_core, write_odds, write_race_meta, write_track
from .repository import CollectArtifactRepository, CollectJobRepository, CollectTargetRepository
from .validator import (
    ValidationResult,
    validate_entries_core,
    validate_odds,
    validate_race_meta,
    validate_track,
)


class CollectJobNotSupportedError(ValueError):
    """Job kind/artifact_type outside supported scope."""


@dataclass(frozen=True)
class CollectJobResult:
    job_id: str
    final_status: str
    artifact_uid: str | None
    raw_path: str | None
    validation: ValidationResult | None
    http_status: int | None = None
    error: str | None = None


_SUPPORTED = {
    race_meta_contract.ARTIFACT_TYPE: {
        "kind": race_meta_contract.KIND,
        "path": "/v1/static/race_meta",
        "write": write_race_meta,
        "validate": validate_race_meta,
    },
    entries_core_contract.ARTIFACT_TYPE: {
        "kind": entries_core_contract.KIND,
        "path": "/v1/static/entries_core",
        "write": write_entries_core,
        "validate": validate_entries_core,
    },
    odds_contract.ARTIFACT_TYPE: {
        "kind": odds_contract.KIND,
        "path": "/v1/dynamic/odds",
        "write": write_odds,
        "validate": validate_odds,
    },
    track_contract.ARTIFACT_TYPE: {
        "kind": track_contract.KIND,
        "path": "/v1/dynamic/track",
        "write": write_track,
        "validate": validate_track,
    },
}


class KeibaNetCollector:
    """
    Collector: STATIC_CORE (race_meta/entries_core) + DYNAMIC (odds/track 最小).

    Flow: Job → KeibaNetClient → Raw Store → Artifact → Validator → READY | PARTIAL
    """

    def __init__(
        self,
        *,
        client: KeibaNetClient,
        jobs: CollectJobRepository | None = None,
        artifacts: CollectArtifactRepository | None = None,
        targets: CollectTargetRepository | None = None,
    ) -> None:
        self.client = client
        self.jobs = jobs or CollectJobRepository()
        self.artifacts = artifacts or CollectArtifactRepository()
        self.targets = targets or CollectTargetRepository()

    def run_job(self, job_id: str) -> CollectJobResult:
        job = self.jobs.get(job_id)
        if not job:
            raise KeyError(f"collect_job not found: {job_id}")

        handler = self._assert_supported(job)
        artifact_type = str(job.get("artifact_type") or "")

        current = str(job.get("status") or "")
        if current == sm.READY:
            return CollectJobResult(
                job_id=job_id,
                final_status=sm.READY,
                artifact_uid=None,
                raw_path=None,
                validation=None,
            )
        if current == sm.SKIPPED:
            return CollectJobResult(
                job_id=job_id,
                final_status=sm.SKIPPED,
                artifact_uid=None,
                raw_path=None,
                validation=None,
            )
        if current != sm.PENDING:
            raise ValueError(f"job {job_id!r} cannot start from status {current!r}")

        self.jobs.transition(job_id, sm.RUNNING, attempt=int(job.get("attempt") or 0) + 1)
        job = self.jobs.get(job_id) or job
        attempt = int(job.get("attempt") or 1)

        target = self._load_target(job)
        url_path = self._build_path(handler["path"], job, target)

        try:
            response = self.client.fetch(url_path)
        except KeibaNetError as exc:
            self._mark_failed(job_id, attempt=attempt, last_error=str(exc))
            return CollectJobResult(
                job_id=job_id,
                final_status=sm.FAILED,
                artifact_uid=None,
                raw_path=None,
                validation=None,
                error=str(exc),
            )

        if not response.ok:
            err = f"HTTP {response.status_code} from KeibaNet"
            self._mark_failed(job_id, attempt=attempt, last_error=err)
            return CollectJobResult(
                job_id=job_id,
                final_status=sm.FAILED,
                artifact_uid=None,
                raw_path=None,
                validation=None,
                http_status=response.status_code,
                error=err,
            )

        race_id = self._resolve_race_id(job, target, response.body)
        write_fn: Callable[[str, bytes], dict[str, Any]] = handler["write"]
        stored = write_fn(race_id, response.body)

        artifact_uid = f"art-{job_id}-{uuid.uuid4().hex[:8]}"
        self.artifacts.create(
            artifact_uid=artifact_uid,
            job_id=job_id,
            week_id=str(job["week_id"]),
            race_date=str(job["race_date"]),
            race_id=race_id,
            artifact_type=artifact_type,
            kind=str(handler["kind"]),
            status=sm.RUNNING,
            raw_path=stored["raw_path"],
            content_hash=stored["content_hash"],
        )
        self.jobs.link_artifact(job_id, artifact_uid)

        validate_fn = handler["validate"]
        validation = validate_fn(http_ok=True, body=response.body)
        if validation.ok:
            self.artifacts.transition(artifact_uid, sm.READY)
            self.jobs.transition(job_id, sm.READY)
            final_status = sm.READY
        else:
            self.artifacts.transition(
                artifact_uid,
                sm.PARTIAL,
                validation_errors=validation.errors,
            )
            self._mark_partial(
                job_id,
                attempt=attempt,
                validation_errors=validation.errors,
            )
            final_status = sm.PARTIAL

        return CollectJobResult(
            job_id=job_id,
            final_status=final_status,
            artifact_uid=artifact_uid,
            raw_path=stored["raw_path"],
            validation=validation,
            http_status=response.status_code,
        )

    def _mark_failed(
        self,
        job_id: str,
        *,
        attempt: int,
        last_error: str,
    ) -> None:
        self.jobs.transition(
            job_id,
            sm.FAILED,
            last_error=last_error,
            retry_after=compute_retry_after(attempt=attempt),
        )

    def _mark_partial(
        self,
        job_id: str,
        *,
        attempt: int,
        validation_errors: list[dict[str, str]],
    ) -> None:
        self.jobs.transition(
            job_id,
            sm.PARTIAL,
            validation_errors=validation_errors,
            retry_after=compute_retry_after(attempt=attempt),
        )

    def _assert_supported(self, job: dict[str, Any]) -> dict[str, Any]:
        kind = str(job.get("kind") or "")
        artifact_type = str(job.get("artifact_type") or "")
        handler = _SUPPORTED.get(artifact_type)
        if not handler or kind != handler["kind"]:
            raise CollectJobNotSupportedError(
                f"unsupported collect job kind={kind!r} artifact_type={artifact_type!r}"
            )
        return handler

    def _load_target(self, job: dict[str, Any]) -> dict[str, Any]:
        target_id = job.get("target_id")
        if target_id is None:
            raise ValueError(f"job {job['job_id']!r} missing target_id")
        target = self.targets.get(int(target_id))
        if not target:
            raise KeyError(f"collect_target not found: {target_id}")
        return target

    def _build_path(self, base: str, job: dict[str, Any], target: dict[str, Any]) -> str:
        params = urlencode(
            {
                "date": str(job.get("race_date") or target.get("race_date")),
                "venue": str(target.get("venue") or ""),
                "race_no": int(target.get("race_no") or 0),
            },
            quote_via=quote,
        )
        return f"{base}?{params}"

    def _resolve_race_id(
        self,
        job: dict[str, Any],
        target: dict[str, Any],
        body: bytes,
    ) -> str:
        for candidate in (job.get("race_id"), target.get("race_id")):
            if candidate:
                return str(candidate)
        try:
            payload = json.loads(body.decode("utf-8"))
            if isinstance(payload, dict) and payload.get("race_id"):
                return str(payload["race_id"])
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        venue = str(target.get("venue") or "unknown")
        race_no = int(target.get("race_no") or 0)
        race_date = str(job.get("race_date") or target.get("race_date") or "")
        return f"{race_date}_{venue}_{race_no}"
