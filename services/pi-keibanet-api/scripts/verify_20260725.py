# -*- coding: utf-8 -*-
"""Verify 2026-07-25 venues after parser fix."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pi_keibanet.service import PiKeibaNetService, RaceNotFoundError

DATE = "2026-07-25"
CASES = [
    ("札幌", 10),
    ("札幌", 1),
    ("新潟", 6),
    ("新潟", 1),
    ("中京", 6),
    ("中京", 1),
]

svc = PiKeibaNetService()
for venue, race_no in CASES:
    print(f"=== {venue} R{race_no} ===")
    try:
        meta = svc.race_meta(date=DATE, venue=venue, race_no=race_no)
        entries = svc.entries_core(date=DATE, venue=venue, race_no=race_no)
        print(
            "OK",
            meta.get("numeric_race_id"),
            meta.get("race_name"),
            f"entries={len(entries['entries'])}",
        )
    except RaceNotFoundError as exc:
        print("404", exc.reason, exc.message)
    except Exception as exc:
        print("ERR", type(exc).__name__, exc)
