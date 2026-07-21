# -*- coding: utf-8 -*-
"""Raw Store — evidence/supply/raw/ (C-1 / C-4)."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[6]


def raw_root() -> Path:
    env = (os.environ.get("EXPECT_COLLECT_RAW_DIR") or "").strip()
    if env:
        return Path(env)
    return repo_root() / "evidence" / "supply" / "raw"


def _safe_race_id(race_id: str) -> str:
    return str(race_id).strip().replace("/", "_").replace("\\", "_")


def race_meta_relative_path(race_id: str) -> str:
    return f"race_meta/{_safe_race_id(race_id)}.json"


def entries_core_relative_path(race_id: str) -> str:
    return f"entries_core/{_safe_race_id(race_id)}.json"


def odds_relative_path(race_id: str) -> str:
    return f"odds/{_safe_race_id(race_id)}.json"


def track_relative_path(race_id: str) -> str:
    return f"track/{_safe_race_id(race_id)}.json"


def _write_artifact(rel: str, body: bytes) -> dict[str, Any]:
    root = raw_root()
    dest = root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    return {
        "raw_path": rel.replace("\\", "/"),
        "absolute_path": str(dest),
        "content_hash": hashlib.sha256(body).hexdigest(),
        "size_bytes": len(body),
    }


def write_race_meta(race_id: str, body: bytes) -> dict[str, Any]:
    """Layout: evidence/supply/raw/race_meta/{race_id}.json"""
    return _write_artifact(race_meta_relative_path(race_id), body)


def write_entries_core(race_id: str, body: bytes) -> dict[str, Any]:
    """Layout: evidence/supply/raw/entries_core/{race_id}.json"""
    return _write_artifact(entries_core_relative_path(race_id), body)


def write_odds(race_id: str, body: bytes) -> dict[str, Any]:
    """Layout: evidence/supply/raw/odds/{race_id}.json"""
    return _write_artifact(odds_relative_path(race_id), body)


def write_track(race_id: str, body: bytes) -> dict[str, Any]:
    """Layout: evidence/supply/raw/track/{race_id}.json"""
    return _write_artifact(track_relative_path(race_id), body)


def read_race_meta(race_id: str) -> bytes:
    return (raw_root() / race_meta_relative_path(race_id)).read_bytes()


def read_entries_core(race_id: str) -> bytes:
    return (raw_root() / entries_core_relative_path(race_id)).read_bytes()


def read_odds(race_id: str) -> bytes:
    return (raw_root() / odds_relative_path(race_id)).read_bytes()


def read_track(race_id: str) -> bytes:
    return (raw_root() / track_relative_path(race_id)).read_bytes()
