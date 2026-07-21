# -*- coding: utf-8 -*-
"""entries_core artifact contract — C-4 STATIC_CORE."""
from __future__ import annotations

ARTIFACT_TYPE = "entries_core"
KIND = "STATIC_CORE"

# Top-level required
REQUIRED_FIELDS: tuple[str, ...] = (
    "race_id",
    "date",
    "venue",
    "race_no",
    "entries",
)

ARRAY_FIELDS: tuple[str, ...] = ("entries",)

# Per-entry required (馬番・枠番・馬名・騎手・斤量)
ENTRY_REQUIRED_FIELDS: tuple[str, ...] = (
    "horse_number",
    "frame",
    "horse_name",
    "jockey",
    "weight",
)
