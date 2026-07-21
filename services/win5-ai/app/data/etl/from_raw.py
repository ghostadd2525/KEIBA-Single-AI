# -*- coding: utf-8 -*-
"""
EtlFromRaw — Raw Store → existing ETL → SQLite.

C-3: race_meta → races
C-4: entries_core → entries (+ horses)
Collector は ETL を知らない。本モジュールが Bridge 役。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..collect.raw_store import raw_root
from ..db import connect, migrate
from ..repository import EntryRepository, HorseRepository, RaceRepository
from ...engine import data as engine_data
from .feature_builder import FeatureBuilder
from .normalizer import CsvNormalizer


@dataclass
class EtlFromRawResult:
    races: int = 0
    entries: int = 0
    horses: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "races": self.races,
            "entries": self.entries,
            "horses": self.horses,
            "skipped": self.skipped,
            "errors": self.errors,
        }

    def merge(self, other: "EtlFromRawResult") -> "EtlFromRawResult":
        self.races += other.races
        self.entries += other.entries
        self.horses += other.horses
        self.skipped += other.skipped
        self.errors.extend(other.errors)
        return self


def race_meta_payload_to_row(payload: dict[str, Any]) -> dict[str, Any]:
    """Map Collector race_meta JSON to CsvNormalizer-compatible row."""
    return {
        "race_id": payload.get("race_id"),
        "date": payload.get("date"),
        "venue": payload.get("venue"),
        "race_no": payload.get("race_no"),
        "distance": payload.get("distance"),
        "surface": payload.get("surface"),
        "race_name": payload.get("race_name") or payload.get("class_label"),
        "horse_count": payload.get("field_size") or payload.get("horse_count"),
        "post_time": payload.get("post_time"),
        "status": payload.get("status"),
    }


class EtlFromRaw:
    """
    Raw Store → Normalizer → Resolver → FeatureBuilder → Repository.

    race_meta → races
    entries_core → entries / horses（FeatureLoader / features は変更しない）
    """

    def __init__(self) -> None:
        migrate()
        self.normalizer = CsvNormalizer()
        self.builder = FeatureBuilder()
        self.races = RaceRepository()
        self.entries = EntryRepository()
        self.horses = HorseRepository()

    def ingest_race_meta_bytes(
        self,
        body: bytes,
        *,
        source: str = "collect_raw/race_meta",
    ) -> EtlFromRawResult:
        result = EtlFromRawResult()
        try:
            payload = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            result.errors.append(f"invalid_json: {exc}")
            result.skipped += 1
            return result

        if not isinstance(payload, dict):
            result.errors.append("invalid_shape: root must be object")
            result.skipped += 1
            return result

        row = race_meta_payload_to_row(payload)
        norm = self.normalizer.normalize_race_row(row, source=source)
        if not norm:
            result.errors.append("normalize_failed: race_meta could not be resolved")
            result.skipped += 1
            return result

        built = self.builder.build_race(norm)
        self.races.upsert(built.row)
        result.races += 1
        engine_data.clear_caches()
        return result

    def ingest_entries_core_bytes(
        self,
        body: bytes,
        *,
        source: str = "collect_raw/entries_core",
    ) -> EtlFromRawResult:
        """
        entries_core → entries / horses.

        features テーブルは触らない（FeatureLoader / Prediction を壊さない）。
        """
        result = EtlFromRawResult()
        try:
            payload = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            result.errors.append(f"invalid_json: {exc}")
            result.skipped += 1
            return result

        if not isinstance(payload, dict):
            result.errors.append("invalid_shape: root must be object")
            result.skipped += 1
            return result

        race_row = {
            "race_id": payload.get("race_id"),
            "date": payload.get("date"),
            "venue": payload.get("venue"),
            "race_no": payload.get("race_no"),
        }
        norm_race = self.normalizer.normalize_race_row(race_row, source=source)
        if not norm_race:
            result.errors.append("normalize_failed: entries_core race could not be resolved")
            result.skipped += 1
            return result

        built_race = self.builder.build_race(norm_race)
        catalog_id = built_race.race_id

        entries = payload.get("entries") or []
        if not isinstance(entries, list):
            result.errors.append("invalid_shape: entries must be array")
            result.skipped += 1
            return result

        seen_horses: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                result.skipped += 1
                continue
            horse_number = entry.get("horse_number")
            horse_name = entry.get("horse_name")
            horse_id = entry.get("horse_id") or (
                f"h{int(horse_number):03d}" if horse_number is not None else None
            )
            self.entries.upsert(
                {
                    "race_id": catalog_id,
                    "horse_id": horse_id,
                    "horse_number": horse_number,
                    "horse_name": horse_name,
                    "frame_number": entry.get("frame") or entry.get("frame_number"),
                    "jockey": entry.get("jockey"),
                    "extra": {"weight": entry.get("weight"), "source": source},
                }
            )
            result.entries += 1

            if horse_id and horse_id not in seen_horses:
                seen_horses.add(horse_id)
                self.horses.upsert(
                    {
                        "horse_id": horse_id,
                        "horse_name": horse_name or "",
                    }
                )
                result.horses += 1

        engine_data.clear_caches()
        return result

    def ingest_path(self, raw_path: str, *, artifact_type: str) -> EtlFromRawResult:
        path = raw_root() / raw_path.replace("\\", "/")
        if not path.is_file():
            res = EtlFromRawResult()
            res.errors.append(f"raw_file_missing: {path}")
            res.skipped += 1
            return res
        body = path.read_bytes()
        source = f"collect_raw/{raw_path}"
        if artifact_type == "race_meta":
            return self.ingest_race_meta_bytes(body, source=source)
        if artifact_type == "entries_core":
            return self.ingest_entries_core_bytes(body, source=source)
        res = EtlFromRawResult()
        res.errors.append(f"unsupported_artifact_type: {artifact_type}")
        res.skipped += 1
        return res

    def ingest_race_meta_path(self, raw_path: str, *, source: str | None = None) -> EtlFromRawResult:
        return self.ingest_path(raw_path, artifact_type="race_meta")

    def ingest_ready(
        self,
        *,
        week_id: str,
        artifact_type: str | None = None,
    ) -> EtlFromRawResult:
        migrate()
        types = [artifact_type] if artifact_type else ["race_meta", "entries_core"]
        total = EtlFromRawResult()
        for atype in types:
            conn = connect()
            try:
                rows = conn.execute(
                    """
                    SELECT a.raw_path, a.artifact_type
                    FROM collect_artifacts a
                    INNER JOIN collect_jobs j ON j.job_id = a.job_id
                    WHERE j.week_id = ?
                      AND j.status = 'READY'
                      AND a.status = 'READY'
                      AND a.artifact_type = ?
                      AND a.raw_path IS NOT NULL
                    ORDER BY j.priority, j.scheduled_for, j.job_id
                    """,
                    (week_id, atype),
                ).fetchall()
            finally:
                conn.close()

            for row in rows:
                part = self.ingest_path(str(row["raw_path"]), artifact_type=str(row["artifact_type"]))
                total.merge(part)
        engine_data.clear_caches()
        return total

    def ingest_ready_race_meta(self, *, week_id: str) -> EtlFromRawResult:
        return self.ingest_ready(week_id=week_id, artifact_type="race_meta")

    def ingest_ready_entries_core(self, *, week_id: str) -> EtlFromRawResult:
        return self.ingest_ready(week_id=week_id, artifact_type="entries_core")


def ingest_ready_race_meta(week_id: str) -> EtlFromRawResult:
    return EtlFromRaw().ingest_ready_race_meta(week_id=week_id)


def ingest_ready_entries_core(week_id: str) -> EtlFromRawResult:
    return EtlFromRaw().ingest_ready_entries_core(week_id=week_id)
