# -*- coding: utf-8 -*-
"""Shared netkeiba domain halt signal (PAGE-A1 block → conservative PAGE-C stop hint).

Does NOT modify W2 seal/index. W2 may later read this file; C4 only writes/clears.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_domain_halt(
    path: Path,
    *,
    reason: str,
    http_status: int | None,
    source: str = "netkeiba_page_a1",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "halt": True,
        "source": source,
        "reason": reason,
        "http_status": http_status,
        "affects": ["c4_page_a1", "page_c_background"],
        "note": "Conservative domain halt. Does not alter W2 seal. P1 independent.",
        "updated_at": _iso(),
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def clear_domain_halt(path: Path) -> None:
    if not path.exists():
        return
    payload = {
        "halt": False,
        "source": "netkeiba_page_a1",
        "reason": "cleared_on_recovery",
        "updated_at": _iso(),
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_domain_halt(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
