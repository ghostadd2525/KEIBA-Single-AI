# -*- coding: utf-8 -*-
"""Prediction / Complete readiness evaluation — C-5."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .contracts.availability import AVAILABILITY_CONTRACT, ArtifactAvailability


def prediction_required_artifacts() -> list[ArtifactAvailability]:
    return [s for s in AVAILABILITY_CONTRACT.values() if s.prediction_required]


def all_contract_artifacts() -> list[ArtifactAvailability]:
    return list(AVAILABILITY_CONTRACT.values())


@dataclass(frozen=True)
class RaceReadiness:
    target_id: int
    race_date: str
    venue: str
    race_no: int
    prediction_ready: bool
    complete_ready: bool
    missing_prediction: tuple[str, ...] = ()
    missing_complete: tuple[str, ...] = ()


@dataclass(frozen=True)
class WeekReadiness:
    week_id: str
    total_races_expected: int
    prediction_ready_races: int
    complete_ready_races: int
    prediction_ready: bool
    complete_ready: bool
    races: tuple[RaceReadiness, ...] = ()
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "week_id": self.week_id,
            "total_races_expected": self.total_races_expected,
            "prediction_ready_races": self.prediction_ready_races,
            "complete_ready_races": self.complete_ready_races,
            "prediction_ready": self.prediction_ready,
            "complete_ready": self.complete_ready,
            "notes": list(self.notes),
            "races": [
                {
                    "target_id": r.target_id,
                    "race_date": r.race_date,
                    "venue": r.venue,
                    "race_no": r.race_no,
                    "prediction_ready": r.prediction_ready,
                    "complete_ready": r.complete_ready,
                    "missing_prediction": list(r.missing_prediction),
                    "missing_complete": list(r.missing_complete),
                }
                for r in self.races
            ],
        }


def evaluate_week_readiness(
    *,
    week_id: str,
    targets: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
    total_races_expected: int | None = None,
) -> WeekReadiness:
    """
    Prediction Ready:
      全対象レースで prediction_required artifact (race_meta, entries_core) が READY。

    Complete Ready:
      全対象レースで Availability Contract 上の全 artifact が READY。
      （odds/track 未生成・未 READY なら false — Prediction には影響しない）
    """
    expected = (
        int(total_races_expected)
        if total_races_expected is not None
        else len(targets)
    )

    # (target_id, artifact_type) -> status
    by_key: dict[tuple[int, str], str] = {}
    for job in jobs:
        tid = job.get("target_id")
        if tid is None:
            continue
        by_key[(int(tid), str(job.get("artifact_type") or ""))] = str(
            job.get("status") or ""
        )

    pred_specs = prediction_required_artifacts()
    all_specs = all_contract_artifacts()

    race_results: list[RaceReadiness] = []
    pred_ready_count = 0
    complete_ready_count = 0

    for target in targets:
        tid = int(target["id"])
        missing_pred: list[str] = []
        missing_complete: list[str] = []

        for spec in pred_specs:
            status = by_key.get((tid, spec.artifact_type))
            if status != "READY":
                missing_pred.append(spec.artifact_type)

        for spec in all_specs:
            status = by_key.get((tid, spec.artifact_type))
            if status != "READY":
                missing_complete.append(spec.artifact_type)

        is_pred = len(missing_pred) == 0
        is_complete = len(missing_complete) == 0
        if is_pred:
            pred_ready_count += 1
        if is_complete:
            complete_ready_count += 1

        race_results.append(
            RaceReadiness(
                target_id=tid,
                race_date=str(target.get("race_date") or ""),
                venue=str(target.get("venue") or ""),
                race_no=int(target.get("race_no") or 0),
                prediction_ready=is_pred,
                complete_ready=is_complete,
                missing_prediction=tuple(missing_pred),
                missing_complete=tuple(missing_complete),
            )
        )

    notes: list[str] = []
    if expected <= 0:
        notes.append("total_races_expected is 0")
    if pred_ready_count < expected:
        notes.append(
            f"prediction_ready_races {pred_ready_count} < expected {expected}"
        )

    prediction_ready = expected > 0 and pred_ready_count == expected
    complete_ready = expected > 0 and complete_ready_count == expected

    return WeekReadiness(
        week_id=week_id,
        total_races_expected=expected,
        prediction_ready_races=pred_ready_count,
        complete_ready_races=complete_ready_count,
        prediction_ready=prediction_ready,
        complete_ready=complete_ready,
        races=tuple(race_results),
        notes=tuple(notes),
    )
