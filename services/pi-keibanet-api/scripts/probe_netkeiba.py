# -*- coding: utf-8 -*-
"""One-off probe for netkeiba race_list HTML."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pi_keibanet.netkeiba.client import NetkeibaClient
from pi_keibanet.netkeiba.parse import find_numeric_race_id

c = NetkeibaClient(min_interval_sec=0)
html = c.fetch_race_list("2026-07-19")
print("race_id count", len(re.findall(r"race_id", html, re.I)))
print("shutuba count", html.count("shutuba"))
links = re.findall(r'href="([^"]*race[^"]*)"', html, re.I)[:20]
for link in links:
    print(link)
idx = html.find("RaceList")
print("--- snippet ---")
print(html[idx : idx + 2500] if idx >= 0 else html[:2500])

for venue in ["新潟", "函館", "福島", "小倉", "中京"]:
    rid = find_numeric_race_id(html, venue=venue, race_no=1)
    print(venue, rid)
