# -*- coding: utf-8 -*-
"""Scheduler — dequeue + DYNAMIC refresh (C-6)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from . import state as sm
from .budget import CollectBudget
from .contracts.dynamic import get_dynamic_contract, is_dynamic_artifact
from .manifest_store import (
    build_scheduler_manifest_update,
    read_manifest,
    write_manifest,
)
from .readiness import evaluate_week_readiness
from .repository import CollectJobRepository, CollectTargetRepository


@dataclass(frozen=True)
class SchedulerResult:
    week_id: str
    dequeued_count: int
    manifest_path: str


@dataclass(frozen=True)
class DynamicRefreshResult:
    marked_stale: list[str] = field(default_factory=list)
    requeued: list[str] = field(default_factory=list)

    @property
    def marked_stale_count(self) -> int:
        return len(self.marked_stale)

    @property
    def requeued_count(self) -> int:
        return len(self.requeued)


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class CollectScheduler:
    """
    Scheduler: dequeue + collect/budget 進捗 + DYNAMIC refresh.

    READY → STALE_DYNAMIC（refresh_interval 経過・DYNAMIC のみ）
    STALE_DYNAMIC → PENDING（再取得対象）

    status.prediction_ready / complete_ready は Friday Gate 正本。
    status.dynamic_ready / dynamic_stale は本 Scheduler が更新可。
    """

    def __init__(
        self,
        *,
        week_id: str,
        as_of_date: str,
        jobs: CollectJobRepository | None = None,
        targets: CollectTargetRepository | None = None,
        budget: CollectBudget | None = None,
    ) -> None:
        self.week_id = week_id
        self.as_of_date = as_of_date
        self.jobs = jobs or CollectJobRepository()
        self.targets = targets or CollectTargetRepository()
        self.budget = budget or CollectBudget.from_env()
        self._dequeued_count = 0

    def dequeue_pending(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        batch = self.jobs.dequeue_pending(
            week_id=self.week_id,
            as_of_date=self.as_of_date,
            budget=self.budget,
            limit=limit,
        )
        self._dequeued_count += len(batch)
        return batch

    def process_dynamic_refresh(
        self,
        *,
        now: datetime | None = None,
    ) -> DynamicRefreshResult:
        """
        DYNAMIC のみ:
          READY + interval 経過 → STALE_DYNAMIC
          STALE_DYNAMIC → PENDING
        STATIC は変更しない。
        """
        as_of = now or datetime.now(timezone.utc)
        marked: list[str] = []
        requeued: list[str] = []

        for job in self.jobs.list_dynamic_jobs(self.week_id, status=sm.READY):
            artifact_type = str(job.get("artifact_type") or "")
            if not is_dynamic_artifact(artifact_type):
                continue
            spec = get_dynamic_contract(artifact_type)
            if not spec.auto_refresh:
                continue
            updated = _parse_ts(str(job.get("updated_at") or ""))
            if updated is None:
                continue
            age = (as_of - updated).total_seconds()
            if age < float(spec.refresh_interval_sec or 0):
                continue
            job_id = str(job["job_id"])
            self.jobs.transition(job_id, sm.STALE_DYNAMIC)
            marked.append(job_id)

        for job in self.jobs.list_dynamic_jobs(self.week_id, status=sm.STALE_DYNAMIC):
            job_id = str(job["job_id"])
            self.jobs.transition(job_id, sm.PENDING)
            requeued.append(job_id)

        return DynamicRefreshResult(marked_stale=marked, requeued=requeued)

    def finish(self) -> SchedulerResult:
        existing = read_manifest(self.week_id)
        if not existing:
            raise FileNotFoundError(f"manifest not found for week_id={self.week_id!r}")

        stats = self.jobs.count_by_status(self.week_id)
        target_rows = self.targets.list_by_week(self.week_id)
        job_rows = self.jobs.list_by_week(self.week_id)
        expected = int((existing.get("races") or {}).get("total_races_expected") or 0)
        readiness = evaluate_week_readiness(
            week_id=self.week_id,
            targets=target_rows,
            jobs=job_rows,
            total_races_expected=expected if expected > 0 else len(target_rows),
        )
        race_meta_ready = self.jobs.count_race_meta_ready_races(self.week_id)
        dyn = self.jobs.count_dynamic_status(self.week_id)
        dynamic_ready = dyn["total"] > 0 and dyn["ready"] == dyn["total"]
        dynamic_stale = dyn["stale"] > 0 or (
            dyn["refreshing"] > 0 and dyn["ready"] < dyn["total"]
        )

        updated = build_scheduler_manifest_update(
            existing=existing,
            collect_stats=stats,
            budget=self.budget.as_dict(),
            total_races_ready=race_meta_ready,
            prediction_ready_races=readiness.prediction_ready_races,
            dynamic_ready=dynamic_ready,
            dynamic_stale=dynamic_stale,
        )
        path = write_manifest(updated)
        return SchedulerResult(
            week_id=self.week_id,
            dequeued_count=self._dequeued_count,
            manifest_path=path,
        )
