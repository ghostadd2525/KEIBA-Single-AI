# -*- coding: utf-8 -*-
"""Classify / probe existing D1/D2 HTML caches (read-only, HTTP 0)."""
from __future__ import annotations

import re
from pathlib import Path

_SAFE_ID = re.compile(r"^[A-Za-z0-9_]+$")


def classify_horse_id(raw: str | None) -> tuple[str, str]:
    """Return (normalized_id, format). Never invent IDs."""
    if raw is None:
        return "", "invalid"
    s = str(raw).strip()
    if not s:
        return "", "invalid"
    if not _SAFE_ID.match(s):
        return s, "invalid"
    if len(s) == 10 and s.isdigit():
        return s, "netkeiba_10digit"
    # foreign / other canonical netkeiba ids (e.g. 000a014377)
    if re.fullmatch(r"[0-9a-fA-F]{6,}", s) or re.fullmatch(r"[0-9a-zA-Z]{6,16}", s):
        return s, "netkeiba_other_canonical"
    return s, "invalid"


def find_d1_html(horse_id: str, roots: list[Path]) -> Path | None:
    if not horse_id or not _SAFE_ID.match(horse_id):
        return None
    names = [
        f"{horse_id}.html",
        f"horse_{horse_id}.html",
        f"{horse_id}/index.html",
    ]
    for root in roots:
        if not root:
            continue
        for name in names:
            p = Path(root) / name
            if p.is_file():
                return p
    return None


def find_d2_html(horse_id: str, roots: list[Path]) -> Path | None:
    if not horse_id or not _SAFE_ID.match(horse_id):
        return None
    names = [
        f"{horse_id}.html",
        f"ped_{horse_id}.html",
        f"horse_ped_{horse_id}.html",
        f"{horse_id}/ped.html",
        f"ped/{horse_id}.html",
    ]
    for root in roots:
        if not root:
            continue
        for name in names:
            p = Path(root) / name
            if p.is_file():
                return p
    return None
