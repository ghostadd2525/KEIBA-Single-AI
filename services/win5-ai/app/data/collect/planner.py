# -*- coding: utf-8 -*-
"""Planner — 開催カレンダー → collect_targets + Availability Queue (C-4)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .budget import CollectBudget
from .contracts.availability import AvailabilityContext
from .contracts.calendar import RaceCalendar, expand_calendar_targets
from .contracts.targets import PlannerContract
from .manifest_store import build_planner_manifest, write_manifest
from .queue import CollectQueue
from .repository import CollectRunRepository, CollectTargetRepository


def _default_weekday_as_of(week_id: str) -> str:
    """week_id (Saturday) → 直前の金曜。WEEKDAY availability 評価用。"""
    d = datetime.strptime(str(week_id)[:10], "%Y-%m-%d").date()
    if d.weekday() >= 5:
        d = d - timedelta(days=d.weekday() - 4)
    return d.isoformat()


@dataclass(frozen=True)
class PlannerResult:
    planner_run_id: str
    week_id: str
    calendar_version: str
    targets_count: int
    jobs_enqueued: int
    jobs_not_generated: int
    enqueued_types: list[str]
    not_generated_types: list[str]
    manifest_path: str


class CollectPlanner:
    """
    Planner: 開催カレンダー (SoT) → collect_targets → Availability-filtered Queue.

    全 artifact を知っているが、Availability に従ってのみ enqueue。
    取得不可は SKIPPED ではなく未生成。
    """

    def __init__(
        self,
        *,
        runs: CollectRunRepository | None = None,
        targets: CollectTargetRepository | None = None,
        queue: CollectQueue | None = None,
        budget: CollectBudget | None = None,
    ) -> None:
        self.runs = runs or CollectRunRepository()
        self.targets = targets or CollectTargetRepository()
        self.queue = queue or CollectQueue()
        self.budget = budget or CollectBudget.from_env()

    def run(
        self,
        calendar: RaceCalendar,
        *,
        scheduled_for: str | None = None,
        availability: AvailabilityContext | None = None,
        draw_confirmed: bool | None = None,
    ) -> PlannerResult:
        target_rows = expand_calendar_targets(calendar)
        validated = PlannerContract.validate_targets_from_calendar(
            calendar_version=calendar.calendar_version,
            week_id=calendar.week_id,
            targets=target_rows,
        )

        run = self.runs.create(
            week_id=calendar.week_id,
            calendar_version=calendar.calendar_version,
        )
        planner_run_id = str(run["planner_run_id"])

        inserted = self.targets.insert_many(
            planner_run_id=planner_run_id,
            targets=[t.as_dict() for t in validated],
        )

        as_of = scheduled_for or _default_weekday_as_of(calendar.week_id)
        if availability is not None:
            context = availability
        else:
            context = AvailabilityContext(
                as_of_date=as_of,
                draw_confirmed=bool(draw_confirmed) if draw_confirmed is not None else False,
            )

        enqueue = self.queue.enqueue_available(
            planner_run_id=planner_run_id,
            week_id=calendar.week_id,
            targets=inserted,
            context=context,
            scheduled_for=scheduled_for,
            daily_limit=self.budget.daily_limit,
        )

        manifest = build_planner_manifest(
            calendar_version=calendar.calendar_version,
            week_id=calendar.week_id,
            planner_run_id=planner_run_id,
            total_races_expected=calendar.total_races_expected(),
            venue_count=calendar.venue_count(),
            race_count_per_venue=calendar.race_count_per_venue(),
            daily_limit=self.budget.daily_limit,
        )
        manifest_path = write_manifest(manifest)

        self.runs.finish(
            planner_run_id,
            status="success",
            targets_count=len(inserted),
            jobs_enqueued=enqueue.jobs_created,
            manifest_path=manifest_path,
            detail={
                "jobs_skipped_idempotent": enqueue.jobs_skipped,
                "jobs_not_generated": enqueue.jobs_not_generated,
                "enqueued_types": enqueue.enqueued_types,
                "not_generated_types": enqueue.not_generated_types,
                "scheduled_distribution": enqueue.scheduled_distribution,
                "availability": {
                    "as_of_date": context.as_of_date,
                    "draw_confirmed": context.draw_confirmed,
                },
                "budget_daily_limit": self.budget.daily_limit,
                "scope": "STATIC_CORE/availability-filtered",
            },
        )

        return PlannerResult(
            planner_run_id=planner_run_id,
            week_id=calendar.week_id,
            calendar_version=calendar.calendar_version,
            targets_count=len(inserted),
            jobs_enqueued=enqueue.jobs_created,
            jobs_not_generated=enqueue.jobs_not_generated,
            enqueued_types=list(enqueue.enqueued_types),
            not_generated_types=list(enqueue.not_generated_types),
            manifest_path=manifest_path,
        )
