# -*- coding: utf-8 -*-
"""Probe netkeiba JSON APIs for race list."""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

UA = "Mozilla/5.0 (compatible; Expect-PI-KeibaNet/1.0)"


def get(url: str, params: dict | None = None) -> tuple[int, str]:
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "*/*",
            "Referer": "https://race.netkeiba.com/top/race_list.html",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read()
    for enc in ("utf-8", "euc-jp", "cp932"):
        try:
            return resp.status, raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return resp.status, raw.decode("utf-8", errors="replace")


candidates = [
    (
        "https://race.netkeiba.com/api/api_get_jra_digest2.html",
        {"input": "UTF-8", "output": "json", "rf": "race_list"},
    ),
    (
        "https://race.netkeiba.com/api/api_get_race_list.html",
        {"input": "UTF-8", "output": "json", "kaisai_date": "20260719"},
    ),
    (
        "https://race.netkeiba.com/api/api_get_race_list.html",
        {"input": "UTF-8", "output": "json", "kaisai_date": "20260719", "rf": "race_list"},
    ),
    (
        "https://race.netkeiba.com/top/race_list_sub.html",
        {"kaisai_date": "20260719"},
    ),
    (
        "https://race.sp.netkeiba.com/",
        {"pid": "race_list", "kaisai_date": "20260719"},
    ),
]

for url, params in candidates:
    print("===", url, params, "===")
    try:
        status, body = get(url, params)
        print("status", status, "len", len(body))
        print(body[:1200])
        if "race_id" in body:
            import re

            ids = re.findall(r"\d{12}", body)
            print("12-digit ids sample:", ids[:10])
    except Exception as exc:
        print("ERR", exc)
    print()
