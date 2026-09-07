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
    surface: str | None = None
    distance: int | None = None
    going: str | None = None


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
                dist = raw.get("distance") or raw.get("target_distance")
                try:
                    dist_i = int(float(dist)) if dist not in (None, "") else None
                except ValueError:
                    dist_i = None
                going = (
                    raw.get("going")
                    or raw.get("track_condition")
                    or raw.get("condition")
                    or raw.get("baba")
                    or None
                )
                out.append(
                    RaceResultRow(
                        race_id=rid,
                        race_date=rd,
                        venue=(raw.get("venue") or None),
                        winner_horse_number=win_i,
                        field_size=fs_i,
                        winner_name=(raw.get("winner_name") or raw.get("horse_name") or None),
                        source=f"csv:{path.name}",
                        surface=(raw.get("surface") or raw.get("target_surface") or None),
                        distance=dist_i,
                        going=(str(going).strip() if going not in (None, "") else None),
                        extra={k: v for k, v in raw.items() if k not in {
                            "race_id", "race_date", "result_date", "venue",
                            "winner_horse_number", "winner_number", "field_size",
                            "winner_name", "horse_name", "surface", "target_surface",
                            "distance", "target_distance", "going", "track_condition",
                            "condition", "baba",
                        }},
                    )
                )
        return out


class NetkeibaResultProvider(ResultProvider):
    """
    Production official results via netkeiba result HTML.
    Race identity (Win5 race_id) comes from PI catalog.
    Only returns races that already have a published result table.
    """

    def __init__(self, http: Any | None = None):
        from .netkeiba_results import NetkeibaHttp

        self.http = http or NetkeibaHttp()

    def fetch(self, race_date: str) -> list[RaceResultRow]:
        from .netkeiba_results import (
            NetkeibaResultError,
            fetch_pi_race_catalog,
            parse_result_html,
        )

        catalog = fetch_pi_race_catalog(race_date)
        if not catalog:
            raise NetkeibaResultError(f"PI catalog empty for {race_date}")

        rows: list[RaceResultRow] = []
        errors: list[str] = []
        for race in catalog:
            race_id = str(race.get("race_id") or "").strip()
            numeric = str(race.get("numeric_race_id") or "").strip()
            if not race_id or not numeric:
                continue
            try:
                html = self.http.fetch_result_html(numeric)
                parsed = parse_result_html(html)
            except Exception as exc:
                errors.append(f"{race_id}:{exc}")
                continue
            if not parsed:
                # not finalized yet
                continue
            finish_order = parsed["finish_order"]
            rows.append(
                RaceResultRow(
                    race_id=race_id,
                    race_date=str(race.get("race_date") or race_date),
                    venue=(race.get("venue") or race.get("course") or None),
                    winner_horse_number=int(parsed["winner_horse_number"]),
                    field_size=int(parsed.get("field_size") or len(finish_order)),
                    winner_name=parsed.get("winner_name"),
                    source=f"netkeiba:{numeric}",
                    extra={
                        "finish_order": finish_order,
                        "payouts": parsed.get("payouts") or {},
                        "numeric_race_id": numeric,
                        "chakujun": finish_order,
                        "haraimodoshi": parsed.get("payouts") or {},
                    },
                    surface=None,
                    distance=None,
                    going=None,
                )
            )

        if not rows:
            if errors and not catalog:
                raise NetkeibaResultError(
                    f"no finalized netkeiba results for {race_date}: "
                    + "; ".join(errors[:5])
                )
            # Catalog OK but races not finalized yet — incremental poll returns empty.
            return []
        return rows


class CompositeResultProvider(ResultProvider):
    """Try providers in order; first non-empty success wins."""

    def __init__(self, providers: list[ResultProvider]):
        self.providers = providers

    def fetch(self, race_date: str) -> list[RaceResultRow]:
        errors: list[str] = []
        empty_ok = False
        for p in self.providers:
            try:
                rows = p.fetch(race_date)
                if rows:
                    return rows
                empty_ok = True
                errors.append(f"{type(p).__name__}: empty")
            except Exception as exc:
                errors.append(f"{type(p).__name__}: {exc}")
        if empty_ok:
            return []
        raise RuntimeError(
            "all result providers failed for "
            f"{race_date}: "
            + " | ".join(errors)
        )


def default_provider() -> ResultProvider:
    import os

    mode = (os.environ.get("EXPECT_RESULTS_PROVIDER") or "auto").strip().lower()
    raw = (os.environ.get("EXPECT_RESULTS_CSV") or "").strip()
    data_dir = (os.environ.get("EXPECT_RESULTS_DATA_DIR") or "").strip()
    paths = [Path(raw)] if raw else []
    dd = Path(data_dir) if data_dir else None
    if dd is None and mode in ("csv", "auto"):
        root = Path(__file__).resolve().parents[2]
        guess = root / "tests" / "ops" / "fixtures"
        # only use fixtures when explicitly csv mode
        if mode == "csv" and guess.is_dir():
            dd = guess
    csv_provider = CsvResultProvider(paths=paths, data_dir=dd)

    if mode == "csv":
        return csv_provider
    if mode == "netkeiba":
        return NetkeibaResultProvider()
    # auto: production netkeiba first, optional CSV override if configured
    providers: list[ResultProvider] = [NetkeibaResultProvider()]
    if raw or data_dir:
        providers.append(csv_provider)
    return CompositeResultProvider(providers)
