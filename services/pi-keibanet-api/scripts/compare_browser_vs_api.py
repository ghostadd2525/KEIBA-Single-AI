# -*- coding: utf-8 -*-
"""Compare browser URLs vs PI API fetched HTML."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pi_keibanet.netkeiba.client import NetkeibaClient
from pi_keibanet.netkeiba.parse import (
    _RACE_ID_RE,
    parse_entries_from_shutuba,
    parse_meetings_from_race_list,
    shutuba_has_race,
)

OUT = ROOT / "var" / "debug" / "compare"
OUT.mkdir(parents=True, exist_ok=True)

client = NetkeibaClient(min_interval_sec=1)

# ---- 1. Browser race_list URL (the one user actually sees) ----
urls = {
    "race_list_main": "https://race.netkeiba.com/top/race_list.html?kaisai_date=20260725",
    "race_list_sub": "https://race.netkeiba.com/top/race_list_sub.html?kaisai_date=20260725",
    "race_list_sp": "https://race.sp.netkeiba.com/?pid=race_list&kaisai_date=20260725",
}

for label, url in urls.items():
    html = client.fetch(url, label=label)
    path = OUT / f"{label}.html"
    path.write_text(html, encoding="utf-8")
    ids = sorted(set(_RACE_ID_RE.findall(html)))
    venues = {}
    for rid in ids:
        code = rid[4:6]
        venues.setdefault(code, []).append(rid)
    print(f"\n=== {label} ===")
    print(f"  URL: {url}")
    print(f"  bytes: {len(html.encode('utf-8'))}")
    print(f"  unique race_ids: {len(ids)}")
    for code, rids in sorted(venues.items()):
        from pi_keibanet.venues import COURSE_CODE_TO_NAME
        name = COURSE_CODE_TO_NAME.get(code, code)
        nums = sorted(int(r[-2:]) for r in rids)
        print(f"    {name}({code}): R{nums}")
    meetings = parse_meetings_from_race_list(html)
    if meetings:
        print(f"  meetings: {[(m.venue, m.kai, m.day) for m in meetings]}")

# ---- 2. Shutuba pages ----
shutuba_ids = [
    ("202604020101", "新潟1R"),
    ("202604020102", "新潟2R"),
    ("202604020106", "新潟6R (user confirmed)"),
    ("202607020106", "中京6R"),
    ("202601010110", "札幌10R"),
    ("202601010101", "札幌1R"),
]

print("\n\n=== SHUTUBA COMPARISON ===")
for rid, desc in shutuba_ids:
    url = f"https://race.netkeiba.com/race/shutuba.html?race_id={rid}"
    html = client.fetch(url, label=f"shutuba_{rid}")
    path = OUT / f"shutuba_{rid}.html"
    path.write_text(html, encoding="utf-8")

    has = shutuba_has_race(html)
    entries = parse_entries_from_shutuba(html)
    title_m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    title = title_m.group(1).strip() if title_m else "?"
    race_name_m = re.search(r'RaceName[^>]*>([\s\S]*?)</', html, re.I)
    race_name = re.sub(r"<[^>]+>", "", race_name_m.group(1)).strip() if race_name_m else ""
    has_table = "Shutuba_Table" in html
    has_horselist = 'class="HorseList"' in html
    has_horse_link = "/horse/" in html or "db.netkeiba.com/horse/" in html

    print(f"\n--- {desc} ({rid}) ---")
    print(f"  URL: {url}")
    print(f"  bytes: {len(html.encode('utf-8'))}")
    print(f"  <title>: {title[:100]}")
    print(f"  race_name: {race_name[:60]}")
    print(f"  has Shutuba_Table: {has_table}")
    print(f"  has HorseList rows: {has_horselist}")
    print(f"  has /horse/ links: {has_horse_link}")
    print(f"  shutuba_has_race(): {has}")
    print(f"  parsed entries: {len(entries)}")
    if entries:
        print(f"  first: {entries[0]}")

# ---- 3. Specific horse DB page ----
horse_url = "https://db.netkeiba.com/horse/2023100681"
print(f"\n\n=== HORSE DB PAGE ===")
print(f"  URL: {horse_url}")
html = client.fetch(horse_url, label="horse_2023100681")
path = OUT / "horse_2023100681.html"
path.write_text(html, encoding="utf-8")
print(f"  bytes: {len(html.encode('utf-8'))}")
title_m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
print(f"  <title>: {title_m.group(1).strip()[:120] if title_m else '?'}")

# ---- 4. Check if race_list.html loads data via AJAX ----
print("\n\n=== AJAX API CHECK ===")
ajax_urls = [
    "https://race.netkeiba.com/api/api_get_jra_digest2.html?input=UTF-8&output=json&rf=race_list",
    "https://race.netkeiba.com/top/race_list_sub.html?kaisai_date=20260725",
]
for url in ajax_urls:
    html = client.fetch(url, label="ajax_check")
    ids = _RACE_ID_RE.findall(html)
    print(f"  {url.split('?')[0].split('/')[-1]}: {len(html)} bytes, {len(set(ids))} race_ids")
