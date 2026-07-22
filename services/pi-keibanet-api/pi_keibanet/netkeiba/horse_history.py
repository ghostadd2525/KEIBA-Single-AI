# -*- coding: utf-8 -*-
"""
Fetch and parse horse history from db.netkeiba.com.

Race results are loaded via AJAX (ajax_horse_results.html), not the initial page HTML.
Ported from demo_horse_history_fetcher.py (Win5AI legacy).
Uses stdlib urllib (no Selenium) — same as NetkeibaClient.
Output columns are identical to horse_history_raw.csv.
"""
from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Dict, List, Optional, Tuple

from .client import NetkeibaClient

HORSE_AJAX_RESULTS_URL = (
    "https://db.netkeiba.com/horse/ajax_horse_results.html"
    "?input=UTF-8&output=json&id={horse_id}"
)

OUT_COLUMNS = [
    "race_id", "numeric_race_id", "date", "course", "race_number", "race_name",
    "horse_number", "horse_name", "horse_url", "horse_id",
    "sex", "age", "weight_carried_today", "jockey_today",
    "odds_today", "popularity_today",
    "history_index",
    "history_date", "history_place", "history_race_name", "history_class",
    "history_frame_number", "history_horse_number",
    "history_distance_text", "history_surface", "history_distance",
    "history_course_condition",
    "history_finish", "history_popularity", "history_odds",
    "history_last3f", "history_margin", "history_weight",
    "history_passing", "history_time", "history_jockey",
    "history_horse_weight", "history_weather",
    "corner1", "corner2", "corner3", "corner4",
]

_TAG_RE = re.compile(r"<[^>]+>")


def _strip(text: str) -> str:
    return unescape(_TAG_RE.sub("", text or "")).strip()


def _normalize(text: Any) -> str:
    if text is None:
        return ""
    s = str(text).strip()
    s = s.replace("\n", "").replace("\r", "").replace("\u3000", "").replace(" ", "")
    s = s.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    s = s.replace("－", "-").replace("―", "-").replace("—", "-").replace("–", "-")
    return s


def _safe_float(text: str) -> Optional[float]:
    text = (text or "").replace(",", "").strip()
    if not text or text in {"---", "-", "**", "----", "--.-"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _split_course_distance(text: str) -> Tuple[str, Optional[int]]:
    s = _normalize(text)
    surface = ""
    if "芝" in s:
        surface = "芝"
    elif "ダ" in s:
        surface = "ダ"
    elif "障" in s:
        surface = "障"
    m = re.search(r"(\d{3,4})", s)
    distance = int(m.group(1)) if m else None
    return surface, distance


def _parse_passing(value: str) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], str]:
    raw = value.strip()
    s = _normalize(value)
    nums = re.findall(r"\d+", s)
    floats = [float(x) for x in nums if x]
    c1 = floats[0] if len(floats) >= 1 else None
    c2 = floats[1] if len(floats) >= 2 else None
    c3 = floats[2] if len(floats) >= 3 else None
    c4 = floats[3] if len(floats) >= 4 else None
    if len(floats) == 3:
        c4 = floats[2]
    elif len(floats) == 2:
        c4 = floats[1]
    elif len(floats) == 1:
        c4 = floats[0]
    return c1, c2, c3, c4, raw


def _find_header_index(header_map: Dict[str, int], keywords: List[str]) -> Optional[int]:
    for kw in keywords:
        for key, idx in header_map.items():
            if kw in key:
                return idx
    return None


def _cell_text(cells: list, idx: Optional[int]) -> str:
    if idx is None or idx < 0 or idx >= len(cells):
        return ""
    return _strip(cells[idx])


