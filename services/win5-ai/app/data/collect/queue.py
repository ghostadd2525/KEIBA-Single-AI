# -*- coding: utf-8 -*-
"""Queue — Availability-aware enqueue + weekday distribution (C-8)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .budget import CollectBudget
from .contracts.availability import (
    AvailabilityContext,
    ENQUEUEABLE_ARTIFACTS,
    available_enqueueable_artifacts,
    get_availability,
)
from .contracts.weekday_distribution import EnqueueSlot, plan_scheduled_dates
from .repository import CollectJobRepository, JobIdempotencyError


@dataclass(frozen=True)
class QueueEnqueueResult:
    jobs_created: int
    jobs_skipped: int
    jobs_not_generated: int
    job_ids: list[str]
    enqueued_types: list[str] = field(default_factory=list)
    not_generated_types: list[str] = field(default_factory=list)
    scheduled_distribution: dict[str, int] = field(default_factory=dict)


class CollectQueue:
    """
    Enqueue collect_jobs from collect_targets.

    Availability に従い、現在取得可能な artifact のみジョブ生成。
    scheduled_for 未指定時は Weekday Distribution で月〜金へ計画分散。
    """

    def __init__(self, jobs: CollectJobRepository | None = None) -> None:
        self.jobs = jobs or CollectJobRepository()

    def enqueue_available(
        self,
        *,
        planner_run_id: str,
        week_id: str,
        targets: list[dict[str, Any]],
        context: AvailabilityContext,
        scheduled_for: str | None = None,
        daily_limit: int | None = None,
    ) -> QueueEnqueueResult:
        created: list[str] = []
        skipped = 0
        not_generated = 0
        enqueued_types: set[str] = set()
        not_generated_types: set[str] = set()

        limit = (
            int(daily_limit)
            if daily_limit is not None
            else CollectBudget.from_env().daily_limit
        )

        # Build flat work list then assign scheduled_for in one pass
        work: list[tuple[dict[str, Any], str]] = []  # (target, artifact_type)
        for target in targets:
            race_date = str(target["race_date"])
            available = available_enqueueable_artifacts(
                context=context,
                race_date=race_date,
            )
            available_names = {a.artifact_type for a in available}
            for name in ENQUEUEABLE_ARTIFACTS:
                if name not in available_names:
                    not_generated += 1
                    not_generated_types.add(name)
            for spec in available:
                work.append((target, spec.artifact_type))

        slots = [
            EnqueueSlot(artifact_type=atype, race_date=str(t["race_date"]))
            for t, atype in work
        ]
        dates = plan_scheduled_dates(
            slots,
            week_id=week_id,
            context_as_of=context.as_of_date,
            daily_limit=limit,
            fixed_scheduled_for=scheduled_for,
        )

        distribution: dict[str, int] = {}
        for (target, artifact_type), sf in zip(work, dates):
            race_date = str(target["race_date"])
            spec = get_availability(artifact_type)
            job_id = self._job_id(week_id, target, artifact_type)
            try:
                self.jobs.create(
                    job_id=job_id,
                    week_id=week_id,
                    race_date=race_date,
                    race_id=str(target["race_id"]) if target.get("race_id") else None,
                    artifact_type=artifact_type,
                    kind=spec.kind,
                    priority=spec.priority,
                    planner_run_id=planner_run_id,
                    target_id=int(target["id"]),
                    scheduled_for=sf,
                    budget_cost=1,
                )
                created.append(job_id)
                enqueued_types.add(artifact_type)
                distribution[sf] = distribution.get(sf, 0) + 1
            except JobIdempotencyError:
                skipped += 1

        return QueueEnqueueResult(
            jobs_created=len(created),
            jobs_skipped=skipped,
            jobs_not_generated=not_generated,
            job_ids=created,
            enqueued_types=sorted(enqueued_types),
            not_generated_types=sorted(not_generated_types),
            scheduled_distribution=dict(sorted(distribution.items())),
        )

    def enqueue_race_meta_p1(
        self,
        *,
        planner_run_id: str,
        week_id: str,
        targets: list[dict[str, Any]],
        scheduled_for: str | None = None,
        daily_limit: int | None = None,
    ) -> QueueEnqueueResult:
        """Backward-compatible: enqueue race_meta as if weekday + no draw required."""
        from datetime import datetime, timedelta

        as_of = scheduled_for or (targets[0]["race_date"] if targets else "2099-01-01")
        d = datetime.strptime(str(as_of)[:10], "%Y-%m-%d").date()
        if d.weekday() >= 5:
            d = d - timedelta(days=d.weekday() - 4)
        context = AvailabilityContext(as_of_date=d.isoformat(), draw_confirmed=False)
        return self.enqueue_available(
            planner_run_id=planner_run_id,
            week_id=week_id,
            targets=targets,
            context=context,
            scheduled_for=scheduled_for,
            daily_limit=daily_limit,
        )

    @staticmethod
    def _job_id(week_id: str, target: dict[str, Any], artifact_type: str) -> str:
        return (
            f"job-{week_id}-{target.get('race_date')}-{target.get('venue')}-"
            f"{int(target.get('race_no') or 0)}-{artifact_type}"
        )
