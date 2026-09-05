# -*- coding: utf-8 -*-
"""
P1 ID namespace types.

Catalog / Numeric / Core / FeatureLookup は別空間。
YYYY-MM-DD-NN-NN の形から意味を推測してはならない。
CoreRaceRef を FeatureLoader lookup key にしてはならない。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_DOTTED_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(\d{2})-(\d{1,2})$")
_VENUE_QUALIFIED_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-([\u4e00-\u9fff]+)-(\d{1,2})$")
_SLUG_RE = re.compile(r"^(\d{8})_([a-z0-9]+)_(\d{1,2})$")
_NUMERIC_RE = re.compile(r"^\d{12}$")

# JRA 公式開催場コード。Catalog label_no とは別空間。
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


def _z2(value: int | str) -> str:
    return f"{int(value):02d}"


@dataclass(frozen=True)
class CatalogRaceRef:
    """Win5 / PI public identity. meeting_label はその日の開催順であり JRA venue ではない。"""

    date: str
    meeting_label: str
    race_no: int

    def as_id(self) -> str:
        return f"{self.date}-{_z2(self.meeting_label)}-{_z2(self.race_no)}"

    @classmethod
    def parse(cls, catalog_id: str) -> "CatalogRaceRef | None":
        m = _DOTTED_RE.fullmatch(str(catalog_id or "").strip())
        if not m:
            return None
        return cls(date=m.group(1), meeting_label=m.group(2), race_no=int(m.group(3)))


@dataclass(frozen=True)
class NumericRaceRef:
    """JRA 12桁: YYYY + venue(2) + kai(2) + day(2) + race(2). 物理正本。"""

    numeric_race_id: str

    def as_id(self) -> str:
        return self.numeric_race_id

    @property
    def jra_venue_code(self) -> str:
        return self.numeric_race_id[4:6]

    @property
    def race_no(self) -> int:
        return int(self.numeric_race_id[10:12])

    @classmethod
    def parse(cls, numeric_race_id: str) -> "NumericRaceRef | None":
        n = re.sub(r"\D", "", str(numeric_race_id or ""))
        if not _NUMERIC_RE.fullmatch(n):
            return None
        if n[4:6] not in JRA_VENUE_CODE_TO_JA:
            return None
        return cls(numeric_race_id=n)


@dataclass(frozen=True)
class CoreRaceRef:
    """JRA venue 桁の Core identity。Feature CSV のキーではない。"""

    date: str
    jra_venue_code: str
    race_no: int

    def as_id(self) -> str:
        return f"{self.date}-{_z2(self.jra_venue_code)}-{_z2(self.race_no)}"

    @classmethod
    def parse(cls, core_id: str) -> "CoreRaceRef | None":
        m = _DOTTED_RE.fullmatch(str(core_id or "").strip())
        if not m:
            return None
        return cls(date=m.group(1), jra_venue_code=m.group(2), race_no=int(m.group(3)))

    @classmethod
    def from_catalog_row(
        cls,
        *,
        date: str,
        course: str,
        race_no: int,
        numeric_race_id: str = "",
    ) -> "CoreRaceRef | None":
        numeric = NumericRaceRef.parse(numeric_race_id)
        if numeric:
            return cls(date=date, jra_venue_code=numeric.jra_venue_code, race_no=int(race_no))
        code = JRA_COURSE_TO_CODE.get(str(course or "").strip(), "")
        if not code:
            return None
        return cls(date=date, jra_venue_code=code, race_no=int(race_no))


@dataclass(frozen=True)
class FeatureLookupRef:
    """
    FeatureLoader / daily CSV の race_id 列。

    Production PI refresh は Catalog/Win5 ID を書く。
    Catalog 行があるときは Catalog ID。
    Catalog が無い legacy Core 入力だけ、入力 Core 文字列をそのまま使う。
    CoreRaceRef（JRA venue 形）をここに入れてはならない。
    """

    key: str
    source: str

    def as_id(self) -> str:
        return self.key

    @classmethod
    def from_catalog(cls, catalog_id: str) -> "FeatureLookupRef":
        return cls(key=str(catalog_id).strip(), source="catalog")

    @classmethod
    def from_legacy_core(cls, core_id: str) -> "FeatureLookupRef":
        return cls(key=str(core_id).strip(), source="legacy_core")


@dataclass(frozen=True)
class VenueQualifiedRaceRef:
    date: str
    venue_name: str
    race_no: int

    def as_id(self) -> str:
        return f"{self.date}-{self.venue_name}-{int(self.race_no)}"

    @classmethod
    def parse(cls, text: str) -> "VenueQualifiedRaceRef | None":
        m = _VENUE_QUALIFIED_RE.fullmatch(str(text or "").strip())
        if not m:
            return None
        return cls(date=m.group(1), venue_name=m.group(2), race_no=int(m.group(3)))


def looks_like_dotted_id(text: str) -> bool:
    return bool(_DOTTED_RE.fullmatch(str(text or "").strip()))


def looks_like_numeric_id(text: str) -> bool:
    return bool(_NUMERIC_RE.fullmatch(re.sub(r"\D", "", str(text or ""))))


def looks_like_slug(text: str) -> bool:
    return bool(_SLUG_RE.fullmatch(str(text or "").strip().lower()))


def matches_feature_lookup(
    *,
    race_id: str,
    lookup_key: str,
    numeric_race_id: str = "",
    extra_numeric: str = "",
) -> bool:
    """CSV 行が FeatureLookupRef に当たるか。CoreRaceRef 文字列では当てない。"""
    key = str(lookup_key or "").strip()
    if key and str(race_id or "").strip() == key:
        return True
    numeric = re.sub(r"\D", "", str(numeric_race_id or ""))
    extra = re.sub(r"\D", "", str(extra_numeric or ""))
    if extra and numeric == extra:
        return True
    return False


__all__ = [
    "CatalogRaceRef",
    "NumericRaceRef",
    "CoreRaceRef",
    "FeatureLookupRef",
    "VenueQualifiedRaceRef",
    "JRA_VENUE_CODE_TO_JA",
    "JRA_COURSE_TO_CODE",
    "looks_like_dotted_id",
    "looks_like_numeric_id",
    "looks_like_slug",
    "matches_feature_lookup",
]
