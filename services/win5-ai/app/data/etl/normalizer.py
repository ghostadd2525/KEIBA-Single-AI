# -*- coding: utf-8 -*-
"""CSV row normalizer — 列名ゆれを吸収し Race Resolver 入力へ正規化。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..race_resolver import RaceIdentity, RaceResolver


def _as_int(v: Any) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


@dataclass
class NormalizedRaceRow:
    identity: RaceIdentity
    surface: str | None = None
    distance: int | None = None
    class_label: str | None = None
    field_size: int | None = None
    post_time: str | None = None
    status: str | None = None
    source: str | None = None
    extra: dict[str, Any] | None = None


@dataclass
class NormalizedFeatureRow:
    identity: RaceIdentity
    horse_number: int | None
    horse_id: str | None
    horse_name: str | None
    payload: dict[str, Any]
    feature_set: str = "runners_pace_market"


class CsvNormalizer:
    def __init__(self, resolver: RaceResolver | None = None) -> None:
        self.resolver = resolver or RaceResolver()

    def normalize_race_row(
        self,
        row: dict[str, Any],
        *,
        source: str | None = None,
    ) -> NormalizedRaceRow | None:
        race_id = (row.get("race_id") or "").strip()
        date = (row.get("date") or "").strip()[:10]
        venue = (row.get("course") or row.get("venue") or "").strip()
        race_no = _as_int(row.get("race_number") or row.get("race_no"))

        probe = race_id
        if not probe and date and venue and race_no:
            probe = f"{date}-{venue}-{race_no}"

        if not probe:
            return None

        identity = self.resolver.resolve(
            probe,
            race_meta={"date": date, "venue": venue, "race_no": race_no},
        )
        if not identity:
            return None

        extra = {
            k: v
            for k, v in row.items()
            if k
            not in {
                "race_id",
                "date",
                "course",
                "venue",
                "race_number",
                "race_no",
            }
        }
        return NormalizedRaceRow(
            identity=identity,
            surface=row.get("target_surface") or row.get("surface"),
            distance=_as_int(row.get("target_distance") or row.get("distance")),
            class_label=row.get("race_name") or row.get("class_label"),
            field_size=_as_int(row.get("horse_count") or row.get("field_size")),
            post_time=row.get("post_time"),
            status=row.get("status"),
            source=source,
            extra=extra,
        )

    def normalize_feature_row(
        self,
        row: dict[str, Any],
        *,
        feature_set: str = "runners_pace_market",
    ) -> NormalizedFeatureRow | None:
        race_id = (row.get("race_id") or "").strip()
        if not race_id:
            return None

        identity = self.resolver.resolve(race_id)
        if not identity or not identity.core_race_id:
            return None

        hn = _as_int(row.get("horse_number"))
        payload = dict(row)
        payload["race_id"] = identity.core_race_id

        return NormalizedFeatureRow(
            identity=identity,
            horse_number=hn,
            horse_id=(row.get("horse_id") or None),
            horse_name=(row.get("horse_name") or None),
            payload=payload,
            feature_set=feature_set,
        )
