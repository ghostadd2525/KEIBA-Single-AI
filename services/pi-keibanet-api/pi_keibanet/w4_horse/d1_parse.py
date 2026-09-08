# -*- coding: utf-8 -*-
"""PAGE-D1 horse profile RAW parser (Research only; no Feature)."""
from __future__ import annotations

import re
from typing import Any

PARSER_VERSION = "w4b_d1_profile_v1"
SOURCE_NAME = "netkeiba_page_d1"
D1_URL = "https://db.netkeiba.com/horse/{horse_id}/"

_STRIP = re.compile(r"<[^>]+>")
_HORSE_HREF = re.compile(r"/horse/([A-Za-z0-9]+)/?", re.I)
_TRAINER_HREF = re.compile(r"/trainer/(?:result/recent/)?([A-Za-z0-9]+)/?", re.I)


def decode_html_bytes(raw: bytes) -> str:
    """Decode HTML preferring meta charset (db.netkeiba is often euc-jp)."""
    head = raw[:4096].decode("ascii", errors="ignore").lower()
    preferred: list[str] = []
    if "charset=euc-jp" in head or "charset=euc_jp" in head:
        preferred.append("euc-jp")
    elif "charset=utf-8" in head or "charset=utf8" in head:
        preferred.append("utf-8")
    elif "charset=shift_jis" in head or "charset=sjis" in head:
        preferred.append("cp932")
    for enc in preferred + ["utf-8", "euc-jp", "cp932"]:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _text(html: str) -> str:
    t = _STRIP.sub(" ", html)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", t).strip()


def _th_cell(html: str, label: str) -> str | None:
    m = re.search(
        rf"<th[^>]*>\s*{re.escape(label)}\s*</th>\s*<td[^>]*>([\s\S]*?)</td>",
        html,
    )
    if not m:
        return None
    return _text(m.group(1)) or None


def parse_d1_profile(html: str, *, expected_horse_id: str | None = None) -> dict[str, Any]:
    """Parse horse profile page into RAW fields. Absent → None (no inference)."""
    out: dict[str, Any] = {
        "horse_id": None,
        "horse_name": None,
        "sex": None,
        "birth_date": None,
        "birth_year": None,
        "coat_color": None,
        "profile_current_trainer_id": None,
        "profile_current_trainer_name": None,
        "profile_current_affiliation": None,
        "owner": None,
        "breeder": None,
        "birthplace": None,
        "parse_ok": False,
        "parser_version": PARSER_VERSION,
        "source": SOURCE_NAME,
        "reasons": [],
    }

    ids = _HORSE_HREF.findall(html)
    if expected_horse_id and expected_horse_id in ids:
        out["horse_id"] = expected_horse_id
    elif expected_horse_id:
        out["horse_id"] = expected_horse_id
        if ids and expected_horse_id not in ids:
            out["reasons"].append("expected_id_not_in_page_links")
    elif ids:
        out["horse_id"] = ids[0]

    # horse_title block
    title = re.search(r'class="horse_title"[\s\S]{0,800}', html)
    title_txt = _text(title.group(0)) if title else ""
    # Name often in <h1> or horse_title strong/a
    name = re.search(r'class="horse_title"[\s\S]*?<h1[^>]*>\s*([^<]+)', html)
    if not name:
        name = re.search(r"<title>\s*([^|<]+)", html)
    if name:
        out["horse_name"] = name.group(1).strip()

    # Sex: 牡/牝/セ in title area
    sex_m = re.search(r"([牡牝セ騸])\s*[0-9０-９]{1,2}", title_txt) or re.search(
        r"([牡牝セ騸])\s*[0-9０-９]{1,2}", html[:8000]
    )
    if sex_m:
        out["sex"] = sex_m.group(1)

    # Coat in title: 鹿毛/黒鹿毛/栗毛/青鹿毛/青毛/白毛/芦毛
    coat_m = re.search(
        r"(黒鹿毛|青鹿毛|鹿毛|栗毛|青毛|白毛|芦毛|栃栗毛)",
        title_txt,
    ) or re.search(r"(黒鹿毛|青鹿毛|鹿毛|栗毛|青毛|白毛|芦毛|栃栗毛)", html[:12000])
    if coat_m:
        out["coat_color"] = coat_m.group(1)
    # th 毛色 if present
    coat_th = _th_cell(html, "毛色")
    if coat_th:
        out["coat_color"] = coat_th

    birth = _th_cell(html, "生年月日")
    if birth:
        out["birth_date"] = birth
        ym = re.search(r"(19|20)\d{2}", birth)
        if ym:
            out["birth_year"] = int(ym.group(0))

    trainer_cell = _th_cell(html, "調教師")
    if trainer_cell:
        # "小栗実 (栗東)" 
        m_aff = re.match(r"^(.+?)\s*[（(]([^)）]+)[)）]\s*$", trainer_cell)
        if m_aff:
            out["profile_current_trainer_name"] = m_aff.group(1).strip()
            out["profile_current_affiliation"] = m_aff.group(2).strip()
        else:
            out["profile_current_trainer_name"] = trainer_cell
    # trainer id from trainer cell region
    trainer_block = re.search(
        r"<th[^>]*>\s*調教師\s*</th>\s*<td[^>]*>([\s\S]*?)</td>",
        html,
    )
    if trainer_block:
        tm = _TRAINER_HREF.search(trainer_block.group(1))
        if tm:
            out["profile_current_trainer_id"] = tm.group(1)

    out["owner"] = _th_cell(html, "馬主")
    out["breeder"] = _th_cell(html, "生産者")
    out["birthplace"] = _th_cell(html, "産地")

    if out["horse_id"] and (out["horse_name"] or out["birth_date"] or out["profile_current_trainer_name"]):
        out["parse_ok"] = True
    else:
        out["reasons"].append("insufficient_profile_fields")
    return out
