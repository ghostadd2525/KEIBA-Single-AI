# -*- coding: utf-8 -*-
"""End-to-end PI service smoke test against live netkeiba."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIN5 = ROOT.parent / "win5-ai"
for p in (ROOT, WIN5):
    if p.is_dir() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

from pi_keibanet.service import PiKeibaNetService

svc = PiKeibaNetService()
date, venue, race_no = "2026-07-19", "福島", 1
for name in ("race_meta", "entries_core", "odds", "track"):
    payload = getattr(svc, name)(date=date, venue=venue, race_no=race_no)
    print("===", name, "===")
    print(json.dumps(payload, ensure_ascii=False, indent=2)[:1500])

from app.data.collect import validate_entries_core, validate_race_meta

meta = svc.race_meta(date=date, venue=venue, race_no=race_no)
entries = svc.entries_core(date=date, venue=venue, race_no=race_no)
rm = validate_race_meta(http_ok=True, body=json.dumps(meta, ensure_ascii=False).encode())
ec = validate_entries_core(http_ok=True, body=json.dumps(entries, ensure_ascii=False).encode())
print("validator race_meta", rm.ok, rm.errors)
print("validator entries_core", ec.ok, ec.errors)
