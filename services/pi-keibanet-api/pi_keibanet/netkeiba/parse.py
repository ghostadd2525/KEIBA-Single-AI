# -*- coding: utf-8 -*-
"""Parse netkeiba HTML into structured rows (stdlib regex)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from typing import Any

from ..venues import COURSE_NAME_TO_CODE, COURSE_CODE_TO_NAME

_RACE_ID_RE = re.compile(r"race_id=(\d{12})")
_TAG_RE = re.compile(r"<[^>]+>")
_VENUE_BLOCK_RE = re.compile(r"<dl class=\"RaceList_DataList\">[\s\S]*?</dl>", re.I)
_TITLE_RE = re.compile(
    r"RaceList_DataTitle\">\s*(?:<small>\s*(\d+)\s*回\s*</small>)?\s*([^<]+?)\s*<small>\s*(\d+)\s*日目\s*</small>",
    re.I,
)
_LIST_ITEM_RE = re.compile(
    r"<li class=\"RaceList_DataItem[\s\S]*?</li>",
    re.I,
)
_HORSE_LIST_RE = re.compile(r'<tr class="HorseList"[^>]*>([\s\S]*?)</tr>', re.I)
_SP_DAY_WRAP_RE = re.compile(
    r'<div class="RaceListDayWrap"([^>]*)>([\s\S]*?)(?=<div class="RaceListDayWrap"|$)',
    re.I,
)
_SP_MAIN_BOX_RE = re.compile(
    r'<div class="RaceList_Main_Box">([\s\S]*?)<div class="RaceList_Menu_Box">',
    re.I,
)


def _strip_tags(text: str) -> str:
    return unescape(_TAG_RE.sub("", text or "")).strip()


def _normalize(text: str) -> str:
    s = _strip_tags(text)
    s = s.replace("\u3000", " ").replace("\xa0", " ")
    s = s.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    return re.sub(r"\s+", " ", s).strip()


def _compact(text: str) -> str:
    return _normalize(text).replace(" ", "")


@dataclass(frozen=True)
class _Meeting:
    venue: str
    venue_code: str
    kai: str
    day: str


@dataclass(frozen=True)
class _ListRace:
    venue: str
    race_no: int
    race_id: str
    race_name: str = ""
    post_time: str = ""


def _year_token(date: str) -> str:
    return date.replace("-", "")[:4]


def _build_race_id(*, year: str, venue_code: str, kai: str, day: str, race_no: int) -> str:
    return f"{year}{venue_code}{kai}{day}{int(race_no):02d}"


def _sp_active_day_html(html: str) -> str:
    """SP レース一覧は土日が同一HTML。表示中（display:none 以外）の日だけ使う。"""
    blocks = _SP_DAY_WRAP_RE.findall(html or "")
    if not blocks:
        return html or ""
    visible: list[str] = []
    hidden: list[str] = []
    for attrs, body in blocks:
        compact = re.sub(r"\s+", "", attrs or "").lower()
        if "display:none" in compact:
            hidden.append(body)
        else:
            visible.append(body)
    if visible:
        return "\n".join(visible)
    return "\n".join(hidden) if hidden else (html or "")


def _parse_meetings_from_sp(html: str) -> list[_Meeting]:
    day_html = _sp_active_day_html(html)
    seen: set[tuple[str, str, str]] = set()
    meetings: list[_Meeting] = []
    for box in _SP_MAIN_BOX_RE.findall(day_html):
        m_id = _RACE_ID_RE.search(box)
        if not m_id:
            continue
        rid = m_id.group(1)
        if len(rid) < 10:
            continue
        venue_code, kai, day = rid[4:6], rid[6:8], rid[8:10]
        venue = COURSE_CODE_TO_NAME.get(venue_code)
        if not venue:
            continue
        key = (venue_code, kai, day)
        if key in seen:
            continue
        seen.add(key)
        meetings.append(_Meeting(venue=venue, venue_code=venue_code, kai=kai, day=day))
    return meetings


def _parse_list_races_from_sp(html: str) -> list[_ListRace]:
    day_html = _sp_active_day_html(html)
    races: list[_ListRace] = []
    seen: set[str] = set()
    for box in _SP_MAIN_BOX_RE.findall(day_html):
        m_id = _RACE_ID_RE.search(box)
        m_num = re.search(r"Race_Num[^>]*>\s*<span>\s*(\d+)\s*R\s*</span>", box, re.I)
        if not m_id or not m_num:
            continue
        rid = m_id.group(1)
        if rid in seen:
            continue
        seen.add(rid)
        venue = COURSE_CODE_TO_NAME.get(rid[4:6], "")
        if not venue:
            continue
        m_name = re.search(r'class="Race_Name"[^>]*>([\s\S]*?)</div>', box, re.I)
        race_name = _normalize(m_name.group(1)) if m_name else ""
        m_time = re.search(r'class="Race_Data"[^>]*>[\s\S]*?(\d{1,2}:\d{2})', box, re.I)
        post_time = ""
        if m_time:
            hh, mm = m_time.group(1).split(":")
            post_time = f"{int(hh):02d}:{mm}"
        races.append(
            _ListRace(
                venue=venue,
                race_no=int(m_num.group(1)),
                race_id=rid,
                race_name=race_name,
                post_time=post_time,
            )
        )
    return races


def parse_meetings_from_race_list(html: str) -> list[_Meeting]:
    meetings: list[_Meeting] = []
    for block in _VENUE_BLOCK_RE.findall(html):
        m_title = _TITLE_RE.search(block)
        if not m_title:
            continue
        kai_raw, venue_raw, day_raw = m_title.group(1), m_title.group(2), m_title.group(3)
        venue = _normalize(venue_raw)
        code = COURSE_NAME_TO_CODE.get(venue)
        if not code or not kai_raw or not day_raw:
            continue
        meetings.append(
            _Meeting(
                venue=venue,
                venue_code=code,
                kai=f"{int(kai_raw):02d}",
                day=f"{int(day_raw):02d}",
            )
        )
    if meetings:
        return meetings
    return _parse_meetings_from_sp(html)


def parse_list_races_from_race_list(html: str) -> list[_ListRace]:
    races: list[_ListRace] = []
    for block in _VENUE_BLOCK_RE.findall(html):
        m_title = _TITLE_RE.search(block)
        if not m_title:
            continue
        venue = _normalize(m_title.group(2))
        if venue not in COURSE_NAME_TO_CODE:
            continue
        for item in _LIST_ITEM_RE.findall(block):
            m_id = _RACE_ID_RE.search(item)
            m_num = re.search(r"Race_Num[\s\S]*?(\d+)\s*R", item, re.I)
            if not m_id or not m_num:
                continue
            m_name = re.search(r'class="ItemTitle"[^>]*>([^<]+)', item, re.I)
            if not m_name:
                m_name = re.search(r'class="RaceList_ItemTitle"[^>]*>[\s\S]*?<span[^>]*>([^<]+)', item, re.I)
            race_name = _normalize(m_name.group(1)) if m_name else ""
            m_time = re.search(
                r'class="RaceList_Itemtime"[^>]*>\s*(\d{1,2}:\d{2})',
                item,
                re.I,
            )
            post_time = ""
            if m_time:
                hh, mm = m_time.group(1).split(":")
                post_time = f"{int(hh):02d}:{mm}"
            races.append(
                _ListRace(
                    venue=venue,
                    race_no=int(m_num.group(1)),
                    race_id=m_id.group(1),
                    race_name=race_name,
                    post_time=post_time,
                )
            )
    if races:
        return races
    return _parse_list_races_from_sp(html)


def find_numeric_race_id(html: str, *, date: str, venue: str, race_no: int) -> str | None:
    code = COURSE_NAME_TO_CODE.get(venue)
    if not code:
        return None

    year = _year_token(date)
    target = int(race_no)

    seen: set[str] = set()
    for rid in _RACE_ID_RE.findall(html):
        if rid in seen:
            continue
        seen.add(rid)
        if rid[4:6] != code:
            continue
        if int(rid[-2:]) != target:
            continue
        return rid

    for item in parse_list_races_from_race_list(html):
        if item.venue == venue and item.race_no == target:
            return item.race_id

    for meeting in parse_meetings_from_race_list(html):
        if meeting.venue != venue:
            continue
        return _build_race_id(
            year=year,
            venue_code=meeting.venue_code,
            kai=meeting.kai,
            day=meeting.day,
            race_no=target,
        )

    return None


def shutuba_has_race(html: str) -> bool:
    if _HORSE_LIST_RE.search(html):
        return True
    m = re.search(r'class="[^"]*RaceName[^"]*"[^>]*>(.*?)</', html, re.I | re.S)
    if m and _normalize(m.group(1)):
        return True
    return False


def _race_data_text(html: str, class_name: str) -> str:
    m = re.search(rf'class="{class_name}"[^>]*>([\s\S]*?)</div>', html, re.I)
    if not m:
        return ""
    return _normalize(m.group(1))


def parse_race_conditions_from_shutuba(html: str) -> dict[str, str]:
    """Extract turn / weather / track_condition from RaceData01 (Win5AI compatible)."""
    data01 = _race_data_text(html, "RaceData01")
    data02 = _race_data_text(html, "RaceData02")
    combined = f"{data01} {data02}"

    turn = "unknown"
    m_turn = re.search(r"[\(（]\s*([右左直])", combined)
    if m_turn:
        turn = m_turn.group(1)
    elif re.search(r"(?<![A-Za-z])([右左直])(?![A-Za-z])", combined):
        m_turn2 = re.search(r"(?<![A-Za-z])([右左直])(?![A-Za-z])", combined)
        if m_turn2:
            turn = m_turn2.group(1)

    weather = "unknown"
    m_weather = re.search(r"天候\s*[:：]\s*([^\s/|]+)", combined)
    if m_weather:
        weather = m_weather.group(1).strip()

    track_condition = "unknown"
    m_track = re.search(r"馬場\s*[:：]\s*([^\s/|]+)", combined)
    if m_track:
        track_condition = m_track.group(1).strip()
    if track_condition == "unknown":
        track_condition = parse_track_condition(html)

    return {
        "turn": turn,
        "weather": weather,
        "track_condition": track_condition,
    }


def parse_race_meta_from_shutuba(
    html: str,
    *,
    date: str,
    venue: str,
    race_no: int,
    numeric_race_id: str,
) -> dict[str, Any]:
    compact = _compact(html)
    distance = 0
    surface = ""

    m_dist = re.search(r"(芝|ダート|ダ)(\d{3,4})m", compact)
    if m_dist:
        surface = "ダ" if m_dist.group(1).startswith("ダ") else "芝"
        distance = int(m_dist.group(2))

    m_name = re.search(r'<div[^>]*class="[^"]*RaceName[^"]*"[^>]*>(.*?)</div>', html, re.I | re.S)
    if not m_name:
        m_name = re.search(r'<h1[^>]*>[\s\S]*?RaceName[^>]*>(.*?)</span>', html, re.I | re.S)
    race_name = _normalize(m_name.group(1)) if m_name else ""

    post_time = ""
    m_post = re.search(r"(\d{1,2}):(\d{2})\s*発走", compact)
    if m_post:
        post_time = f"{int(m_post.group(1)):02d}:{m_post.group(2)}"
    elif race_name:
        m_in_name = re.search(r"(\d{1,2}):(\d{2})\s*発走", race_name)
        if m_in_name:
            post_time = f"{int(m_in_name.group(1)):02d}:{m_in_name.group(2)}"
            race_name = _normalize(re.sub(r"\s*\d{1,2}:\d{2}\s*発走", "", race_name))

    entries = parse_entries_from_shutuba(html)
    field_size = len(entries)
    if field_size == 0:
        m_cnt = re.search(r"(\d{1,2})頭", compact)
        if m_cnt:
            field_size = int(m_cnt.group(1))

    conditions = parse_race_conditions_from_shutuba(html)

    from ..venues import collector_race_id

    payload: dict[str, Any] = {
        "race_id": collector_race_id(date, venue, race_no),
        "date": date,
        "venue": venue,
        "race_no": race_no,
        "distance": distance or 1600,
        "surface": surface or "芝",
        "race_name": race_name,
        "field_size": field_size,
        "numeric_race_id": numeric_race_id,
        **conditions,
    }
    if post_time:
        payload["post_time"] = post_time
    return payload


def _parse_horse_list_row(tr_html: str, *, fallback_number: int) -> dict[str, Any] | None:
    m_horse = re.search(
        r'class="HorseName"[^>]*>[\s\S]*?(?:title="([^"]+)"|>([^<]+))[\s\S]*?(?:db\.netkeiba\.com/horse/|/horse/)(\d+)',
        tr_html,
        re.I,
    )
    if not m_horse:
        m_horse = re.search(
            r'(?:db\.netkeiba\.com/horse/|/horse/)(\d+)[^>]*>([\s\S]*?)</a>',
            tr_html,
            re.I,
        )
    if not m_horse:
        return None

    if m_horse.lastindex and m_horse.lastindex >= 3:
        horse_name = _normalize(m_horse.group(1) or m_horse.group(2) or "")
        horse_id = m_horse.group(3)
    else:
        horse_id = m_horse.group(1)
        horse_name = _normalize(m_horse.group(2))

    if not horse_name or "HorseName" not in tr_html:
        return None

    m_jockey = re.search(r'class="Jockey"[\s\S]*?<a[^>]*title="([^"]+)"', tr_html, re.I)
    if not m_jockey:
        m_jockey = re.search(r'class="Jockey"[\s\S]*?<a[^>]*>([^<]+)</a>', tr_html, re.I)
    jockey = _normalize(m_jockey.group(1)) if m_jockey else ""

    m_waku = re.search(r'class="Waku[^"]*"[^>]*>[\s\S]*?<span[^>]*>(\d+)</span>', tr_html, re.I)
    frame = _to_int(m_waku.group(1)) if m_waku else 0

    m_umaban = re.search(r'class="Umaban[^"]*"[^>]*>\s*(\d+)\s*<', tr_html, re.I)
    horse_number = _to_int(m_umaban.group(1)) if m_umaban else None
    if horse_number is None:
        m_tr = re.search(r'\bid="tr_(\d+)"', tr_html, re.I)
        horse_number = _to_int(m_tr.group(1)) if m_tr else None
    if horse_number is None:
        horse_number = fallback_number

    # 性齢 (e.g. "牡3", "牝4", "セ5")
    m_barei = re.search(r'class="Barei[^"]*"[^>]*>([\s\S]*?)</td>', tr_html, re.I)
    sex, age = "", None
    if m_barei:
        barei_text = _normalize(m_barei.group(1))
        if barei_text:
            if barei_text[0] in ("牡", "牝", "セ"):
                sex = barei_text[0]
            age_m = re.search(r"(\d+)", barei_text)
            age = int(age_m.group(1)) if age_m else None

    m_weight = re.search(
        r'class="Barei[^"]*"[^>]*>[\s\S]*?</td>\s*<td[^>]*>\s*([\d.]+)\s*<',
        tr_html,
        re.I,
    )
    weight = _to_float(m_weight.group(1)) if m_weight else 0.0

    # 調教師
    m_trainer = re.search(r'class="Trainer"[\s\S]*?<a[^>]*title="([^"]+)"', tr_html, re.I)
    if not m_trainer:
        m_trainer = re.search(r'class="Trainer"[\s\S]*?<a[^>]*>([^<]+)</a>', tr_html, re.I)
    trainer = _normalize(m_trainer.group(1)) if m_trainer else ""

    m_odds = re.search(r'id="odds-[^"]+"[^>]*>([^<]+)</span>', tr_html, re.I)
    odds = _to_float(m_odds.group(1)) if m_odds else None

    m_pop = re.search(r'id="ninki-[^"]+"[^>]*>([^<]+)</span>', tr_html, re.I)
    popularity = _to_int(m_pop.group(1)) if m_pop else None

    horse_url = f"https://db.netkeiba.com/horse/{horse_id}/" if horse_id else ""

    row: dict[str, Any] = {
        "horse_number": horse_number,
        "frame": frame or 0,
        "horse_name": horse_name,
        "jockey": jockey,
        "weight": weight if weight is not None else 0.0,
        "horse_id": horse_id,
        "_sex": sex,
        "_age": age,
        "_trainer": trainer,
        "_horse_url": horse_url,
    }
    if odds is not None:
        row["_odds"] = odds
    if popularity is not None:
        row["_popularity"] = popularity
    return row


def _dedupe_entries_by_horse_id(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep one row per horse_id (shutuba may contain duplicate placeholder rows)."""
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for row in rows:
        hid = str(row.get("horse_id") or "").strip()
        if not hid:
            continue
        if hid not in by_id:
            by_id[hid] = row
            order.append(hid)
            continue
        prev = by_id[hid]
        prev_score = int(bool(prev.get("_odds"))) + int(bool(prev.get("horse_name")))
        new_score = int(bool(row.get("_odds"))) + int(bool(row.get("horse_name")))
        if new_score > prev_score:
            by_id[hid] = row
    out = [by_id[hid] for hid in order]
    out.sort(key=lambda r: int(r.get("horse_number") or 999))
    return out


