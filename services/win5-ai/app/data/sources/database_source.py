# -*- coding: utf-8 -*-
"""DatabaseSource — 既存 DB から races/features を再供給。"""
from __future__ import annotations

import json

from ..repository import FeatureRepository, RaceRepository
from .base import DownloadResult


class DatabaseSource:
    source_type = "database"

    def available(self) -> bool:
        try:
            RaceRepository().list(limit=1)
            return True
        except Exception:
            return False

    def download(self, race_date: str) -> DownloadResult:
        result = DownloadResult(race_date=race_date, source_type=self.source_type)
        races = RaceRepository().list(date=race_date, limit=500)
        result.race_rows = [
            {
                "race_id": r.get("core_race_id") or r.get("race_id"),
                "date": r.get("date"),
                "venue": r.get("venue"),
                "race_no": r.get("race_no"),
                "surface": r.get("surface"),
                "distance": r.get("distance"),
                "race_name": r.get("class_label"),
                "horse_count": r.get("field_size"),
            }
            for r in races
        ]

        feat_repo = FeatureRepository()
        for race in races:
            core_id = race.get("core_race_id") or race.get("race_id")
            if not core_id:
                continue
            for feat in feat_repo.list_for_race(str(core_id)):
                payload = feat.get("payload") or {}
                if isinstance(payload, str):
                    payload = json.loads(payload)
                result.feature_rows.append(payload)

        result.notes.append(
            f"loaded {len(result.race_rows)} races, {len(result.feature_rows)} features from DB"
        )
        return result
