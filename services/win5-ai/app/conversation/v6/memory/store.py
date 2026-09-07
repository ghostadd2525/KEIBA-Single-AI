# -*- coding: utf-8 -*-
"""
Memory Store — ユーザー単位の長期永続（JSON ファイル）。

Conversation History（プロセス FIFO）とは別ストレージ。
Prediction / Knowledge / Security データは一切保持しない。
"""
from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any

from .models import MemoryRecord, _utc_now


def _default_root() -> Path:
    override = (os.environ.get("CONVERSATION_MEMORY_DIR") or "").strip()
    if override:
        return Path(override)
    # services/win5-ai/var/memory
    here = Path(__file__).resolve()
    return here.parents[4] / "var" / "memory"


def _safe_user_id(user_id: str) -> str:
    raw = str(user_id or "").strip() or "anonymous"
    return re.sub(r"[^a-zA-Z0-9._@-]+", "_", raw)[:128]


class MemoryStore:
    """Long-term Memory persistence（consent 済みレコードのみ）。"""

    version = "v6-phase2"
    kind = "long_term_file"

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else _default_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, user_id: str) -> Path:
        return self.root / f"{_safe_user_id(user_id)}.json"

    def _load(self, user_id: str) -> list[MemoryRecord]:
        path = self._path(user_id)
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        items = raw.get("memories") if isinstance(raw, dict) else raw
        if not isinstance(items, list):
            return []
        out: list[MemoryRecord] = []
        for item in items:
            if isinstance(item, dict) and item.get("consent") is True:
                out.append(MemoryRecord.from_dict(item))
        return out

    def _save(self, user_id: str, records: list[MemoryRecord]) -> None:
        path = self._path(user_id)
        payload = {
            "user_id": str(user_id),
            "kind": self.kind,
            "updated_at": _utc_now(),
            "memories": [r.to_dict() for r in records if r.consent],
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(path)

    def list(self, user_id: str) -> list[MemoryRecord]:
        with self._lock:
            return list(self._load(user_id))

    def upsert(self, record: MemoryRecord) -> MemoryRecord:
        """consent=True のレコードのみ受理。同一 category+key は上書き。"""
        if not record.consent:
            raise ValueError("memory_store_requires_consent")
        with self._lock:
            records = self._load(record.user_id)
            replaced = False
            for i, existing in enumerate(records):
                if existing.category == record.category and existing.key == record.key:
                    record.memory_id = existing.memory_id
                    record.created_at = existing.created_at
                    record.updated_at = _utc_now()
                    records[i] = record
                    replaced = True
                    break
            if not replaced:
                records.append(record)
            self._save(record.user_id, records)
            return record

    def delete_matching(self, user_id: str, query: str) -> list[MemoryRecord]:
        q = str(query or "").strip().lower()
        with self._lock:
            records = self._load(user_id)
            kept: list[MemoryRecord] = []
            removed: list[MemoryRecord] = []
            for r in records:
                blob = f"{r.category} {r.key} {r.value} {r.source_text}".lower()
                if q and q in blob:
                    removed.append(r)
                else:
                    kept.append(r)
            if removed:
                self._save(user_id, kept)
            return removed

    def clear(self, user_id: str) -> int:
        with self._lock:
            records = self._load(user_id)
            n = len(records)
            path = self._path(user_id)
            if path.exists():
                path.unlink()
            return n

    def meta(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "kind": self.kind,
            "root": str(self.root),
            "persistent": True,
            "history_separated": True,
        }


_STORE: MemoryStore | None = None
_STORE_LOCK = threading.Lock()


def get_memory_store() -> MemoryStore:
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = MemoryStore()
        return _STORE


def reset_memory_store_for_tests(root: Path | None = None) -> MemoryStore:
    global _STORE
    with _STORE_LOCK:
        _STORE = MemoryStore(root=root)
        return _STORE
