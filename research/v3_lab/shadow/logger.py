# -*- coding: utf-8 -*-
"""A-05 Shadow Logger — JSONL only; no purchase / API side effects."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ShadowSettings, load_shadow_settings


class ShadowLogger:
    """Append-only JSONL logger for Shadow race records."""

    def __init__(self, settings: ShadowSettings | None = None) -> None:
        self.settings = settings or load_shadow_settings()
        self.log_dir = Path(self.settings.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        self.path = self.log_dir / f"a05_shadow_{day}.jsonl"

    def write(self, record: dict[str, Any]) -> Path:
        payload = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "schema": "v3-a05-shadow-race/1.0",
            "phase": self.settings.phase,
            **record,
        }
        # Never log as purchase instruction
        payload["purchase_executed"] = False
        payload["purchase_forbidden"] = True
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return self.path

    def write_many(self, records: list[dict[str, Any]]) -> Path:
        for r in records:
            self.write(r)
        return self.path


__all__ = ["ShadowLogger"]
