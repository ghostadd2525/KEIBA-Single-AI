# -*- coding: utf-8 -*-
"""Catalog / Core / FeatureLookup identity metadata for race_refresh (no scoring)."""
from __future__ import annotations

from .venues import COURSE_CODE_TO_NAME, COURSE_NAME_TO_CODE


def catalog_identity_metadata(
    *,
    date: str,
    catalog_race_id: str,
    numeric_race_id: str,
    course: str,
    race_number: int,
) -> dict[str, str]:
    """
    Identity metadata only. race_id / Feature 計算は変えない。

    Production Feature CSV の lookup key は Catalog/Win5 ID のまま。
    Core ID は JRA venue（numeric 桁または course 名）であり lookup には使わない。
    """
    numeric = "".join(ch for ch in str(numeric_race_id or "") if ch.isdigit())
    jra = ""
    if len(numeric) == 12 and numeric[4:6] in COURSE_CODE_TO_NAME:
        jra = numeric[4:6]
    elif str(course or "").strip() in COURSE_NAME_TO_CODE:
        jra = COURSE_NAME_TO_CODE[str(course).strip()]
    core_id = ""
    if jra:
        core_id = f"{date}-{jra}-{int(race_number):02d}"
    return {
        "catalog_race_id": catalog_race_id,
        "feature_lookup_key": catalog_race_id,
        "core_race_id": core_id,
        "jra_venue_code": jra,
    }
