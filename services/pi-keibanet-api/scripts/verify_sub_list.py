# -*- coding: utf-8 -*-
"""Verify race_list_sub.html works with parser."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import urllib.parse

from pi_keibanet.http_budget.probes import ProbeRefused, budgeted_probe_client, exit_refused
from pi_keibanet.netkeiba.parse import find_numeric_race_id

date = "20260719"
url = "https://race.netkeiba.com/top/race_list_sub.html?" + urllib.parse.urlencode(
    {"kaisai_date": date}
)
try:
    client = budgeted_probe_client()
except ProbeRefused as exc:
    exit_refused(exc)
html = client.fetch(url, label="verify_sub_list")

print("len", len(html), "race_id=", html.count("race_id="))
for venue in ["福島", "函館", "小倉", "新潟", "中京"]:
    for r in range(1, 13):
        rid = find_numeric_race_id(html, venue=venue, race_no=r)
        if rid:
            print(venue, f"R{r}", rid)
