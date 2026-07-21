# -*- coding: utf-8 -*-
"""Weekly Manifest contract helpers — C-0."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA_VERSION = "expect-collect-week-manifest/1.1"

_REPO_ROOT = Path(__file__).resolve().parents[6]
_SCHEMA_PATH = (
    _REPO_ROOT
    / "contracts"
    / "expect-collect-week-manifest"
    / "1.1"
    / "schema.json"
)


def schema_path() -> Path:
    return _SCHEMA_PATH


def load_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_manifest_structure(manifest: dict[str, Any]) -> list[str]:
    """Lightweight structural validation (full schema in contract tests)."""
    errors: list[str] = []
    required_top = (
        "schema_version",
        "week_id",
        "calendar_version",
        "planner_run_id",
        "generated_at",
        "races",
        "collect",
        "budget",
        "status",
    )
    for key in required_top:
        if key not in manifest:
            errors.append(f"missing required field: {key}")

    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        errors.append(
            f"schema_version must be {MANIFEST_SCHEMA_VERSION!r}, got {manifest.get('schema_version')!r}"
        )

    races = manifest.get("races") or {}
    for key in (
        "total_races_expected",
        "total_races_ready",
        "venue_count",
        "race_count_per_venue",
        "prediction_ready_races",
    ):
        if key not in races:
            errors.append(f"missing races.{key}")

    collect = manifest.get("collect") or {}
    for key in ("ready", "partial", "failed", "retry"):
        if key not in collect:
            errors.append(f"missing collect.{key}")

    budget = manifest.get("budget") or {}
    for key in ("daily_limit", "used", "remaining"):
        if key not in budget:
            errors.append(f"missing budget.{key}")

    status = manifest.get("status") or {}
    for key in ("prediction_ready", "complete_ready", "dynamic_ready", "dynamic_stale"):
        if key not in status:
            errors.append(f"missing status.{key}")

    expected = races.get("total_races_expected")
    venue_count = races.get("venue_count")
    if isinstance(expected, int) and isinstance(venue_count, int) and expected < 0:
        errors.append("races.total_races_expected must be >= 0")
    if isinstance(venue_count, int) and venue_count < 0:
        errors.append("races.venue_count must be >= 0")

    return errors


def assert_valid_manifest(manifest: dict[str, Any]) -> None:
    errors = validate_manifest_structure(manifest)
    if errors:
        raise ValueError("; ".join(errors))
