# -*- coding: utf-8 -*-
"""Horse number integrity gate for race_refresh → Feature CSV."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

REASON_INCOMPLETE = "Race Refresh Incomplete"
REASON_HORSE_NUMBER_NOT_READY = "Horse Number Not Ready"
REASON_FRAME_NOT_READY = "Frame Number Not Ready"
REASON_MISSING_HORSE_ID = "Horse Id Missing"
REASON_FALLBACK_HORSE_NUMBER = "Fallback Horse Number Forbidden"

_VALID_SOURCES = frozenset({"umaban"})
_FALLBACK_SOURCES = frozenset({"fallback", "seq", "tr_id", "fallback_number"})


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    text = str(value).strip()
    return text == "" or text.lower() in {"nan", "none", "null"}


def _as_positive_int(value: Any) -> int | None:
    if _is_blank(value):
        return None
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


@dataclass
class HorseNumberIntegrityRace:
    race_id: str
    ok: bool
    runner_count: int = 0
    horse_number_ready: bool = False
    frame_number_ready: bool = False
    missing_horse_id: list[str] = field(default_factory=list)
    missing_horse_number: list[str] = field(default_factory=list)
    fallback_horse_number: list[str] = field(default_factory=list)
    missing_frame_number: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HorseNumberIntegrityReport:
    date: str
    checked_at: str
    ok: bool
    races_total: int = 0
    races_ok: int = 0
    races_ng: int = 0
    ready_race_ids: list[str] = field(default_factory=list)
    blocked_race_ids: list[str] = field(default_factory=list)
    races: list[HorseNumberIntegrityRace] = field(default_factory=list)
    log_lines: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["check"] = "Horse Number Integrity"
        return payload


def _runner_rows(runners: pd.DataFrame | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(runners, pd.DataFrame):
        if runners.empty:
            return []
        return runners.to_dict(orient="records")
    return list(runners or [])


def validate_race_runners(race_id: str, rows: list[dict[str, Any]]) -> HorseNumberIntegrityRace:
    """Validate one race: every runner needs horse_id + formal horse_number."""
    result = HorseNumberIntegrityRace(race_id=str(race_id), ok=False, runner_count=len(rows))
    if not rows:
        result.reasons = [REASON_INCOMPLETE, REASON_HORSE_NUMBER_NOT_READY]
        return result

    for row in rows:
        hid = "" if _is_blank(row.get("horse_id")) else str(row.get("horse_id")).strip()
        label = hid or str(row.get("horse_name") or "").strip() or "?"
        if not hid:
            result.missing_horse_id.append(label)

        source = str(row.get("horse_number_source") or "").strip().lower()
        hn = _as_positive_int(row.get("horse_number"))
        if source in _FALLBACK_SOURCES or source.startswith("fallback"):
            result.fallback_horse_number.append(label)
            hn = None
        if hn is None:
            result.missing_horse_number.append(label)
        elif source and source not in _VALID_SOURCES:
            # Unknown non-umaban source is treated as not formal.
            result.fallback_horse_number.append(label)
            result.missing_horse_number.append(label)

        frame = row.get("frame_number", row.get("frame"))
        frame_i = _as_positive_int(frame)
        if frame_i is None:
            result.missing_frame_number.append(label)

    result.horse_number_ready = (
        not result.missing_horse_id
        and not result.missing_horse_number
        and not result.fallback_horse_number
    )
    result.frame_number_ready = not result.missing_frame_number

    reasons: list[str] = []
    if not result.horse_number_ready:
        reasons.append(REASON_INCOMPLETE)
        reasons.append(REASON_HORSE_NUMBER_NOT_READY)
        if result.missing_horse_id:
            reasons.append(REASON_MISSING_HORSE_ID)
        if result.fallback_horse_number:
            reasons.append(REASON_FALLBACK_HORSE_NUMBER)
    if not result.frame_number_ready:
        reasons.append(REASON_FRAME_NOT_READY)
    result.reasons = reasons
    # Feature CSV hard gate: horse_id + formal horse_number for all runners.
    result.ok = result.horse_number_ready
    return result


def validate_runners_horse_number_integrity(
    runners: pd.DataFrame | list[dict[str, Any]],
    *,
    date: str = "",
    race_ids: set[str] | list[str] | None = None,
) -> HorseNumberIntegrityReport:
    rows = _runner_rows(runners)
    by_race: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        rid = str(row.get("race_id") or "").strip()
        if not rid:
            continue
        if race_ids is not None and rid not in {str(x) for x in race_ids}:
            continue
        by_race.setdefault(rid, []).append(row)

    if race_ids is not None:
        for rid in sorted({str(x) for x in race_ids}):
            by_race.setdefault(rid, [])

    checked_at = datetime.now(timezone.utc).isoformat()
    races = [validate_race_runners(rid, by_race[rid]) for rid in sorted(by_race)]
    ready = [r.race_id for r in races if r.ok]
    blocked = [r.race_id for r in races if not r.ok]
    log_lines: list[str] = []
    for race in races:
        if race.ok:
            continue
        log_lines.append(
            f"[race-refresh] {REASON_INCOMPLETE}: race_id={race.race_id} "
            f"reasons={','.join(race.reasons)}"
        )
        if not race.horse_number_ready:
            log_lines.append(
                f"[race-refresh] {REASON_HORSE_NUMBER_NOT_READY}: race_id={race.race_id} "
                f"missing_horse_number={len(race.missing_horse_number)} "
                f"fallback={len(race.fallback_horse_number)} "
                f"missing_horse_id={len(race.missing_horse_id)}"
            )
        if not race.frame_number_ready:
            log_lines.append(
                f"[race-refresh] {REASON_FRAME_NOT_READY}: race_id={race.race_id} "
                f"missing_frame={len(race.missing_frame_number)}"
            )

    report = HorseNumberIntegrityReport(
        date=str(date or ""),
        checked_at=checked_at,
        ok=len(blocked) == 0 and len(races) > 0,
        races_total=len(races),
        races_ok=len(ready),
        races_ng=len(blocked),
        ready_race_ids=ready,
        blocked_race_ids=blocked,
        races=races,
        log_lines=log_lines,
    )
    if not races:
        report.ok = True
        report.log_lines.append("[race-refresh] Horse Number Integrity: no races to check")
    return report


def write_integrity_report(report: HorseNumberIntegrityReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    latest = path.parent / "horse_number_integrity_latest.json"
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def load_integrity_report(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def purge_feature_race_ids(features_df: pd.DataFrame, race_ids: set[str]) -> pd.DataFrame:
    if features_df is None or features_df.empty or not race_ids or "race_id" not in features_df.columns:
        return features_df
    blocked = {str(x) for x in race_ids}
    return features_df[~features_df["race_id"].astype(str).isin(blocked)].copy()


__all__ = [
    "REASON_FALLBACK_HORSE_NUMBER",
    "REASON_FRAME_NOT_READY",
    "REASON_HORSE_NUMBER_NOT_READY",
    "REASON_INCOMPLETE",
    "REASON_MISSING_HORSE_ID",
    "HorseNumberIntegrityRace",
    "HorseNumberIntegrityReport",
    "load_integrity_report",
    "purge_feature_race_ids",
    "validate_race_runners",
    "validate_runners_horse_number_integrity",
    "write_integrity_report",
]
