# -*- coding: utf-8 -*-
"""Verify race_list_sub.html works with parser."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import urllib.parse
import urllib.request

from pi_keibanet.netkeiba.parse import find_numeric_race_id

date = "20260719"
url = "https://race.netkeiba.com/top/race_list_sub.html?" + urllib.parse.urlencode(
    {"kaisai_date": date}
)
req = urllib.request.Request(
    url,
    headers={
        "User-Agent": "Mozilla/5.0 (compatible; Expect-PI-KeibaNet/1.0)",
        "Referer": "https://race.netkeiba.com/top/race_list.html",
    },
)
with urllib.request.urlopen(req, timeout=25) as resp:
    html = resp.read().decode("utf-8", errors="replace")

print("len", len(html), "race_id=", html.count("race_id="))
for venue in ["福島", "函館", "小倉", "新潟", "中京"]:
    for r in range(1, 13):
        rid = find_numeric_race_id(html, venue=venue, race_no=r)
        if rid:
            print(venue, f"R{r}", rid)
