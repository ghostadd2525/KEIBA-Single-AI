# -*- coding: utf-8 -*-
"""PAGE-D2 horse pedigree RAW parser (identity/relation only; no scores)."""
from __future__ import annotations

import re
from typing import Any

from .d1_parse import decode_html_bytes  # noqa: F401 — re-export helper

PARSER_VERSION = "w4b_d2_pedigree_v1"
SOURCE_NAME = "netkeiba_page_d2"
D2_URL = "https://db.netkeiba.com/horse/ped/{horse_id}/"

_STRIP = re.compile(r"<[^>]+>")
_CELL = re.compile(
    r'<td[^>]*class="([^"]*)"[^>]*(?:rowspan="(\d+)")?[^>]*>'
    r"|<td[^>]*(?:rowspan=\"(\d+)\")?[^>]*class=\"([^\"]*)\"[^>]*>",
    re.I,
)


def _text(html: str) -> str:
    t = _STRIP.sub(" ", html)
    return re.sub(r"\s+", " ", t).strip()


def _extract_blood_table(html: str) -> str | None:
    m = re.search(
        r'<table[^>]*class="[^"]*blood_table[^"]*"[^>]*>([\s\S]*?)</table>',
        html,
        re.I,
    )
    return m.group(0) if m else None


def _first_horse_in_td(td_html: str) -> tuple[str | None, str | None]:
    """Return (horse_id, horse_name) from first /horse/{id}/ link that is not ped/sire/mare subpath-only."""
    # Prefer profile links /horse/ID/ not /horse/ped/ID/
    m = re.search(
        r'href="[^"]*/horse/(?!ped/|sire/|mare/)([A-Za-z0-9]+)/?"[^>]*>\s*([\s\S]*?)</a>',
        td_html,
        re.I,
    )
    if not m:
        m = re.search(
            r'href="[^"]*/horse/([A-Za-z0-9]+)/?"[^>]*>\s*([\s\S]*?)</a>',
            td_html,
            re.I,
        )
    if not m:
        return None, None
    hid = m.group(1)
    name = _text(m.group(2))
    # drop English line / year fragments: take first token line
    if name:
        name = name.split("  ")[0].strip()
        # remove trailing year-like if whole name is messy
        name = re.split(r"\s+\d{4}\b", name)[0].strip()
    return hid, name or None


def _iter_tds(table_html: str) -> list[dict[str, Any]]:
    tds: list[dict[str, Any]] = []
    for m in re.finditer(r"<td([^>]*)>([\s\S]*?)</td>", table_html, re.I):
        attrs, body = m.group(1), m.group(2)
        cls_m = re.search(r'class="([^"]*)"', attrs, re.I)
        rs_m = re.search(r'rowspan="(\d+)"', attrs, re.I)
        cls = cls_m.group(1) if cls_m else ""
        rowspan = int(rs_m.group(1)) if rs_m else 1
        hid, name = _first_horse_in_td(body)
        tds.append(
            {
                "class": cls,
                "rowspan": rowspan,
                "horse_id": hid,
                "horse_name": name,
            }
        )
    return tds


def parse_d2_pedigree(html: str, *, expected_horse_id: str | None = None) -> dict[str, Any]:
    """Parse pedigree blood_table: sire / dam / broodmare_sire only (depth fixed)."""
    out: dict[str, Any] = {
        "horse_id": expected_horse_id,
        "sire_id": None,
        "sire_name": None,
        "dam_id": None,
        "dam_name": None,
        "broodmare_sire_id": None,
        "broodmare_sire_name": None,
        "parse_ok": False,
        "parser_version": PARSER_VERSION,
        "source": SOURCE_NAME,
        "reasons": [],
        "pedigree_depth_contract": 3,
    }

    # subject id from canonical link if present
    if not out["horse_id"]:
        m = re.search(r'rel="canonical"[^>]*href="[^"]*/horse/([A-Za-z0-9]+)/?"', html, re.I)
        if m:
            out["horse_id"] = m.group(1)

    table = _extract_blood_table(html)
    if not table:
        out["reasons"].append("no_blood_table")
        return out

    tds = _iter_tds(table)
    sire = next((t for t in tds if "b_ml" in t["class"] and t["rowspan"] >= 16 and t["horse_id"]), None)
    dam = next((t for t in tds if "b_fml" in t["class"] and t["rowspan"] >= 16 and t["horse_id"]), None)
    if sire:
        out["sire_id"] = sire["horse_id"]
        out["sire_name"] = sire["horse_name"]
    else:
        out["reasons"].append("sire_missing")
    if dam:
        out["dam_id"] = dam["horse_id"]
        out["dam_name"] = dam["horse_name"]
    else:
        out["reasons"].append("dam_missing")

    # broodmare sire: first rowspan>=8 b_ml after dam cell
    bms = None
    if dam is not None:
        seen_dam = False
        for t in tds:
            if t is dam:
                seen_dam = True
                continue
            if not seen_dam:
                continue
            if "b_ml" in t["class"] and t["rowspan"] >= 8 and t["horse_id"]:
                bms = t
                break
    if bms:
        out["broodmare_sire_id"] = bms["horse_id"]
        out["broodmare_sire_name"] = bms["horse_name"]
    else:
        out["reasons"].append("broodmare_sire_missing")

    if out["sire_id"] and out["dam_id"]:
        out["parse_ok"] = True
    return out
