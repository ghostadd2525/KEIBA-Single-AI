# -*- coding: utf-8 -*-
"""Result providers — abstract result fetch (Production)."""
from __future__ import annotations

import csv
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass
class RaceResultRow:
    race_id: str
    race_date: str
    venue: str | None
    winner_horse_number: int | None
    field_size: int | None
    winner_name: str | None
    source: str
    extra: dict[str, Any]


class ResultProvider(ABC):
    @abstractmethod
    def fetch(self, race_date: str) -> list[RaceResultRow]:
        """Fetch official results for a race date. Raises on hard failure."""


class CsvResultProvider(ResultProvider):
    """
    CSV columns (flexible):
      race_id, race_date, venue, winner_horse_number, field_size, winner_name
    """

    def __init__(self, paths: Iterable[Path] | None = None, data_dir: Path | None = None):
        self.paths = [Path(p) for p in (paths or [])]
        self.data_dir = Path(data_dir) if data_dir else None

    def _resolve_files(self, race_date: str) -> list[Path]:
        files: list[Path] = list(self.paths)
        if self.data_dir and self.data_dir.is_dir():
            # date-specific then generic
            candidates = [
                self.data_dir / f"results_{race_date}.csv",
                self.data_dir / race_date / "results.csv",
                self.data_dir / "results.csv",
                self.data_dir / "sample_results.csv",
            ]
            for c in candidates:
                if c.is_file() and c not in files:
                    files.append(c)
        return [f for f in files if f.is_file()]

    def fetch(self, race_date: str) -> list[RaceResultRow]:
        files = self._resolve_files(race_date)
        if not files:
            raise FileNotFoundError(
                f"no results CSV for {race_date} (data_dir={self.data_dir})"
            )
        rows: list[RaceResultRow] = []
        for path in files:
            rows.extend(self._read_csv(path, race_date))
        # de-dupe by race_id (last wins)
        by_id: dict[str, RaceResultRow] = {}
        for r in rows:
            if r.race_date == race_date:
                by_id[r.race_id] = r
        if not by_id:
            raise ValueError(f"CSV has no rows for race_date={race_date}")
        return list(by_id.values())

    def _read_csv(self, path: Path, race_date: str) -> list[RaceResultRow]:
        out: list[RaceResultRow] = []
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for raw in reader:
                rid = (raw.get("race_id") or "").strip()
                rd = (raw.get("race_date") or raw.get("result_date") or "").strip()
                if not rid:
                    continue
                if rd and rd != race_date:
                    continue
                if not rd:
                    rd = race_date
                win_n = raw.get("winner_horse_number") or raw.get("winner_number")
                try:
                    win_i = int(win_n) if win_n not in (None, "") else None
                except ValueError:
                    win_i = None
                fs = raw.get("field_size")
                try:
                    fs_i = int(fs) if fs not in (None, "") else None
                except ValueError:
                    fs_i = None
                out.append(
                    RaceResultRow(
                        race_id=rid,
                        race_date=rd,
                        venue=(raw.get("venue") or None),
                        winner_horse_number=win_i,
                        field_size=fs_i,
                        winner_name=(raw.get("winner_name") or raw.get("horse_name") or None),
                        source=f"csv:{path.name}",
                        extra={k: v for k, v in raw.items() if k not in {
                            "race_id", "race_date", "result_date", "venue",
                            "winner_horse_number", "winner_number", "field_size",
                            "winner_name", "horse_name",
                        }},
                    )
                )
        return out


def default_provider() -> ResultProvider:
    import os

    raw = (os.environ.get("EXPECT_RESULTS_CSV") or "").strip()
    data_dir = (os.environ.get("EXPECT_RESULTS_DATA_DIR") or "").strip()
    paths = [Path(raw)] if raw else []
    dd = Path(data_dir) if data_dir else None
    if dd is None:
        # repo fixtures fallback for local/dev
        root = Path(__file__).resolve().parents[2]
        guess = root / "tests" / "ops" / "fixtures"
        if guess.is_dir():
            dd = guess
    return CsvResultProvider(paths=paths, data_dir=dd)
