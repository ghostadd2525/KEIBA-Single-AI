# -*- coding: utf-8 -*-
"""
ETL Scheduler

開催日指定 → Download → Normalize → Resolver → Feature Builder → Repository → DB → Validation
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...engine import data as engine_data
from ..coverage import compute_coverage
from ..repository.supply import SupplyRepository
from ..sources import DownloadResult, get_source, resolve_sources
from ..validation import validate_all_races
from .feature_builder import FeatureBuilder
from .normalizer import CsvNormalizer
from .pipeline import EtlPipeline, EtlResult
from ..race_resolver import RaceResolver
from ..repository import EntryRepository, FeatureRepository, HorseRepository, RaceRepository


STEPS = (
    "download",
    "normalize",
    "resolver",
    "feature_builder",
    "repository",
    "db",
    "validation",
)


@dataclass
class SchedulerResult:
    run_id: int
    race_date: str
    status: str
    stopped_at_step: str | None = None
    error_reason: str | None = None
    missing_data: dict[str, Any] = field(default_factory=dict)
    etl: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    steps: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "race_date": self.race_date,
            "status": self.status,
            "stopped_at_step": self.stopped_at_step,
            "error_reason": self.error_reason,
            "missing_data": self.missing_data,
            "etl": self.etl,
            "validation": self.validation,
            "steps": self.steps,
        }


class EtlScheduler:
    def __init__(
        self,
        *,
        source_type: str | None = None,
        data_dir: Path | None = None,
    ) -> None:
        self.source_type = source_type
        self.data_dir = data_dir
        self.supply = SupplyRepository()
        self.pipeline = EtlPipeline()
        self.resolver = RaceResolver()
        self.normalizer = CsvNormalizer(self.resolver)
        self.builder = FeatureBuilder()
        self.races = RaceRepository()
        self.features = FeatureRepository()
        self.entries = EntryRepository()
        self.horses = HorseRepository()

    def run(self, race_date: str) -> SchedulerResult:
        source = get_source(self.source_type, data_dir=self.data_dir)
        run_id = self.supply.create_run(race_date, source.source_type)
        result = SchedulerResult(run_id=run_id, race_date=race_date, status="running")

        try:
            download = self._step_download(run_id, race_date, source)
            if not self._has_data(download):
                return self._fail(
                    result,
                    "download",
                    "no data available from source",
                    {
                        "race_date": race_date,
                        "source_type": source.source_type,
                        "notes": download.notes,
                    },
                )

            etl_result = self._step_etl(run_id, download)
            result.etl = etl_result.as_dict()

            validation = self._step_validation(run_id, race_date)
            result.validation = validation
            result.status = "success"
            result.steps = self.supply.steps_for_run(run_id)

            self.supply.finish_run(
                run_id,
                status="success",
                result={"etl": result.etl, "validation": validation},
            )
            self.supply.add_import_history(
                run_id=run_id,
                race_date=race_date,
                source_type=source.source_type,
                races_count=etl_result.races,
                features_count=etl_result.features,
                entries_count=etl_result.entries,
                horses_count=etl_result.horses,
                skipped_count=etl_result.skipped,
                detail={"errors": etl_result.errors},
            )
            engine_data.clear_caches()
            return result

        except Exception as exc:
            step = getattr(exc, "step", "unknown")
            return self._fail(result, step, str(exc), {"exception": str(exc)})

    def _step_download(self, run_id: int, race_date: str, source) -> DownloadResult:
        download = source.download(race_date)
        self.supply.add_step(
            run_id,
            "download",
            "success" if self._has_data(download) else "failed",
            {
                "source_type": source.source_type,
                "race_files": download.race_files,
                "feature_files": download.feature_files,
                "race_rows": len(download.race_rows),
                "feature_rows": len(download.feature_rows),
                "notes": download.notes,
            },
        )
        if not self._has_data(download):
            for fb in resolve_sources(self.source_type):
                if fb.source_type == source.source_type:
                    continue
                alt = fb.download(race_date)
                if self._has_data(alt):
                    self.supply.add_step(
                        run_id,
                        "download",
                        "success",
                        {"fallback_source": fb.source_type, "notes": alt.notes},
                    )
                    return alt
        return download

    def _step_etl(self, run_id: int, download: DownloadResult) -> EtlResult:
        total = EtlResult()

        # normalize + resolver + feature_builder + repository + db
        if download.race_files or download.feature_files:
            for path_str in download.race_files:
                r = self.pipeline.import_races_csv(Path(path_str))
                total.races += r.races
                total.skipped += r.skipped
            for path_str in download.feature_files:
                r = self.pipeline.import_features_csv(Path(path_str))
                total.features += r.features
                total.entries += r.entries
                total.horses += r.horses
                total.skipped += r.skipped
        else:
            total = self._ingest_rows(run_id, download)

        self.supply.add_step(run_id, "normalize", "success", {"mode": "rows_or_files"})
        self.supply.add_step(run_id, "resolver", "success", {})
        self.supply.add_step(run_id, "feature_builder", "success", {})
        self.supply.add_step(
            run_id,
            "repository",
            "success",
            {"races": total.races, "features": total.features},
        )
        self.supply.add_step(run_id, "db", "success", total.as_dict())
        return total

    def _ingest_rows(self, run_id: int, download: DownloadResult) -> EtlResult:
        result = EtlResult()
        for row in download.race_rows:
            norm = self.normalizer.normalize_race_row(row, source=download.source_type)
            if not norm:
                result.skipped += 1
                continue
            built = self.builder.build_race(norm)
            self.races.upsert(built.row)
            result.races += 1

        norms = []
        for row in download.feature_rows:
            norm = self.normalizer.normalize_feature_row(row)
            if not norm:
                result.skipped += 1
                continue
            norms.append(norm)

        bundle = self.builder.build_features(norms, source_file=download.source_type)
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

        return result

    def _step_validation(self, run_id: int, race_date: str) -> dict[str, Any]:
        validation = validate_all_races(run_id=run_id, race_date=race_date)
        self.supply.add_step(
            run_id,
            "validation",
            "success",
            {"coverage": validation.get("coverage"), "validation_id": validation.get("validation_id")},
        )
        return validation

    def _has_data(self, download: DownloadResult) -> bool:
        return bool(
            download.race_files
            or download.feature_files
            or download.race_rows
            or download.feature_rows
        )

    def _fail(
        self,
        result: SchedulerResult,
        step: str,
        reason: str,
        missing: dict[str, Any],
    ) -> SchedulerResult:
        result.status = "failed"
        result.stopped_at_step = step
        result.error_reason = reason
        result.missing_data = missing
        result.steps = self.supply.steps_for_run(result.run_id)
        self.supply.add_step(result.run_id, step, "failed", {"reason": reason, "missing": missing})
        self.supply.finish_run(
            result.run_id,
            status="failed",
            stopped_at_step=step,
            error_reason=reason,
            missing_data=missing,
        )
        return result


def run_scheduled_etl(race_date: str, **kwargs: Any) -> SchedulerResult:
    return EtlScheduler(**kwargs).run(race_date)
