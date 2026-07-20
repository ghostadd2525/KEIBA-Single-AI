# -*- coding: utf-8 -*-
"""
ETL Pipeline

CSV → Normalizer → Race Resolver → Feature Builder → Repository → DB
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..db import migrate
from ..race_resolver import RaceResolver
from ..repository import EntryRepository, FeatureRepository, HorseRepository, RaceRepository
from ...engine import data as engine_data
from .feature_builder import FeatureBuilder
from .normalizer import CsvNormalizer


@dataclass
class EtlResult:
    races: int = 0
    features: int = 0
    entries: int = 0
    horses: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "races": self.races,
            "features": self.features,
            "entries": self.entries,
            "horses": self.horses,
            "skipped": self.skipped,
            "errors": self.errors,
        }


class EtlPipeline:
    def __init__(self) -> None:
        migrate()
        self.resolver = RaceResolver()
        self.normalizer = CsvNormalizer(self.resolver)
        self.builder = FeatureBuilder()
        self.races = RaceRepository()
        self.features = FeatureRepository()
        self.entries = EntryRepository()
        self.horses = HorseRepository()

    def import_races_csv(self, path: Path, *, source: str | None = None) -> EtlResult:
        result = EtlResult()
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                norm = self.normalizer.normalize_race_row(row, source=source or path.name)
                if not norm:
                    result.skipped += 1
                    continue
                built = self.builder.build_race(norm)
                self.races.upsert(built.row)
                result.races += 1
        engine_data.clear_caches()
        return result

    def import_features_csv(
        self,
        path: Path,
        *,
        feature_set: str = "runners_pace_market",
    ) -> EtlResult:
        result = EtlResult()
        norms = []
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                norm = self.normalizer.normalize_feature_row(row, feature_set=feature_set)
                if not norm:
                    result.skipped += 1
                    continue
                norms.append(norm)

        bundle = self.builder.build_features(norms, source_file=str(path))
        for row in bundle.feature_rows:
            self.features.upsert_row(
                race_id=row["race_id"],
                horse_number=row.get("horse_number"),
                horse_id=row.get("horse_id"),
                payload=row["payload"],
                feature_set=row["feature_set"],
                source_file=row.get("source_file"),
            )
            result.features += 1

        for row in bundle.entry_rows:
            self.entries.upsert(row)
            result.entries += 1

        for row in bundle.horse_rows:
            self.horses.upsert(row)
            result.horses += 1

        engine_data.clear_caches()
        return result

    def import_day(self, data_dir: Path, *, race_date: str | None = None) -> EtlResult:
        """開催日ディレクトリまたは data ルートから races/features CSV を一括投入。"""
        total = EtlResult()
        patterns = [
            "races.csv",
            "demo_races.csv",
            "Demo_races*.csv",
            "runners_pace_market_features.csv",
            "demo_runners_pace_market_features.csv",
            "Runners_pace_market_features.csv",
        ]

        race_files: list[Path] = []
        feature_files: list[Path] = []
        for pat in patterns:
            for p in sorted(data_dir.glob(pat)):
                name = p.name.lower()
                if "runner" in name or "feature" in name:
                    feature_files.append(p)
                else:
                    race_files.append(p)

        if race_date:
            sub = data_dir / race_date
            if sub.is_dir():
                for p in sorted(sub.glob("*.csv")):
                    name = p.name.lower()
                    if "runner" in name or "feature" in name:
                        feature_files.append(p)
                    else:
                        race_files.append(p)

        for path in race_files:
            r = self.import_races_csv(path)
            total.races += r.races
            total.skipped += r.skipped
            total.errors.extend(r.errors)

        for path in feature_files:
            r = self.import_features_csv(path)
            total.features += r.features
            total.entries += r.entries
            total.horses += r.horses
            total.skipped += r.skipped
            total.errors.extend(r.errors)

        return total


def run_etl(kind: str, path: Path, **kwargs: Any) -> EtlResult:
    pipe = EtlPipeline()
    if kind == "races":
        return pipe.import_races_csv(path, source=kwargs.get("source"))
    if kind == "features":
        return pipe.import_features_csv(
            path, feature_set=kwargs.get("feature_set", "runners_pace_market")
        )
    raise ValueError(f"unknown etl kind: {kind}")


def import_day(data_dir: Path, *, race_date: str | None = None) -> EtlResult:
    return EtlPipeline().import_day(data_dir, race_date=race_date)