def parse_entries_from_shutuba(html: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    horse_rows = _HORSE_LIST_RE.findall(html)
    if horse_rows:
        seq = 0
        for tr_html in horse_rows:
            if "HorseName" not in tr_html and "/horse/" not in tr_html and "db.netkeiba.com/horse/" not in tr_html:
                continue
            seq += 1
            row = _parse_horse_list_row(tr_html, fallback_number=seq)
            if row and row.get("horse_name"):
                rows.append(row)
        if rows:
            return _dedupe_entries_by_horse_id(rows)

    for table_html in re.findall(r"<table[\s\S]*?</table>", html, re.I):
        compact = _compact(table_html)
        if "馬名" not in compact:
            continue
        if "枠" not in compact and "馬番" not in compact:
            continue

        header_cells = re.findall(r"<th[^>]*>([\s\S]*?)</th>", table_html, re.I)
        headers = [_compact(h) for h in header_cells]
        if not headers:
            first_tr = re.search(r"<tr[^>]*>([\s\S]*?)</tr>", table_html, re.I)
            if first_tr:
                headers = [_compact(x) for x in re.findall(r"<t[dh][^>]*>([\s\S]*?)</t[dh]>", first_tr.group(1), re.I)]

        def idx(*keys: str) -> int | None:
            for key in keys:
                for i, h in enumerate(headers):
                    if key in h:
                        return i
            return None

        i_frame = idx("枠")
        i_num = idx("馬番")
        i_name = idx("馬名")
        i_jockey = idx("騎手")
        i_weight = idx("斤量")
        i_odds = idx("オッズ", "予想オッズ")
        i_pop = idx("人気")

        seq = 0
        for tr in re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", table_html, re.I)[1:]:
            if "/horse/" not in tr and "db.netkeiba.com/horse/" not in tr:
                continue
            cells = re.findall(r"<td[^>]*>([\s\S]*?)</td>", tr, re.I)
            if len(cells) < 3:
                continue

            def cell(i: int | None) -> str:
                if i is None or i >= len(cells):
                    return ""
                return _normalize(cells[i])

            horse_name = cell(i_name)
            m_horse = re.search(r"(?:db\.netkeiba\.com/horse/|/horse/)(\d+)", tr)
            horse_id = m_horse.group(1) if m_horse else ""
            if not horse_name:
                m_anchor = re.search(
                    r"<a[^>]*href=\"[^\"]*(?:db\.netkeiba\.com/horse/|/horse/)(\d+)[^\"]*\"[^>]*>([\s\S]*?)</a>",
                    tr,
                    re.I,
                )
                if m_anchor:
                    horse_id = horse_id or m_anchor.group(1)
                    horse_name = _normalize(m_anchor.group(2))

            horse_number = _to_int(cell(i_num))
            frame = _to_int(cell(i_frame))
            weight = _to_float(cell(i_weight))
            odds = _to_float(cell(i_odds))
            popularity = _to_int(cell(i_pop))

            if horse_number is None:
                seq += 1
                horse_number = seq

            if not horse_name:
                continue

            row = {
                "horse_number": horse_number,
                "frame": frame or 0,
                "horse_name": horse_name,
                "jockey": cell(i_jockey),
                "weight": weight if weight is not None else 0.0,
            }
            if horse_id:
                row["horse_id"] = horse_id
            if odds is not None:
                row["_odds"] = odds
            if popularity is not None:
                row["_popularity"] = popularity
            rows.append(row)

        if rows:
            break
    return _dedupe_entries_by_horse_id(rows)


def parse_track_condition(html: str) -> str:
    compact = _compact(html)
    m = re.search(r"馬場[:：]?(良|稍重|稍|重|不良)", compact)
    if not m:
        return "良"
    val = m.group(1)
    if val == "稍":
        return "稍重"
    return val


def parse_odds_from_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    odds: list[dict[str, Any]] = []
    for e in entries:
        win = e.get("_odds")
        if win is None:
            continue
        odds.append({"horse_number": e["horse_number"], "win": float(win)})
    return odds


def parse_jra_win_odds_payload(payload: dict[str, Any] | str) -> list[dict[str, Any]]:
    """
    api_get_jra_odds.html (type=1) → [{horse_number, win, popularity?}, ...]

    data.odds['1']['01'] = ['3.7', '0', '3']  # win, ?, popularity
    status が middle でも data に値が入ることがある（発売中）。
    """
    if isinstance(payload, str):
        import json

        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return []
    if not isinstance(payload, dict):
        return []

    data = payload.get("data")
    if isinstance(data, str):
        if not data.strip():
            return []
        import json

        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return []
    if not isinstance(data, dict):
        return []

    odds_root = data.get("odds") if isinstance(data.get("odds"), dict) else data
    tan = odds_root.get("1") if isinstance(odds_root, dict) else None
    if not isinstance(tan, dict):
        return []

    rows: list[dict[str, Any]] = []
    for key, val in tan.items():
        try:
            horse_number = int(str(key).lstrip("0") or "0")
        except ValueError:
            continue
        if horse_number <= 0:
            continue
        win = None
        popularity = None
        if isinstance(val, (list, tuple)) and val:
            win = _to_float(str(val[0]))
            if len(val) >= 3:
                popularity = _to_int(str(val[2]))
        elif isinstance(val, (int, float, str)):
            win = _to_float(str(val))
        if win is None:
            continue
        row: dict[str, Any] = {"horse_number": horse_number, "win": float(win)}
        if popularity is not None:
            row["popularity"] = popularity
        rows.append(row)
    rows.sort(key=lambda r: int(r["horse_number"]))
    return rows


def _to_int(text: str) -> int | None:
    text = re.sub(r"[^\d]", "", text or "")
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _to_float(text: str) -> float | None:
    text = (text or "").replace(",", "").strip()
    if not text or text in {"---", "-", "**"} or text.startswith("---"):
        return None
    try:
        return float(text)
    except ValueError:
        return None
