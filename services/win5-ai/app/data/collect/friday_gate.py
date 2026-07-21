# -*- coding: utf-8 -*-
"""Friday Gate — Prediction Ready / Complete Ready (C-5)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .manifest_store import (
    apply_friday_gate_manifest,
    read_manifest,
    write_manifest,
)
from .readiness import WeekReadiness, evaluate_week_readiness
from .repository import CollectJobRepository, CollectTargetRepository


@dataclass(frozen=True)
class FridayGateResult:
    week_id: str
    prediction_ready: bool
    complete_ready: bool
    prediction_ready_races: int
    total_races_expected: int
    manifest_path: str
    readiness: WeekReadiness

    def as_dict(self) -> dict[str, Any]:
        return {
            "week_id": self.week_id,
            "prediction_ready": self.prediction_ready,
            "complete_ready": self.complete_ready,
            "prediction_ready_races": self.prediction_ready_races,
            "total_races_expected": self.total_races_expected,
            "manifest_path": self.manifest_path,
            "readiness": self.readiness.as_dict(),
        }


class FridayGate:
    """
    Friday Gate: 正式な Prediction Ready / Complete Ready 判定と Manifest 更新。

    Manifest 責務:
      - Planner: expected / venue 初期化
      - Scheduler: collect / budget / 進捗カウント
      - Friday Gate: status.prediction_ready / status.complete_ready（正本）
    """

    def __init__(
        self,
        *,
        week_id: str,
        targets: CollectTargetRepository | None = None,
        jobs: CollectJobRepository | None = None,
    ) -> None:
        self.week_id = week_id
        self.targets = targets or CollectTargetRepository()
        self.jobs = jobs or CollectJobRepository()

    def evaluate(self) -> WeekReadiness:
        existing = read_manifest(self.week_id)
        expected = None
        if existing:
            expected = int((existing.get("races") or {}).get("total_races_expected") or 0)

        target_rows = self.targets.list_by_week(self.week_id)
        job_rows = self.jobs.list_by_week(self.week_id)
        return evaluate_week_readiness(
            week_id=self.week_id,
            targets=target_rows,
            jobs=job_rows,
            total_races_expected=expected if expected and expected > 0 else len(target_rows),
        )

    def run(self) -> FridayGateResult:
        readiness = self.evaluate()
        existing = read_manifest(self.week_id)
        if not existing:
            raise FileNotFoundError(f"manifest not found for week_id={self.week_id!r}")

        updated = apply_friday_gate_manifest(
            existing=existing,
            readiness=readiness,
        )
        path = write_manifest(updated)
        return FridayGateResult(
            week_id=self.week_id,
            prediction_ready=readiness.prediction_ready,
            complete_ready=readiness.complete_ready,
            prediction_ready_races=readiness.prediction_ready_races,
            total_races_expected=readiness.total_races_expected,
            manifest_path=path,
            readiness=readiness,
        )


def run_friday_gate(week_id: str) -> FridayGateResult:
    return FridayGate(week_id=week_id).run()
