# -*- coding: utf-8 -*-
"""
Catalog ID 空間（Win5 / Public）と Core ID 空間の明示分離。

同じ YYYY-MM-DD-NN-NN 文字列でも namespace が違う。
形式から venue / 意味を推測してはならない。

  2026-08-16-03-10     Catalog / Win5 identity（label_no=03。競馬場コードではない）
  2026-08-16-札幌-10    venue-qualified identity
  20260816_sapporo_10  resolver slug alias
  2026-08-16-01-10     Core identity（JRA venue 01=札幌）
  202601010810         JRA numeric identity

Catalog→Core bridge は必ず Catalog 行の identity（course / numeric_race_id）から行う。
win5-ai レガシー _VENUE_CODE_TO_JA（03=函館 等）は使わない。
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

# JRA 公式開催場コード（numeric_race_id[4:6] / Core venue 桁）。
# Win5 Catalog の label_no（その日の開催順）とは別空間。
JRA_VENUE_CODE_TO_JA: dict[str, str] = {
    "01": "札幌",
    "02": "函館",
    "03": "福島",
    "04": "新潟",
    "05": "東京",
    "06": "中山",
    "07": "中京",
    "08": "京都",
    "09": "阪神",
    "10": "小倉",
}
JRA_COURSE_TO_CODE: dict[str, str] = {v: k for k, v in JRA_VENUE_CODE_TO_JA.items()}

_CATALOG_ID_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(\d{2})-(\d{2})$")
_FIXTURE_DIR = Path(__file__).resolve().parent / "catalog_fixtures"


@dataclass(frozen=True)
class CatalogRace:
    """Catalog 空間の1行。core_race_id は bridge 結果であり Catalog ID そのものではない。"""

    catalog_id: str
    date: str
    course: str
    race_no: int
    numeric_race_id: str = ""
    race_name: str = ""
    core_race_id: str = ""
    jra_venue_code: str = ""
    field_size: int | None = None
    post_time: str = ""
    label_no: str = ""


def parse_jra_numeric_id(numeric_race_id: str) -> tuple[str, str, str, int] | None:
    """
    JRA 12桁: YYYY + venue(2) + kai(2) + day(2) + race(2)

    カレンダー日付は numeric に含まれない。venue 桁は JRA 開催場コード。
    """
    n = re.sub(r"\D", "", str(numeric_race_id or ""))
    if len(n) != 12:
        return None
    year, venue_code, kai, day, race = n[:4], n[4:6], n[6:8], n[8:10], int(n[10:12])
    if venue_code not in JRA_VENUE_CODE_TO_JA:
        return None
    return year, venue_code, f"{kai}{day}", race


def core_race_id_from_catalog(
    *,
    date: str,
    course: str,
    race_no: int,
    numeric_race_id: str = "",
    stored_core_race_id: str = "",
) -> tuple[str, str]:
    """
    Catalog 行 → (core_race_id, jra_venue_code)。

    優先順:
      1. 行に明示された core_race_id（既に Core 空間）
      2. numeric_race_id の JRA venue 桁
      3. course 名の JRA 公式マップ
    """
    stored = str(stored_core_race_id or "").strip()
    if stored:
        m = _CATALOG_ID_RE.match(stored)
        if m:
            return stored, m.group(2)
    parsed = parse_jra_numeric_id(numeric_race_id)
    if parsed:
        _year, venue_code, _kd, n_race = parsed
        race = int(race_no) if race_no else n_race
        return f"{date}-{venue_code}-{race:02d}", venue_code
    code = JRA_COURSE_TO_CODE.get(str(course or "").strip(), "")
    if code:
        return f"{date}-{code}-{int(race_no):02d}", code
    return "", ""


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


class CatalogIndex:
    """Catalog ID / numeric ID / (date, course, race_no) の索引。Core 空間とは別 dict。"""

    def __init__(self) -> None:
        self._by_catalog: dict[str, CatalogRace] = {}
        self._by_numeric: dict[str, CatalogRace] = {}
        self._by_date_course_race: dict[tuple[str, str, int], CatalogRace] = {}
        self._dates: set[str] = set()
        self._pi_attempted: set[str] = set()

    def add_row(self, payload: dict[str, Any]) -> CatalogRace | None:
        catalog_id = str(
            payload.get("catalog_id")
            or payload.get("catalog_race_id")
            or payload.get("race_id")
            or ""
        ).strip()
        date = str(payload.get("date") or payload.get("race_date") or "")[:10]
        course = str(
            payload.get("course") or payload.get("venue") or payload.get("venue_ja") or ""
        ).strip()
        race_no = _as_int(payload.get("race_no") or payload.get("race_number"))
        if not catalog_id or not date or not course or race_no is None:
            return None
        numeric = re.sub(r"\D", "", str(payload.get("numeric_race_id") or ""))
        core, jra_code = core_race_id_from_catalog(
            date=date,
            course=course,
            race_no=race_no,
            numeric_race_id=numeric,
            stored_core_race_id=str(payload.get("core_race_id") or ""),
        )
        label = ""
        m = _CATALOG_ID_RE.match(catalog_id)
        if m:
            label = m.group(2)
        row = CatalogRace(
            catalog_id=catalog_id,
            date=date,
            course=course,
            race_no=int(race_no),
            numeric_race_id=numeric,
            race_name=str(payload.get("race_name") or payload.get("class_label") or ""),
            core_race_id=core,
            jra_venue_code=jra_code,
            field_size=_as_int(payload.get("field_size") or payload.get("field") or payload.get("horse_count")),
            post_time=str(payload.get("post_time") or ""),
            label_no=label,
        )
        self._index_row(row)
        return row

    def _index_row(self, row: CatalogRace) -> None:
        self._by_catalog[row.catalog_id] = row
        if row.numeric_race_id:
            self._by_numeric[row.numeric_race_id] = row
        self._by_date_course_race[(row.date, row.course, row.race_no)] = row
        self._dates.add(row.date)

    def load_mapping(self, rows: Iterable[dict[str, Any]]) -> int:
        n = 0
        for payload in rows:
            if self.add_row(payload):
                n += 1
        return n

    def load_json(self, path: Path) -> int:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            rows = raw.get("races") or raw.get("items") or []
        else:
            rows = raw
        if not isinstance(rows, list):
            return 0
        return self.load_mapping(rows)

    def load_builtin_fixtures(self) -> int:
        if not _FIXTURE_DIR.is_dir():
            return 0
        total = 0
        for path in sorted(_FIXTURE_DIR.glob("*.json")):
            total += self.load_json(path)
        return total

    def has_date(self, date: str) -> bool:
        return str(date)[:10] in self._dates

    def lookup_catalog_id(self, catalog_id: str) -> CatalogRace | None:
        rid = str(catalog_id or "").strip()
        hit = self._by_catalog.get(rid)
        if hit:
            return hit
        m = _CATALOG_ID_RE.match(rid)
        if m:
            self.ensure_date(m.group(1))
            return self._by_catalog.get(rid)
        return None

    def lookup_numeric(self, numeric_race_id: str) -> CatalogRace | None:
        n = re.sub(r"\D", "", str(numeric_race_id or ""))
        if not n:
            return None
        return self._by_numeric.get(n)

    def lookup_date_course_race(self, date: str, course: str, race_no: int) -> CatalogRace | None:
        d = str(date)[:10]
        if d and not self.has_date(d):
            self.ensure_date(d)
        return self._by_date_course_race.get((d, str(course).strip(), int(race_no)))

    def lookup_any(self, raw: str) -> CatalogRace | None:
        text = str(raw or "").strip()
        if not text:
            return None
        hit = self.lookup_catalog_id(text)
        if hit:
            return hit
        if re.fullmatch(r"\d{12}", text):
            return self.lookup_numeric(text)
        return None

    def all_for_date(self, date: str) -> list[CatalogRace]:
        d = str(date)[:10]
        return sorted(
            (row for row in self._by_catalog.values() if row.date == d),
            key=lambda r: (r.label_no, r.race_no, r.catalog_id),
        )

    def ensure_date(self, date: str) -> None:
        d = str(date)[:10]
        if not d or self.has_date(d) or d in self._pi_attempted:
            return
        self._pi_attempted.add(d)
        rows = _fetch_pi_races(d)
        if rows:
            self.load_mapping(rows)


_shared_index: CatalogIndex | None = None


def _pi_base_url() -> str:
    if (os.environ.get("CATALOG_INDEX_DISABLE_PI") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return ""
    return (
        os.environ.get("PI_BASE_URL")
        or os.environ.get("EXPECT_PI_BASE_URL")
        or os.environ.get("EXPECT_PI_KEIBANET_URL")
        or ""
    ).strip().rstrip("/")


def _fetch_pi_races(date: str) -> list[dict[str, Any]]:
    base = _pi_base_url()
    if not base:
        return []
    url = f"{base}/v1/races?date={date}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return []
    if not isinstance(payload, dict):
        return []
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    races = (data or {}).get("races") if isinstance(data, dict) else None
    if not isinstance(races, list):
        return []
    return [r for r in races if isinstance(r, dict)]


def get_catalog_index() -> CatalogIndex:
    global _shared_index
    if _shared_index is None:
        idx = CatalogIndex()
        idx.load_builtin_fixtures()
        _shared_index = idx
    return _shared_index


def reset_catalog_index_for_tests(index: CatalogIndex | None = None) -> CatalogIndex:
    global _shared_index
    if index is None:
        index = CatalogIndex()
        index.load_builtin_fixtures()
    _shared_index = index
    return index
