# -*- coding: utf-8 -*-
"""Diagnose 2026-07-25 race list parsing."""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pi_keibanet.netkeiba.client import NetkeibaClient, RACE_LIST_URL
from pi_keibanet.netkeiba.parse import find_numeric_race_id
from pi_keibanet.venues import COURSE_CODE_TO_NAME, COURSE_NAME_TO_CODE

DATE = "2026-07-25"
OUT = ROOT / "var" / "debug"
OUT.mkdir(parents=True, exist_ok=True)

client = NetkeibaClient(min_interval_sec=0)
url = RACE_LIST_URL.format(date=DATE.replace("-", ""))
print("URL:", url)
html = client.fetch_race_list(DATE)
path = OUT / f"race_list_sub_{DATE.replace('-', '')}.html"
path.write_text(html, encoding="utf-8")
print("saved:", path, "len=", len(html))

ids = list(dict.fromkeys(re.findall(r"race_id=(\d{12})", html)))
print("unique race_ids:", len(ids))

by_venue: dict[str, list[str]] = defaultdict(list)
for rid in ids:
    code = rid[4:6]
    venue = COURSE_CODE_TO_NAME.get(code, code)
    by_venue[venue].append(rid)

for venue in sorted(by_venue):
    rids = sorted(by_venue[venue], key=lambda x: int(x[-2:]))
    print(f"  {venue} ({COURSE_NAME_TO_CODE.get(venue,'?')}): {len(rids)} races ->", rids[:3], "...", rids[-1:] if rids else [])

targets = ["札幌", "新潟", "中京"]
print("\nfind_numeric_race_id for R1:")
for venue in targets:
    rid = find_numeric_race_id(html, venue=venue, race_no=1)
    print(f"  {venue}: {rid}")

# check if venue names appear in HTML
for venue in targets:
    print(f"  '{venue}' in html:", venue in html)

# sample links with context
for m in re.finditer(r"race_id=(\d{12})[^>]*>([^<]{0,30})", html):
    if m.group(1)[4:6] in ("01", "04", "07"):
        print("link:", m.group(1), "->", m.group(2)[:40])
