# -*- coding: utf-8 -*-
"""
Version7.4 History data sources (STATIC first).

正本の差し替え点:
  CsvHistoryStore  → race_refresh horse_history_raw.csv（現行）
  DbHistoryStore   → Collector STATIC_HISTORY → ETL → Store（将来）
  Live fallback    → service.horse_history() 経由（本モジュール外）

PE / CE / AI ロジックは参照しない。
"""
from __future__ import annotations

import csv
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


def is_weekend_jst(day: str | None = None) -> bool:
    """土日は DYNAMIC のみ（近走は STATIC 保持）。"""
    if day:
        try:
            d = datetime.strptime(day[:10], "%Y-%m-%d").date()
        except ValueError:
            d = datetime.now(JST).date()
    else:
        d = datetime.now(JST).date()
    return d.weekday() >= 5  # Sat=5 Sun=6


def _refresh_paths(date: str) -> tuple[Path, Path]:
    """Lazy resolve race_refresh day paths (avoid import cycles)."""
    from .race_refresh import RefreshConfig, _history_path, _runners_path

    cfg = RefreshConfig.from_env()
    return _history_path(cfg, date), _runners_path(cfg, date)


class HistoryStore(ABC):
    """Near-run history rows in horse_history_raw shape."""

    name: str = "base"

    @abstractmethod
    def load_race_rows(self, race_id: str, *, date: str) -> list[dict[str, Any]] | None:
        """
        Returns:
          list  — rows for race (may be empty = 新馬/過去走0 確定)
          None  — this store has no answer (try next)
        """


class CsvHistoryStore(HistoryStore):
    """race_refresh/{date}/horse_history_raw.csv"""

    name = "csv"

    def day_csv_exists(self, date: str) -> bool:
        hist, _ = _refresh_paths(date)
        return hist.is_file()

    def race_known_in_day(self, race_id: str, date: str) -> bool:
        """refresh が当該 race を扱ったか（history または runners）。"""
        rid = str(race_id).strip()
        hist, runners = _refresh_paths(date)
        for path in (hist, runners):
            if not path.is_file():
                continue
            with path.open("r", encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    if str(row.get("race_id") or "").strip() == rid:
                        return True
        return False

    def load_race_rows(self, race_id: str, *, date: str) -> list[dict[str, Any]] | None:
        hist, _ = _refresh_paths(date)
        if not hist.is_file():
            return None
        rid = str(race_id).strip()
        rows: list[dict[str, Any]] = []
        found = False
        with hist.open("r", encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                if str(row.get("race_id") or "").strip() != rid:
                    continue
                found = True
                rows.append(dict(row))
        if found:
            return rows
        # CSV はあるが当該 race の history 行が無い
        if self.race_known_in_day(rid, date):
            return []  # runners にはある → 新馬等で過去走0確定
        return None  # refresh 未実行


class DbHistoryStore(HistoryStore):
    """
    将来: Collector STATIC_HISTORY → ETL → Store。
    現状は未配線（常に None → 次ソースへ）。
    PI_HISTORY_DB_PATH を将来接続点とする。
    """

    name = "db"

    def load_race_rows(self, race_id: str, *, date: str) -> list[dict[str, Any]] | None:
        raw = (os.environ.get("PI_HISTORY_DB_PATH") or "").strip()
        if not raw:
            return None
        return None


class CompositeHistoryStore:
    """CSV → DB。Live は service 側で明示 fallback。"""

    def __init__(
        self,
        *,
        csv_store: CsvHistoryStore | None = None,
        db_store: DbHistoryStore | None = None,
    ) -> None:
        self.csv = csv_store or CsvHistoryStore()
        self.db = db_store or DbHistoryStore()

    def resolve_static(
        self, race_id: str, *, date: str
    ) -> tuple[list[dict[str, Any]] | None, str]:
        """
        Returns (rows_or_None, source_name).
        None = STATIC では答えられない → live 候補。
        """
        force = str(os.environ.get("PI_HISTORY_FORCE_LIVE", "")).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if force:
            return None, "force_live"

        for store in (self.csv, self.db):
            rows = store.load_race_rows(race_id, date=date)
            if rows is not None:
                return rows, store.name
        return None, "miss"


_default_store: CompositeHistoryStore | None = None


def default_history_store() -> CompositeHistoryStore:
    global _default_store
    if _default_store is None:
        _default_store = CompositeHistoryStore()
    return _default_store
