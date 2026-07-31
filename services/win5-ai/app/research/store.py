# -*- coding: utf-8 -*-
"""Prediction Snapshot JSON store (Research-only)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import repo_root, snapshot_root


def write_snapshot_file(
    *,
    race_date: str,
    race_id: str,
    prediction_id: int,
    payload: dict[str, Any],
) -> str:
    root = snapshot_root()
    safe_date = race_date or "unknown-date"
    dir_path = root / safe_date / race_id
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / f"{prediction_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        return str(path.relative_to(repo_root())).replace("\\", "/")
    except ValueError:
        return str(path)