def parse_history_table_html(html: str) -> List[Dict[str, Any]]:
    """Parse the horse page HTML to extract race history rows.

    This is a regex-only port of demo_horse_history_fetcher.parse_history_rows_from_bs4_table
    + parse_history_rows_from_html_tables, so we don't depend on bs4/pandas.
    """
    rows: List[Dict[str, Any]] = []

    table_m = _find_history_table(html)
    if not table_m:
        return rows

    table_html = table_m

    # Extract header
    header_row_m = re.search(r"<tr[^>]*>([\s\S]*?)</tr>", table_html, re.I)
    if not header_row_m:
        return rows

    headers_raw = re.findall(r"<th[^>]*>([\s\S]*?)</th>", header_row_m.group(1), re.I)
    if not headers_raw:
        return rows
    headers = [_normalize(_strip(h)) for h in headers_raw]
    header_map = {h: i for i, h in enumerate(headers) if h}

    date_idx = _find_header_index(header_map, ["日付"])
    place_idx = _find_header_index(header_map, ["開催", "場所"])
    race_name_idx = _find_header_index(header_map, ["レース名", "レース"])
    class_idx = _find_header_index(header_map, ["クラス", "条件", "格"])
    frame_idx = _find_header_index(header_map, ["枠"])
    horse_num_idx = _find_header_index(header_map, ["馬番"])
    dist_idx = _find_header_index(header_map, ["距離"])
    course_idx = _find_header_index(header_map, ["馬場", "馬場指数"])
    finish_idx = _find_header_index(header_map, ["着順", "着"])
    pop_idx = _find_header_index(header_map, ["人気"])
    odds_idx = _find_header_index(header_map, ["オッズ"])
    last3f_idx = _find_header_index(header_map, ["上り3F", "上り", "上がり"])
    margin_idx = _find_header_index(header_map, ["着差"])
    weight_idx = _find_header_index(header_map, ["斤量"])
    passing_idx = _find_header_index(header_map, ["通過", "コーナー通過順"])
    time_idx = _find_header_index(header_map, ["タイム", "走破タイム"])
    jockey_idx = _find_header_index(header_map, ["騎手"])
    horse_weight_idx = _find_header_index(header_map, ["馬体重"])
    weather_idx = _find_header_index(header_map, ["天気", "天候"])

    # Parse data rows (skip header row)
    all_trs = re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", table_html, re.I)
    for tr_html in all_trs[1:]:
        cells_raw = re.findall(r"<td[^>]*>([\s\S]*?)</td>", tr_html, re.I)
        if len(cells_raw) < 5:
            continue

        date_val = _normalize(_cell_text(cells_raw, date_idx))
        finish_text = _normalize(_cell_text(cells_raw, finish_idx))
        dist_val = _cell_text(cells_raw, dist_idx)

        # skip empty rows
        if not date_val and not finish_text and not dist_val:
            continue

        finish_val: Any = None
        try:
            finish_val = int(re.sub(r"[^\d]", "", finish_text)) if re.search(r"\d", finish_text) else None
        except (ValueError, TypeError):
            finish_val = None

        surface, distance = _split_course_distance(dist_val)
        c1, c2, c3, c4, passing_raw = _parse_passing(_cell_text(cells_raw, passing_idx))

        rows.append({
            "history_date": date_val,
            "history_place": _cell_text(cells_raw, place_idx),
            "history_race_name": _cell_text(cells_raw, race_name_idx),
            "history_class": _cell_text(cells_raw, class_idx),
            "history_frame_number": _cell_text(cells_raw, frame_idx),
            "history_horse_number": _cell_text(cells_raw, horse_num_idx),
            "history_distance_text": dist_val,
            "history_surface": surface,
            "history_distance": distance,
            "history_course_condition": _cell_text(cells_raw, course_idx),
            "history_finish": finish_val,
            "history_popularity": _cell_text(cells_raw, pop_idx),
            "history_odds": _cell_text(cells_raw, odds_idx),
            "history_last3f": _cell_text(cells_raw, last3f_idx),
            "history_margin": _cell_text(cells_raw, margin_idx),
            "history_weight": _cell_text(cells_raw, weight_idx),
            "history_passing": passing_raw,
            "history_time": _cell_text(cells_raw, time_idx),
            "history_jockey": _cell_text(cells_raw, jockey_idx),
            "history_horse_weight": _cell_text(cells_raw, horse_weight_idx),
            "history_weather": _cell_text(cells_raw, weather_idx),
            "corner1": c1,
            "corner2": c2,
            "corner3": c3,
            "corner4": c4,
        })

    return rows


def _find_history_table(html: str) -> Optional[str]:
    """Find the best history table in the horse page HTML."""
    tables = re.findall(r"<table[^>]*>([\s\S]*?)</table>", html, re.I)
    best_score = 0
    best_table = None

    for table_html in tables:
        full = f"<table>{table_html}</table>"
        trs = re.findall(r"<tr", table_html, re.I)
        if len(trs) < 3:
            continue

        header_text = _normalize("".join(re.findall(r"<th[^>]*>([\s\S]*?)</th>", table_html, re.I)))
        if not header_text:
            continue

        score = 0
        if "日付" in header_text:
            score += 20
        if "着順" in header_text or "着" in header_text:
            score += 20
        if "距離" in header_text:
            score += 20
        if "騎手" in header_text:
            score += 10
        if "斤量" in header_text:
            score += 10
        if "レース名" in header_text or "レース" in header_text:
            score += 10
        if "馬体重" in header_text:
            score += 5
        if "血統" in header_text or "生年月日" in header_text:
            score -= 100

        if "db_h_race_results" in table_html.lower() or "raceresults" in table_html.lower():
            score += 100

        if score > best_score:
            best_score = score
            best_table = full

    return best_table


def fetch_horse_history(
    client: NetkeibaClient,
    horse_id: str,
) -> List[Dict[str, Any]]:
    """Fetch race results via AJAX and parse history rows."""
    url = HORSE_AJAX_RESULTS_URL.format(horse_id=horse_id)
    raw = client.fetch(url, label=f"horse_ajax_{horse_id}")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if payload.get("status") != "OK":
        return []
    fragment = payload.get("data") or ""
    if not fragment:
        return []
    return parse_history_table_html(fragment)


def build_history_rows(
    runner: Dict[str, Any],
    parsed_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Attach runner context to parsed history — same as demo_horse_history_fetcher."""
    horse_id = str(runner.get("horse_id", "")).strip()
    horse_url = runner.get("horse_url") or runner.get("_horse_url") or f"https://db.netkeiba.com/horse/{horse_id}/"

    rows: List[Dict[str, Any]] = []
    for idx, r in enumerate(parsed_rows):
        rows.append({
            "race_id": runner.get("race_id", ""),
            "numeric_race_id": runner.get("numeric_race_id", ""),
            "date": runner.get("date", ""),
            "course": runner.get("venue", runner.get("course", "")),
            "race_number": runner.get("race_no", runner.get("race_number")),
            "race_name": runner.get("race_name", ""),
            "horse_number": runner.get("horse_number"),
            "horse_name": runner.get("horse_name", ""),
            "horse_url": horse_url,
            "horse_id": horse_id,
            "sex": runner.get("sex", runner.get("_sex", "")),
            "age": runner.get("age", runner.get("_age")),
            "weight_carried_today": runner.get("weight", runner.get("weight_carried")),
            "jockey_today": runner.get("jockey", ""),
            "odds_today": runner.get("odds", runner.get("_odds")),
            "popularity_today": runner.get("popularity", runner.get("_popularity")),
            "history_index": idx,
            **r,
        })
    return rows
