# -*- coding: utf-8 -*-
"""FeatureLoader — DB / daily CSV / global CSV の統一入口（Prediction Core 正式入力）。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import pandas as pd

DbProvider = Callable[[str], "FeatureLoadResult | None"]

_db_provider: DbProvider | None = None
_last_failure_reason: str | None = None


def register_db_provider(provider: DbProvider | None) -> None:
    """Register SQLite / FeatureRepository loader (wired by win5-ai service)."""
    global _db_provider
    _db_provider = provider


def get_last_failure_reason() -> str | None:
    return _last_failure_reason


def _set_failure(reason: str) -> None:
    global _last_failure_reason
    _last_failure_reason = reason


@dataclass
class FeatureLoadResult:
    frame: pd.DataFrame
    feature_source: str
    metadata: dict[str, Any] = field(default_factory=dict)


class FeatureLoader:
    """Core 唯一の特徴量入力。CorePipeline は CSV/DB を直接参照しない。"""

    SOURCE_DB = "db"
    SOURCE_DAILY_CSV = "daily_csv"
    SOURCE_GLOBAL_CSV = "global_csv"

    def __init__(self, *, data_root: Path | None = None) -> None:
        self._data_root = data_root or _resolve_data_root()

    def load(self, core_race_id: str) -> FeatureLoadResult | None:
        rid = str(core_race_id or "").strip()
        if not rid:
            _set_failure("race_not_found")
            return None

        if _db_provider is not None:
            try:
                loaded = _db_provider(rid)
                if loaded is not None and not loaded.frame.empty:
                    _set_failure("")
                    return loaded
            except Exception:
                pass

        daily = self._load_daily_csv(rid)
        if daily is not None:
            _set_failure("")
            return daily

        global_csv = self._load_global_csv(rid)
        if global_csv is not None:
            _set_failure("")
            return global_csv

        if self._data_root is None or not self._data_root.is_dir():
            _set_failure("platform_missing")
        elif not self._any_csv_exists():
            _set_failure("feature_csv_missing")
        else:
            _set_failure("market_feature_missing")
        return None

    def classify_unavailable(self, core_race_id: str) -> str | None:
        """None if loadable; otherwise fallback_reason code."""
        if self.load(core_race_id) is not None:
            return None
        return get_last_failure_reason() or "market_feature_missing"

    def _load_daily_csv(self, core_race_id: str) -> FeatureLoadResult | None:
        if not self._data_root:
            return None
        date = core_race_id[:10]
        daily_dir = self._data_root / "demo_daily_outputs" / date
        candidates = (
            daily_dir / "demo_runners_pace_market_features.csv",
            daily_dir / "Demo_runners_pace_market_features.csv",
        )
        for path in candidates:
            loaded = self._read_csv_race(path, core_race_id)
            if loaded is not None:
                loaded.feature_source = self.SOURCE_DAILY_CSV
                loaded.metadata["path"] = str(path)
                return loaded
        return None

    def _load_global_csv(self, core_race_id: str) -> FeatureLoadResult | None:
        if not self._data_root:
            return None
        candidates = (
            self._data_root / "runners_pace_market_features.csv",
            self._data_root / "Runners_pace_market_features.csv",
            self._data_root / "demo_runners_pace_market_features.csv",
            self._data_root / "Demo_runners_pace_market_features.csv",
        )
        for path in candidates:
            loaded = self._read_csv_race(path, core_race_id)
            if loaded is not None:
                loaded.feature_source = self.SOURCE_GLOBAL_CSV
                loaded.metadata["path"] = str(path)
                return loaded
        return None

    def _read_csv_race(self, path: Path, core_race_id: str) -> FeatureLoadResult | None:
        if not path.exists():
            return None
        frame = _read_csv(path)
        if "race_id" not in frame.columns:
            return None
        race = frame[frame["race_id"].astype(str) == str(core_race_id)].copy()
        if race.empty:
            return None
        return FeatureLoadResult(
            frame=race,
            feature_source="",
            metadata={"path": str(path), "row_count": len(race)},
        )

    def _any_csv_exists(self) -> bool:
        if not self._data_root:
            return False
        date = ""
        patterns = [
            self._data_root / "runners_pace_market_features.csv",
            self._data_root / "demo_runners_pace_market_features.csv",
        ]
        return any(p.exists() for p in patterns)

    @staticmethod
    def _read_csv(path: Path) -> pd.DataFrame:
        return _read_csv(path)


def _read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, low_memory=False)


def _resolve_data_root() -> Path | None:
    env_root = (os.environ.get("AI_PLATFORM_ROOT") or "").strip()
    if env_root:
        data = Path(env_root) / "data"
        if data.is_dir():
            return data
    here = Path(__file__).resolve()
    for idx in (3, 4, 5):
        if idx < len(here.parents):
            data = here.parents[idx] / "data"
            if data.is_dir():
                return data
    return None


__all__ = [
    "FeatureLoadResult",
    "FeatureLoader",
    "register_db_provider",
    "get_last_failure_reason",
]
