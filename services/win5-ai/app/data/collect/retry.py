# -*- coding: utf-8 -*-
"""Retry — PARTIAL/FAILED → PENDING after retry_after (C-2)."""
from __future__ import annotations

from dataclasses import dataclass

from . import state as sm
from .repository import CollectJobRepository


@dataclass(frozen=True)
class RetryResult:
    requeued: int
    job_ids: list[str]


class CollectRetry:
    """
    Re-enqueue jobs when retry_after has elapsed.

    Only PARTIAL / FAILED are eligible. Same job row → PENDING.
    """

    def __init__(self, jobs: CollectJobRepository | None = None) -> None:
        self.jobs = jobs or CollectJobRepository()

    def process(self, *, week_id: str, as_of_date: str) -> RetryResult:
        due = self.jobs.list_retry_due(week_id=week_id, as_of_date=as_of_date)
        requeued: list[str] = []
        for job in due:
            job_id = str(job["job_id"])
            attempt = int(job.get("attempt") or 0)
            max_attempts = int(job.get("max_attempts") or 5)
            if attempt >= max_attempts:
                continue
            self.jobs.requeue_for_retry(job_id)
            requeued.append(job_id)
        return RetryResult(requeued=len(requeued), job_ids=requeued)
