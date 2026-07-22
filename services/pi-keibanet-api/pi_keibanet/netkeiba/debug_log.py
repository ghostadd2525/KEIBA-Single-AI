# -*- coding: utf-8 -*-
"""Structured logging + optional HTML capture for netkeiba fetches."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path


def debug_dir() -> Path | None:
    raw = os.environ.get("PI_NETKEIBA_DEBUG_DIR", "").strip()
    if not raw:
        return None
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_fetch(*, url: str, html: str, label: str) -> None:
    print(f"[pi-keibanet] fetch {label}: {url} (bytes={len(html.encode('utf-8', errors='replace'))})")
    out = debug_dir()
    if out is None:
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = re.sub(r"[^\w.-]+", "_", label)[:80]
    path = out / f"{stamp}_{safe}.html"
    path.write_text(html, encoding="utf-8")
    print(f"[pi-keibanet] saved html: {path}")
