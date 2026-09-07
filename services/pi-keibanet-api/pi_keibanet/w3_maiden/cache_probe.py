# -*- coding: utf-8 -*-
"""Existing PAGE-C HTML probe (no HTTP)."""
from __future__ import annotations

from pathlib import Path


def find_page_c_html(race_id: str, cache_roots: list[Path]) -> Path | None:
    """Locate `{race_id}.html` under research PAGE-C cache roots (W2-compatible)."""
    for root in cache_roots:
        if not root:
            continue
        p = Path(root) / f"{race_id}.html"
        if p.is_file():
            return p
    return None
