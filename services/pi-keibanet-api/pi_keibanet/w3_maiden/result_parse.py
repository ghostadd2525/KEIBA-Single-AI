# -*- coding: utf-8 -*-
"""PAGE-C maiden result RAW parser (HTTP 0; Research only; no Feature)."""
from __future__ import annotations

import re
from typing import Any

PARSER_VERSION = "w3b_page_c_result_v1"
SOURCE_NAME = "netkeiba_page_c_cache"

_HORSE_ID_RE = re.compile(
    r"https?://(?:db\.)?netkeiba\.com/horse/(\d{10})",
    re.I,
)
_JOCKEY_ID_RE = re.compile(
    r"https?://(?:db\.)?netkeiba\.com/jockey/(?:result/recent/)?(\d+)/",
    re.I,
)
_TRAINER_ID_RE = re.compile(
    r"https?://(?:db\.)?netkeiba\.com/trainer/(?:result/recent/)?(\d+)/",
    re.I,
)
_RACE_ID_RE = re.compile(r"(?:race_id=|/race/(?:result|)?/)(\d{12})")
_STRIP_TAG = re.compile(r"<[^>]+>")


def _text(html: str) -> str:
    t = _STRIP_TAG.sub(" ", html)
    t = re.sub(r"&nbsp;", " ", t)
    t = re.sub(r"&amp;", "&", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _first(pattern: str, html: str, flags: int = 0) -> str | None:
    m = re.search(pattern, html, flags)
    if not m:
        return None
    return m.group(1).strip() if m.lastindex else m.group(0).strip()


def _parse_sex_age(raw: str | None) -> tuple[str | None, int | None]:
    if not raw:
        return None, None
    s = raw.strip()
    m = re.match(r"^([牡牝セ騸])\s*(\d{1,2})$", s)
    if m:
        return m.group(1), int(m.group(2))
    m = re.match(r"^([牡牝セ騸])(\d{1,2})$", s)
    if m:
        return m.group(1), int(m.group(2))
    return s or None, None


def _parse_weight(cell: str) -> tuple[int | None, int | None]:
    """Return (body_weight, body_weight_change). Missing → (None, None)."""
    t = _text(cell)
    if not t or t in ("-", "—", "－", "計不"):
        return None, None
    m = re.match(r"^(\d{2,3})\s*(?:\(([\+\-]?\d+|ー|－)\))?", t)
    if not m:
        return None, None
    bw = int(m.group(1))
    ch_raw = m.group(2)
    if ch_raw is None or ch_raw in ("ー", "－", ""):
        return bw, None
    try:
        return bw, int(ch_raw)
    except ValueError:
        return bw, None


def _parse_finish(raw: str | None) -> tuple[int | None, str | None]:
    """Return (finish_position, result_status)."""
    if raw is None:
        return None, None
    s = raw.strip()
    if not s:
        return None, None
    if s.isdigit():
        return int(s), "finished"
    # 取消 / 除外 / 中止 / 失格 etc.
    return None, s


def _extract_result_table(html: str) -> str | None:
    m = re.search(
        r'<table[^>]*id="All_Result_Table"[^>]*>([\s\S]*?)</table>',
        html,
        re.I,
    )
    if m:
        return m.group(0)
    m = re.search(
        r'<table[^>]*class="[^"]*RaceTable01[^"]*"[^>]*>([\s\S]*?)</table>',
        html,
        re.I,
    )
    return m.group(0) if m else None


def parse_race_header(html: str, *, expected_race_id: str | None = None) -> dict[str, Any]:
    """Race-level RAW from PAGE-C. Absent fields stay None (no inference)."""
    race: dict[str, Any] = {
        "race_id": None,
        "race_date": None,
        "venue": None,
        "race_number": None,
        "race_name": None,
        "class_condition": None,
        "age_condition": None,
        "sex_condition": None,
        "surface": None,
        "distance": None,
        "direction": None,
        "weather": None,
        "track_condition": None,
        "start_time": None,
        "field_size": None,
    }

    ids = _RACE_ID_RE.findall(html)
    if expected_race_id and expected_race_id in ids:
        race["race_id"] = expected_race_id
    elif ids:
        race["race_id"] = ids[0]
    elif expected_race_id:
        race["race_id"] = expected_race_id

    race["race_name"] = _first(r'class="RaceName"[^>]*>\s*([^<]+)', html) or _first(
        r"RaceName\">\s*([^<]+)", html
    )

    # race_date from payback / kaisai_date=YYYYMMDD
    kd = _first(r"kaisai_date=(\d{8})", html)
    if kd:
        race["race_date"] = f"{kd[0:4]}-{kd[4:6]}-{kd[6:8]}"

    data01 = _first(r'class="RaceData01"[^>]*>([\s\S]*?)</div>', html) or ""
    data01_text = _text(data01)
    # 11:05発走
    st = re.search(r"(\d{1,2}:\d{2})\s*発走", data01_text)
    if st:
        race["start_time"] = st.group(1)
    # ダ1800m / 芝1600m / 障 etc.
    surf = re.search(r"(芝|ダ|障)\s*(\d{3,4})\s*m", data01_text)
    if surf:
        race["surface"] = surf.group(1)
        race["distance"] = int(surf.group(2))
    direc = re.search(r"[（(](右|左|直|右 外|左 外)[）)]", data01_text)
    if direc:
        race["direction"] = direc.group(1)
    weather = re.search(r"天候[:：]\s*([^\s/]+)", data01_text)
    if weather:
        race["weather"] = weather.group(1).strip()
    track = re.search(r"馬場[:：]\s*([^\s/<]+)", data01_text)
    if track:
        race["track_condition"] = track.group(1).strip()

    data02 = _first(r'class="RaceData02"[^>]*>([\s\S]*?)</div>', html) or ""
    spans = re.findall(r"<span[^>]*>([\s\S]*?)</span>", data02)
    span_texts = [_text(s) for s in spans if _text(s)]
    # Typical: 1回 / 中山 / 3日目 / サラ系３歳 / 未勝利 / (混)[指] / 馬齢 / 16頭
    for t in span_texts:
        if re.fullmatch(r"\d+頭", t):
            race["field_size"] = int(t.replace("頭", ""))
        elif t in (
            "東京",
            "中山",
            "京都",
            "阪神",
            "中京",
            "小倉",
            "新潟",
            "福島",
            "札幌",
            "函館",
        ):
            race["venue"] = t
        elif "歳" in t and ("サラ" in t or "障害" in t or re.search(r"[０-９0-9]", t)):
            if race["age_condition"] is None:
                race["age_condition"] = t
        elif t in ("未勝利", "新馬", "1勝クラス", "2勝クラス", "3勝クラス", "オープン"):
            race["class_condition"] = t
        elif t.startswith("(") or t.startswith("（") or "[指]" in t or "特指" in t:
            race["sex_condition"] = t

    rid = race.get("race_id")
    if isinstance(rid, str) and len(rid) == 12 and rid.isdigit():
        race["race_number"] = int(rid[-2:])

    return race


def parse_runners(html: str, *, race_id: str | None = None) -> list[dict[str, Any]]:
    table = _extract_result_table(html)
    if not table:
        return []
    tbody = re.search(r"<tbody[^>]*>([\s\S]*?)</tbody>", table, re.I)
    body = tbody.group(1) if tbody else table
    rows_html = re.findall(r"<tr[^>]*class=\"[^\"]*HorseList[^\"]*\"[^>]*>[\s\S]*?</tr>", body, re.I)
    if not rows_html:
        # fallback: all tr after header
        all_tr = re.findall(r"<tr[^>]*>[\s\S]*?</tr>", body, re.I)
        rows_html = [tr for tr in all_tr if "Horse_Info" in tr or "/horse/" in tr]

    runners: list[dict[str, Any]] = []
    for tr in rows_html:
        rank_raw = _first(r'class="Rank"[^>]*>\s*([^<]+)', tr)
        finish_pos, result_status = _parse_finish(rank_raw)

        waku = _first(r'class="Num\s+Waku\d+"[^>]*>\s*<div>\s*(\d+)\s*<', tr) or _first(
            r"Waku(\d+)", tr
        )
        umaban = _first(r'class="Num\s+Txt_C"[^>]*>\s*<div>\s*(\d+)\s*<', tr)

        horse_m = _HORSE_ID_RE.search(tr)
        horse_id = horse_m.group(1) if horse_m else None
        horse_name = _first(r'class="HorseNameSpan"[^>]*>\s*([^<]+)', tr) or _first(
            r'title="([^"]+)"[^>]*>\s*<span class="HorseNameSpan"', tr
        )

        sex_age_raw = _first(r'class="Lgt_Txt[^"]*"[^>]*>\s*([^<]+)', tr)
        sex, age = _parse_sex_age(_text(sex_age_raw) if sex_age_raw else None)

        carried = _first(r'class="JockeyWeight"[^>]*>\s*([^<]+)', tr)
        carried_weight = None
        if carried:
            try:
                carried_weight = float(carried.strip())
            except ValueError:
                carried_weight = None

        jockey_m = _JOCKEY_ID_RE.search(tr)
        jockey_id = jockey_m.group(1) if jockey_m else None
        jockey_name = _first(r'class="JockeyNameSpan"[^>]*>\s*([^<]+)', tr)

        # finish time: first RaceTime in Time td that looks like clock
        times = re.findall(r'class="RaceTime"[^>]*>\s*([^<]*)', tr)
        finish_time = None
        margin = None
        if times:
            t0 = times[0].strip()
            if t0:
                finish_time = t0
            if len(times) > 1 and times[1].strip():
                margin = times[1].strip()

        popularity = _first(r'class="OddsPeople"[^>]*>\s*([^<]+)', tr)
        pop_i = int(popularity) if popularity and popularity.strip().isdigit() else None

        odds_raw = _first(
            r'class="Odds[^"]*Txt_R"[^>]*>\s*<span[^>]*>\s*([^<]+)', tr
        ) or _first(r'class="Odds_Ninki"[^>]*>\s*([^<]+)', tr)
        odds = None
        if odds_raw:
            try:
                odds = float(odds_raw.strip())
            except ValueError:
                odds = None

        last3f_raw = _first(r'class="Time\s+BgYellow"[^>]*>\s*([^<]+)', tr)
        if last3f_raw is None:
            # non-highlight last3f cells: look for Time td after Odds without RaceTime
            m_l3 = re.search(
                r'class="Odds[^"]*Txt_R"[\s\S]*?</td>\s*<td class="Time[^"]*">\s*([^<]+)',
                tr,
            )
            last3f_raw = m_l3.group(1).strip() if m_l3 else None
        last3f = None
        if last3f_raw:
            try:
                last3f = float(last3f_raw.strip())
            except ValueError:
                last3f = None

        corner = _first(r'class="PassageRate"[^>]*>\s*([^<]+)', tr)

        trainer_m = _TRAINER_ID_RE.search(tr)
        race_time_trainer_id = trainer_m.group(1) if trainer_m else None
        race_time_trainer_name = _first(r'class="TrainerNameSpan"[^>]*>\s*([^<]+)', tr)
        race_time_trainer_stable = _first(r'class="Label1"[^>]*>\s*([^<]+)', tr)

        weight_cell = _first(r'<td class="Weight"[^>]*>([\s\S]*?)</td>', tr) or ""
        body_weight, body_weight_change = _parse_weight(weight_cell)

        runners.append(
            {
                "race_id": race_id,
                "horse_id": horse_id,
                "horse_name": horse_name.strip() if horse_name else None,
                "frame": int(waku) if waku and str(waku).isdigit() else None,
                "horse_number": int(umaban) if umaban and str(umaban).isdigit() else None,
                "sex": sex,
                "age": age,
                "carried_weight": carried_weight,
                "jockey_id": jockey_id,
                "jockey_name": jockey_name.strip() if jockey_name else None,
                # race-time trainer namespace (never mix with W4 D1 current trainer)
                "race_time_trainer_id": race_time_trainer_id,
                "race_time_trainer_name": (
                    race_time_trainer_name.strip() if race_time_trainer_name else None
                ),
                "race_time_trainer_stable": (
                    race_time_trainer_stable.strip() if race_time_trainer_stable else None
                ),
                "finish_position": finish_pos,
                "finish_time": finish_time,
                "margin": margin,
                "corner_passing": corner.strip() if corner else None,
                "last3f": last3f,
                "body_weight": body_weight,
                "body_weight_change": body_weight_change,
                "popularity": pop_i,
                "odds": odds,
                "result_status": result_status,
            }
        )
    return runners


def classify_parse_status(
    race: dict[str, Any],
    runners: list[dict[str, Any]],
    *,
    expected_race_id: str | None = None,
) -> tuple[str, list[str]]:
    """Return (queue_status, reasons)."""
    reasons: list[str] = []
    if not race.get("race_id"):
        reasons.append("missing_race_id")
    if expected_race_id and race.get("race_id") and race["race_id"] != expected_race_id:
        reasons.append("race_id_mismatch")
    if not runners:
        reasons.append("no_runners")
        return "parse_failed", reasons

    missing_hid = sum(1 for r in runners if not r.get("horse_id"))
    if missing_hid:
        reasons.append(f"horse_id_missing={missing_hid}")

    # field_size vs runner count (informational partial if diverge)
    fs = race.get("field_size")
    if isinstance(fs, int) and fs > 0 and len(runners) != fs:
        reasons.append(f"field_size_mismatch={fs}_vs_{len(runners)}")

    if "no_runners" in reasons or "missing_race_id" in reasons:
        return "parse_failed", reasons
    if "race_id_mismatch" in reasons and not any(r.get("horse_id") for r in runners):
        return "parse_failed", reasons
    if missing_hid or any(
        x.startswith("field_size_mismatch") for x in reasons
    ):
        # horse_id missing → partial; field mismatch alone with all IDs → still complete if IDs ok
        if missing_hid:
            return "partial", reasons
    return "result_complete", reasons


def parse_page_c_result(
    html: str,
    *,
    expected_race_id: str | None = None,
) -> dict[str, Any]:
    """Parse PAGE-C HTML into race_raw + runner_result_raw list."""
    race = parse_race_header(html, expected_race_id=expected_race_id)
    rid = race.get("race_id") or expected_race_id
    runners = parse_runners(html, race_id=rid if isinstance(rid, str) else None)
    status, reasons = classify_parse_status(
        race, runners, expected_race_id=expected_race_id
    )
    return {
        "parse_ok": status in ("result_complete", "partial"),
        "queue_status": status,
        "reasons": reasons,
        "parser_version": PARSER_VERSION,
        "source": SOURCE_NAME,
        "race": race,
        "runners": runners,
        "runner_count": len(runners),
        "horse_id_present": sum(1 for r in runners if r.get("horse_id")),
        "horse_id_missing": sum(1 for r in runners if not r.get("horse_id")),
    }
