# -*- coding: utf-8 -*-
"""track artifact contract — C-6 DYNAMIC (minimal)."""
from __future__ import annotations

ARTIFACT_TYPE = "track"
KIND = "DYNAMIC"

REQUIRED_FIELDS: tuple[str, ...] = (
    "race_id",
    "date",
    "venue",
    "race_no",
    "condition",
)

ARRAY_FIELDS: tuple[str, ...] = ()
