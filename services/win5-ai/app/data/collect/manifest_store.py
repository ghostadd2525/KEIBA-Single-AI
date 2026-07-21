# -*- coding: utf-8 -*-
"""Weekly Manifest persistence — C-5.

Manifest 更新責務:
  Planner     — expected / venue / budget 初期化、status=false
  Scheduler   — collect 集計・budget used・total_races_ready（進捗）
                status.prediction_ready / complete_ready は触らない
  Friday Gate — status.prediction_ready / complete_ready の正本更新
  Collector   — Manifest を更新しない
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts.manifest import MANIFEST_SCHEMA_VERSION, assert_valid_manifest
from .readiness import WeekReadiness


def repo_root() -> Path:
    return Path(__file__).resolve().parents[6]


def manifest_root() -> Path:
    env = (os.environ.get("EXPECT_COLLECT_MANIFEST_DIR") or "").strip()
    if env:
        return Path(env)
    return repo_root() / "evidence" / "supply" / "manifests"


def manifest_path_for_week(week_id: str) -> Path:
    token = week_id.replace("-", "_")
    return manifest_root() / f"week_{token}.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_planner_manifest(
    *,
    calendar_version: str,
    week_id: str,
    planner_run_id: str,
    total_races_expected: int,
    venue_count: int,
    race_count_per_venue: dict[str, dict[str, int]],
    daily_limit: int,
) -> dict[str, Any]:
    """Planner: expected / venue 初期化。status は false 固定。"""
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "week_id": week_id,
        "calendar_version": calendar_version,
        "planner_run_id": planner_run_id,
        "generated_at": _now_iso(),
        "data_scope": {
            "venues": "all_jra_weekend",
            "race_numbers": "1-12_per_calendar",
            "note": "Single AI catalog supply — not Win5 five-leg subset",
        },
        "races": {
            "total_races_expected": total_races_expected,
            "total_races_ready": 0,
            "venue_count": venue_count,
            "race_count_per_venue": race_count_per_venue,
            "prediction_ready_races": 0,
        },
        "collect": {"ready": 0, "partial": 0, "failed": 0, "retry": 0},
        "budget": {
            "daily_limit": daily_limit,
            "used": 0,
            "remaining": daily_limit,
        },
        "status": {
            "prediction_ready": False,
            "complete_ready": False,
            "dynamic_ready": False,
            "dynamic_stale": False,
        },
        "notes": [],
    }


def write_manifest(manifest: dict[str, Any]) -> str:
    assert_valid_manifest(manifest)
    path = manifest_path_for_week(str(manifest["week_id"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def read_manifest(week_id: str) -> dict[str, Any] | None:
    path = manifest_path_for_week(week_id)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_scheduler_manifest_update(
    *,
    existing: dict[str, Any],
    collect_stats: dict[str, int],
    budget: dict[str, int],
    total_races_ready: int,
    prediction_ready_races: int | None = None,
    dynamic_ready: bool | None = None,
    dynamic_stale: bool | None = None,
) -> dict[str, Any]:
    """
    Scheduler: collect / budget / 進捗 + dynamic_*。

    status.prediction_ready / complete_ready は Friday Gate 正本のため変更しない。
    status.dynamic_ready / dynamic_stale は Prediction Ready と独立。
    """
    manifest = dict(existing)
    races = dict(manifest.get("races") or {})
    races["total_races_ready"] = total_races_ready
    if prediction_ready_races is not None:
        races["prediction_ready_races"] = prediction_ready_races
    manifest["races"] = races
    manifest["collect"] = {
        "ready": int(collect_stats.get("ready", 0)),
        "partial": int(collect_stats.get("partial", 0)),
        "failed": int(collect_stats.get("failed", 0)),
        "retry": int(collect_stats.get("retry", 0)),
    }
    manifest["budget"] = {
        "daily_limit": int(budget["daily_limit"]),
        "used": int(budget["used"]),
        "remaining": int(budget["remaining"]),
    }
    status = dict(manifest.get("status") or {})
    status.setdefault("prediction_ready", False)
    status.setdefault("complete_ready", False)
    if dynamic_ready is not None:
        status["dynamic_ready"] = bool(dynamic_ready)
    else:
        status.setdefault("dynamic_ready", False)
    if dynamic_stale is not None:
        status["dynamic_stale"] = bool(dynamic_stale)
    else:
        status.setdefault("dynamic_stale", False)
    manifest["status"] = status
    manifest["generated_at"] = _now_iso()
    return manifest


def apply_friday_gate_manifest(
    *,
    existing: dict[str, Any],
    readiness: WeekReadiness,
) -> dict[str, Any]:
    """Friday Gate: prediction status 正本。dynamic_* は維持。"""
    manifest = dict(existing)
    races = dict(manifest.get("races") or {})
    races["prediction_ready_races"] = readiness.prediction_ready_races
    races["total_races_ready"] = readiness.prediction_ready_races
    manifest["races"] = races
    prev = dict(manifest.get("status") or {})
    manifest["status"] = {
        "prediction_ready": readiness.prediction_ready,
        "complete_ready": readiness.complete_ready,
        "dynamic_ready": bool(prev.get("dynamic_ready", False)),
        "dynamic_stale": bool(prev.get("dynamic_stale", False)),
    }
    notes = list(manifest.get("notes") or [])
    for note in readiness.notes:
        if note not in notes:
            notes.append(note)
    manifest["notes"] = notes
    manifest["generated_at"] = _now_iso()
    return manifest
