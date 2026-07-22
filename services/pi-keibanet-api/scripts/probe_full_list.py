# -*- coding: utf-8 -*-
"""Probe full race list sources and constructed race_id."""
from __future__ import annotations

import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pi_keibanet.netkeiba.client import NetkeibaClient, SHUTUBA_URL

DATE = "20260725"
UA = "Mozilla/5.0 (compatible; Expect-PI-KeibaNet/1.0)"

def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://race.netkeiba.com/"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", errors="replace")

# Try alternate list URLs
urls = [
    f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={DATE}",
    f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={DATE}&current=1",
    f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={DATE}&tab=0",
    f"https://race.sp.netkeiba.com/?pid=race_list&kaisai_date={DATE}",
]
for u in urls:
    try:
        html = get(u)
        ids = set(re.findall(r"race_id=(\d{12})", html))
        print(u.split("?")[1] if "?" in u else "sp", "len", len(html), "ids", len(ids))
    except Exception as e:
        print(u, "ERR", e)

# Test constructed race_ids from header pattern
candidates = [
    ("新潟", "04", "02", "01", 1, "202604020101"),
    ("中京", "07", "02", "01", 1, "202607020101"),
    ("札幌", "01", "01", "01", 1, "202601010101"),
]
client = NetkeibaClient(min_interval_sec=0)
for venue, code, kai, day, rno, expected in candidates:
    url = SHUTUBA_URL.format(race_id=expected)
    try:
        html = client.fetch(url)
        has_horse = "/horse/" in html
        m = re.search(r"Race_Num[\s\S]{0,80}?(\d+)R", html)
        shown = m.group(1) if m else "?"
        print(f"{venue} R{rno} {expected}: len={len(html)} horse={has_horse} shown_r={shown}")
    except Exception as e:
        print(f"{venue} R{rno} {expected}: FAIL {e}")
