# -*- coding: utf-8 -*-
"""Structured ops logging for prediction provenance."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _log_dir() -> Path:
    env = (os.environ.get("EXPECT_AI_LOG_DIR") or "").strip()
    if env:
        return Path(env)
    # services/win5-ai/app/diagnostics → parents[2] = services/win5-ai
    return Path(__file__).resolve().parents[2] / "var" / "logs"


def log_fallback_event(
    *,
    race_id: str,
    engine_source: str,
    fallback_reason: str | None = None,
    core_race_id: str | None = None,
    detail: str | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Append one JSONL line. Returns log file path."""
    directory = _log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "prediction_fallback.jsonl"
    row: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "race_id": race_id,
        "engine_source": engine_source,
        "fallback_reason": fallback_reason,
        "core_race_id": core_race_id,
        "detail": detail,
    }
    if extra:
        row["extra"] = extra
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path
