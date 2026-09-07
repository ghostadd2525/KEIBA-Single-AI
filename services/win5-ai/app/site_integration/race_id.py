# -*- coding: utf-8 -*-
"""I1 Race ID routing / normalization for existing site IDs."""
from __future__ import annotations

import re
from typing import Any


# Site forms seen in production FE / PI:
#   20260719_hanshin_11
#   2026-07-19-hanshin-11
#   2026-07-19-01-11  (meeting-style)
_SLUG = re.compile(
    r"^(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})_(?P<venue>[a-z0-9]+)_(?P<no>\d+)$",
    re.I,
)
_HYPHEN = re.compile(
    r"^(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})-(?P<rest>.+)$",
    re.I,
)


class RaceIdError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def normalize_race_id(raw: Any) -> str:
    """Normalize race_id for routing. Does not invent Core identities."""
    if raw is None:
        raise RaceIdError("BAD_RACE_ID", "race_id required")
    rid = str(raw).strip()
    if not rid:
        raise RaceIdError("BAD_RACE_ID", "race_id required")
    if len(rid) > 128:
        raise RaceIdError("BAD_RACE_ID", "race_id too long")
    # Reject path injection
    if "/" in rid or "\\" in rid or ".." in rid:
        raise RaceIdError("BAD_RACE_ID", "race_id contains illegal characters")
    return rid


def parse_race_id_meta(race_id: str) -> dict[str, Any]:
    """Best-effort meta for routing/logging (non-authoritative vs Core)."""
    rid = normalize_race_id(race_id)
    m = _SLUG.match(rid)
    if m:
        date = f"{m.group('y')}-{m.group('m')}-{m.group('d')}"
        return {
            "race_id": rid,
            "form": "ymd_venue_no",
            "date": date,
            "venue": m.group("venue").lower(),
            "race_no": int(m.group("no")),
        }
    h = _HYPHEN.match(rid)
    if h:
        return {
            "race_id": rid,
            "form": "hyphen",
            "date": f"{h.group('y')}-{h.group('m')}-{h.group('d')}",
            "rest": h.group("rest"),
        }
    return {"race_id": rid, "form": "opaque"}
