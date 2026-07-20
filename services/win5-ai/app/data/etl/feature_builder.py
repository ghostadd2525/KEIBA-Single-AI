# -*- coding: utf-8 -*-
"""Feature Builder — 正規化行から DB 投入用レコードを組み立て。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .normalizer import NormalizedFeatureRow, NormalizedRaceRow


@dataclass
class BuiltRaceRecord:
    race_id: str
    core_race_id: str
    public_race_id: str
    row: dict[str, Any]


@dataclass
class BuiltFeatureBundle:
    feature_rows: list[dict[str, Any]]
    entry_rows: list[dict[str, Any]]
    horse_rows: list[dict[str, Any]]


class FeatureBuilder:
    """Race / Feature 正規化結果 → Repository 向け dict。"""

    def build_race(self, norm: NormalizedRaceRow) -> BuiltRaceRecord:
        ident = norm.identity
        catalog_id = ident.catalog_race_id or f"{ident.date}-{ident.venue_ja}-{ident.race_no}"
        core_id = ident.core_race_id or catalog_id
        public_id = ident.public_race_id or catalog_id

        row = {
            "race_id": catalog_id,
            "core_race_id": core_id,
            "public_race_id": public_id,
            "venue_code": ident.venue_code,
            "date": ident.date,
            "venue": ident.venue_ja,
            "race_no": ident.race_no,
            "meeting_id": f"{ident.date.replace('-', '')}_{ident.venue_ja}",
            "surface": norm.surface,
            "distance": norm.distance,
            "class_label": norm.class_label,
            "field_size": norm.field_size,
            "post_time": norm.post_time,
            "status": norm.status or "scheduled",
            "source": norm.source,
            "extra": norm.extra or {},
        }
        return BuiltRaceRecord(
            race_id=catalog_id,
            core_race_id=core_id,
            public_race_id=public_id,
            row=row,
        )

    def build_features(
        self,
        norms: list[NormalizedFeatureRow],
        *,
        source_file: str | None = None,
    ) -> BuiltFeatureBundle:
        feature_rows: list[dict[str, Any]] = []
        entry_rows: list[dict[str, Any]] = []
        horse_rows: list[dict[str, Any]] = []
        seen_horses: set[str] = set()

        for norm in norms:
            ident = norm.identity
            core_id = ident.core_race_id
            if not core_id:
                continue

            feature_rows.append(
                {
                    "race_id": core_id,
                    "horse_number": norm.horse_number,
                    "horse_id": norm.horse_id,
                    "payload": norm.payload,
                    "feature_set": norm.feature_set,
                    "source_file": source_file,
                }
            )

            if norm.horse_number is None:
                continue

            entry_rows.append(
                {
                    "race_id": core_id,
                    "horse_id": norm.horse_id,
                    "horse_number": norm.horse_number,
                    "horse_name": norm.horse_name,
                    "jockey": norm.payload.get("jockey"),
                    "odds": norm.payload.get("odds") or norm.payload.get("odds_refetched"),
                    "popularity": norm.payload.get("popularity")
                    or norm.payload.get("popularity_refetched"),
                }
            )

            if norm.horse_id and norm.horse_id not in seen_horses:
                seen_horses.add(norm.horse_id)
                horse_rows.append(
                    {
                        "horse_id": norm.horse_id,
                        "horse_name": norm.horse_name or "",
                    }
                )

        return BuiltFeatureBundle(
            feature_rows=feature_rows,
            entry_rows=entry_rows,
            horse_rows=horse_rows,
        )
