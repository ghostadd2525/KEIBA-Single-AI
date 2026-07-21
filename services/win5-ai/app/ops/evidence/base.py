# -*- coding: utf-8 -*-
"""Improvement Evidence — shared envelope helpers."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "expect-improvement-evidence/1.0"
PIPELINE = "ops-result-automation/1.0"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def make_envelope(
    *,
    event_type: str,
    race_id: str | None,
    race_date: str,
    payload: dict[str, Any],
    model_version: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    ts = timestamp or now_iso()
    fp = fingerprint({"event_type": event_type, "race_id": race_id, "payload": payload})
    event_id = f"{event_type}:{race_id or race_date}:{ts}"
    return {
        "schema_version": SCHEMA,
        "event_type": event_type,
        "event_id": event_id,
        "timestamp": ts,
        "race_id": race_id,
        "race_date": race_date,
        "fingerprint": fp,
        "payload": payload,
        "version": {
            "model_version": model_version,
            "pipeline_version": PIPELINE,
        },
    }


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
