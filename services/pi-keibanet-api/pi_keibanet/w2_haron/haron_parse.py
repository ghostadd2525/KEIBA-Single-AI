# -*- coding: utf-8 -*-
"""PAGE-C Race_HaronTime parser (Shadow RAW only; no Feature)."""
from __future__ import annotations

import re


def parse_haron(html: str) -> dict:
    """Parse Race_HaronTime table from result.html.

    Returns dict with haron_exists, parse_ok, sectional, cumulative, raw_excerpt, …
    """
    out: dict = {
        "haron_exists": False,
        "parse_ok": False,
        "lap_sequence_length": 0,
        "markers_m": [],
        "sectional": [],
        "cumulative": [],
        "malformed_reason": None,
        "raw_excerpt": None,
        "raw_haron_text": None,
    }
    if "Race_HaronTime" not in html and "HaronTime" not in html:
        out["malformed_reason"] = "no_Race_HaronTime_marker"
        return out
    out["haron_exists"] = True
    m = re.search(
        r'<table[^>]*class="[^"]*Race_HaronTime[^"]*"[^>]*>([\s\S]*?)</table>',
        html,
        re.I,
    )
    if not m:
        m = re.search(r"<table[^>]*Race_HaronTime[^>]*>([\s\S]*?)</table>", html, re.I)
    frag = m.group(1) if m else ""
    if not frag:
        m2 = re.search(r"HaronTime[\s\S]{0,1500}", html)
        frag = m2.group(0) if m2 else ""
        out["raw_excerpt"] = frag[:400]
        out["raw_haron_text"] = frag[:2000] if frag else None
    else:
        text_plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", frag))
        out["raw_excerpt"] = text_plain[:400]
        out["raw_haron_text"] = text_plain[:2000]
    text = re.sub(r"<[^>]+>", " ", frag)
    text = re.sub(r"\s+", " ", text)
    markers = [int(x) for x in re.findall(r"\b(\d{2,4})m\b", text)]
    times = re.findall(r"\b(\d{1,2}:\d{2}\.\d|\d{1,2}\.\d)\b", text)
    vals: list[float] = []
    for t in times:
        if ":" in t:
            mm, ss = t.split(":")
            vals.append(round(int(mm) * 60 + float(ss), 3))
        else:
            vals.append(float(t))
    out["markers_m"] = markers
    n = len(markers)
    if n >= 3 and len(vals) >= n:
        out["parse_ok"] = True
        out["lap_sequence_length"] = n
        out["cumulative"] = vals[:n]
        out["sectional"] = vals[n : 2 * n] if len(vals) >= 2 * n else []
    else:
        out["malformed_reason"] = f"markers={n} times={len(vals)}"
    return out
