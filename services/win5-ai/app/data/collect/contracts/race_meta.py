# -*- coding: utf-8 -*-
"""race_meta artifact contract — C-1 STATIC_CORE."""
from __future__ import annotations

from typing import Any

ARTIFACT_TYPE = "race_meta"
KIND = "STATIC_CORE"

# race-level required fields for race_meta (C-1 scope)
REQUIRED_FIELDS: tuple[str, ...] = (
    "race_id",
    "date",
    "venue",
    "race_no",
    "distance",
)

# Array fields checked for empty [] when present
ARRAY_FIELDS: tuple[str, ...] = ("entries",)
