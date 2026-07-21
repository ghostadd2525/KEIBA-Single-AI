# -*- coding: utf-8 -*-
"""odds artifact contract — C-6 DYNAMIC (minimal)."""
from __future__ import annotations

ARTIFACT_TYPE = "odds"
KIND = "DYNAMIC"

REQUIRED_FIELDS: tuple[str, ...] = (
    "race_id",
    "date",
    "venue",
    "race_no",
    "odds",
)

ARRAY_FIELDS: tuple[str, ...] = ("odds",)
