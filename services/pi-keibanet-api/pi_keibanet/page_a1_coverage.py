# -*- coding: utf-8 -*-
"""PAGE-A1 source-declared venue/race coverage (completeness evidence).

Extracts inventory from RAW HTML structure independently of canonical listed rows,
then compares. No fixed race-count thresholds (12/24/36 forbidden).
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from .netkeiba.parse import (
    _RACE_ID_RE,
    _SP_MAIN_BOX_RE,
    _TITLE_RE,
    _VENUE_BLOCK_RE,
    _LIST_ITEM_RE,
    _normalize,
    _sp_active_day_html,
)
from .venues import COURSE_CODE_TO_NAME, COURSE_NAME_TO_CODE

# Markers that a response is a recognizable race_list page (incl. empty day).
_RACE_LIST_PAGE_MARKERS = (
    "RaceList_DataList",
    "RaceListDayWrap",
    "RaceList_Main_Box",
    "pid=race_list",
    "RaceList_DataTitle",
)


@dataclass
class SourceRaceDecl:
    race_id: str
    venue: str
    race_number: int | None
    part: str


@dataclass
class SourceInventory:
    known: bool
    venues: set[str] = field(default_factory=set)
    race_ids: set[str] = field(default_factory=set)
    races: list[SourceRaceDecl] = field(default_factory=list)
    duplicate_race_ids: list[str] = field(default_factory=list)
    page_recognized: bool = False
    reason: str = ""
    part: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "known": self.known,
            "venues": sorted(self.venues),
            "race_ids": sorted(self.race_ids),
            "race_count": len(self.race_ids),
            "duplicate_race_ids": list(self.duplicate_race_ids),
            "page_recognized": self.page_recognized,
            "reason": self.reason,
            "part": self.part,
            "races": [asdict(r) for r in self.races],
        }


@dataclass
class CoverageResult:
    venue_coverage_pass: bool
    race_coverage_pass: bool
    inventory_known: bool
    page_recognized: bool
    conflicts: list[str] = field(default_factory=list)
    missing_venues: list[str] = field(default_factory=list)
    extra_venues: list[str] = field(default_factory=list)
    missing_race_ids: list[str] = field(default_factory=list)
    extra_race_ids: list[str] = field(default_factory=list)
    duplicate_race_ids: list[str] = field(default_factory=list)
    venue_race_number_conflicts: list[dict[str, Any]] = field(default_factory=list)
    source_declared_venues: list[str] = field(default_factory=list)
    source_declared_race_ids: list[str] = field(default_factory=list)
    canonical_venues: list[str] = field(default_factory=list)
    canonical_race_ids: list[str] = field(default_factory=list)
    non_race_source_ok: bool = False
    reason: str = ""

    @property
    def coverage_pass(self) -> bool:
        return (
            self.inventory_known
            and self.venue_coverage_pass
            and self.race_coverage_pass
            and not self.conflicts
            and not self.duplicate_race_ids
            and not self.venue_race_number_conflicts
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["coverage_pass"] = self.coverage_pass
        return d


def _page_recognized(html: str) -> bool:
    h = html or ""
    return any(m in h for m in _RACE_LIST_PAGE_MARKERS)


def extract_source_inventory_pc(html: str, *, part: str = "race_list_sub") -> SourceInventory:
    """Structural inventory from PC RaceList_DataList blocks."""
    inv = SourceInventory(known=False, part=part, page_recognized=_page_recognized(html))
    if not inv.page_recognized:
        inv.reason = "pc_page_not_recognized"
        return inv

    blocks = _VENUE_BLOCK_RE.findall(html or "")
    seen_ids: set[str] = set()
    dup: set[str] = set()
    races: list[SourceRaceDecl] = []
    venues: set[str] = set()

    if not blocks:
        # Recognizable page with zero venue blocks → valid empty candidate
        inv.known = True
        inv.reason = "pc_zero_venue_blocks"
        return inv

    for block in blocks:
        m_title = _TITLE_RE.search(block)
        if not m_title:
            inv.known = False
            inv.reason = "pc_venue_block_missing_title"
            return inv
        venue = _normalize(m_title.group(2))
        if venue not in COURSE_NAME_TO_CODE:
            inv.known = False
            inv.reason = f"pc_unknown_venue:{venue}"
            return inv
        venues.add(venue)
        for item in _LIST_ITEM_RE.findall(block):
            m_id = _RACE_ID_RE.search(item)
            if not m_id:
                continue
            rid = m_id.group(1)
            m_num = re.search(r"Race_Num[\s\S]*?(\d+)\s*R", item, re.I)
            num = int(m_num.group(1)) if m_num else None
            if rid in seen_ids:
                dup.add(rid)
            seen_ids.add(rid)
            races.append(SourceRaceDecl(race_id=rid, venue=venue, race_number=num, part=part))

    inv.known = True
    inv.venues = venues
    inv.race_ids = set(seen_ids)
    inv.races = races
    inv.duplicate_race_ids = sorted(dup)
    inv.reason = "pc_ok"
    return inv


def extract_source_inventory_sp(html: str, *, part: str = "race_list_sp") -> SourceInventory:
    """Structural inventory from SP active-day RaceList_Main_Box blocks."""
    inv = SourceInventory(known=False, part=part, page_recognized=_page_recognized(html))
    if not inv.page_recognized:
        inv.reason = "sp_page_not_recognized"
        return inv

    day_html = _sp_active_day_html(html or "")
    boxes = _SP_MAIN_BOX_RE.findall(day_html)
    seen_ids: set[str] = set()
    dup: set[str] = set()
    races: list[SourceRaceDecl] = []
    venues: set[str] = set()

    if not boxes:
        inv.known = True
        inv.reason = "sp_zero_main_boxes"
        return inv

    for box in boxes:
        m_id = _RACE_ID_RE.search(box)
        if not m_id:
            continue
        rid = m_id.group(1)
        code = rid[4:6]
        venue = COURSE_CODE_TO_NAME.get(code)
        if not venue:
            inv.known = False
            inv.reason = f"sp_unknown_venue_code:{code}"
            return inv
        venues.add(venue)
        m_num = re.search(r"Race_Num[^>]*>\s*<span>\s*(\d+)\s*R\s*</span>", box, re.I)
        num = int(m_num.group(1)) if m_num else None
        if rid in seen_ids:
            dup.add(rid)
        seen_ids.add(rid)
        races.append(SourceRaceDecl(race_id=rid, venue=venue, race_number=num, part=part))

    inv.known = True
    inv.venues = venues
    inv.race_ids = set(seen_ids)
    inv.races = races
    inv.duplicate_race_ids = sorted(dup)
    inv.reason = "sp_ok"
    return inv


def extract_source_inventory_from_parts(
    parts: Iterable[Any],
) -> tuple[SourceInventory, dict[str, Any]]:
    """
    Build source inventory from fetch parts (sub/sp).
    Prefer SP when present; if both present, require venue/race-id set agreement.
    """
    by_source: dict[str, Any] = {}
    inventories: dict[str, SourceInventory] = {}
    for part in parts:
        src = getattr(part, "source", "") or ""
        html = getattr(part, "html", "") or ""
        by_source[src] = True
        if src == "race_list_sp" or src.endswith("_sp"):
            inventories["sp"] = extract_source_inventory_sp(html, part=src)
        elif src == "race_list_sub" or src.endswith("_sub"):
            inventories["sub"] = extract_source_inventory_pc(html, part=src)

    meta: dict[str, Any] = {
        "parts_present": sorted(by_source.keys()),
        "inventories": {k: v.to_dict() for k, v in inventories.items()},
    }

    if not inventories:
        unk = SourceInventory(known=False, reason="no_sub_or_sp_parts", page_recognized=False)
        return unk, meta

    if "sp" in inventories and "sub" in inventories:
        sp, sub = inventories["sp"], inventories["sub"]
        if not sp.known or not sub.known:
            unk = SourceInventory(
                known=False,
                page_recognized=sp.page_recognized or sub.page_recognized,
                reason="part_inventory_unknown",
            )
            return unk, meta
        if sp.venues != sub.venues:
            unk = SourceInventory(
                known=False,
                page_recognized=True,
                reason="sub_sp_venue_mismatch",
                venues=sp.venues | sub.venues,
                race_ids=sp.race_ids | sub.race_ids,
            )
            meta["venue_mismatch"] = {
                "sp": sorted(sp.venues),
                "sub": sorted(sub.venues),
            }
            return unk, meta
        if sp.race_ids != sub.race_ids:
            unk = SourceInventory(
                known=False,
                page_recognized=True,
                reason="sub_sp_race_id_mismatch",
                venues=sp.venues,
                race_ids=sp.race_ids | sub.race_ids,
            )
            meta["race_id_mismatch"] = {
                "only_sp": sorted(sp.race_ids - sub.race_ids),
                "only_sub": sorted(sub.race_ids - sp.race_ids),
            }
            return unk, meta
        # Prefer SP race rows (richer names not needed for coverage ids)
        out = SourceInventory(
            known=True,
            venues=set(sp.venues),
            race_ids=set(sp.race_ids),
            races=list(sp.races),
            duplicate_race_ids=sorted(set(sp.duplicate_race_ids) | set(sub.duplicate_race_ids)),
            page_recognized=True,
            reason="sub_sp_agree",
            part="race_list_sp+sub",
        )
        return out, meta

    key = "sp" if "sp" in inventories else "sub"
    return inventories[key], meta


def evaluate_coverage(
    inventory: SourceInventory,
    *,
    canonical_listed: list[Any],
    meetings: list[Any] | None = None,
) -> CoverageResult:
    """Compare source-declared inventory to canonical listed (+ optional meetings)."""
    canon_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    dups: list[str] = []
    for r in canonical_listed or []:
        if isinstance(r, dict):
            rid = str(r.get("race_id") or "")
            venue = str(r.get("venue") or "")
            num = r.get("race_number")
            if num is None:
                num = r.get("race_no")
        else:
            rid = str(getattr(r, "race_id", "") or "")
            venue = str(getattr(r, "venue", "") or "")
            num = getattr(r, "race_no", None)
        if not rid:
            continue
        if rid in seen:
            dups.append(rid)
        seen.add(rid)
        canon_rows.append({"race_id": rid, "venue": venue, "race_number": num})

    canon_ids = {r["race_id"] for r in canon_rows}
    canon_venues = {r["venue"] for r in canon_rows if r["venue"]}

    meeting_venues = {
        (getattr(m, "venue", None) or (m.get("venue") if isinstance(m, dict) else "") or "")
        for m in (meetings or [])
    }
    meeting_venues.discard("")

    result = CoverageResult(
        venue_coverage_pass=False,
        race_coverage_pass=False,
        inventory_known=inventory.known,
        page_recognized=inventory.page_recognized,
        duplicate_race_ids=sorted(set(inventory.duplicate_race_ids) | set(dups)),
        source_declared_venues=sorted(inventory.venues),
        source_declared_race_ids=sorted(inventory.race_ids),
        canonical_venues=sorted(canon_venues),
        canonical_race_ids=sorted(canon_ids),
    )

    if not inventory.known:
        result.conflicts.append(f"inventory_unknown:{inventory.reason}")
        result.reason = inventory.reason or "inventory_unknown"
        return result

    # Venue coverage
    missing_v = sorted(inventory.venues - canon_venues)
    extra_v = sorted(canon_venues - inventory.venues)
    result.missing_venues = missing_v
    result.extra_venues = extra_v
    result.venue_coverage_pass = not missing_v and not extra_v

    if meeting_venues and meeting_venues != inventory.venues:
        result.conflicts.append("meeting_venues_mismatch_source")
        result.conflicts.append(
            f"meetings={sorted(meeting_venues)} source={sorted(inventory.venues)}"
        )

    # Race coverage
    missing_r = sorted(inventory.race_ids - canon_ids)
    extra_r = sorted(canon_ids - inventory.race_ids)
    result.missing_race_ids = missing_r
    result.extra_race_ids = extra_r
    result.race_coverage_pass = not missing_r and not extra_r

    # Per-id venue / race_number conflict vs source decls
    src_by_id = {r.race_id: r for r in inventory.races}
    for row in canon_rows:
        src = src_by_id.get(row["race_id"])
        if not src:
            continue
        if src.venue and row["venue"] and src.venue != row["venue"]:
            result.venue_race_number_conflicts.append(
                {
                    "race_id": row["race_id"],
                    "field": "venue",
                    "source": src.venue,
                    "canonical": row["venue"],
                }
            )
        if (
            src.race_number is not None
            and row["race_number"] is not None
            and int(src.race_number) != int(row["race_number"])
        ):
            result.venue_race_number_conflicts.append(
                {
                    "race_id": row["race_id"],
                    "field": "race_number",
                    "source": src.race_number,
                    "canonical": row["race_number"],
                }
            )

    # Valid non-race: recognized page, known inventory, zero source venues & races
    result.non_race_source_ok = (
        inventory.known
        and inventory.page_recognized
        and not inventory.venues
        and not inventory.race_ids
        and not canon_ids
    )

    if result.coverage_pass:
        result.reason = "coverage_ok"
    elif result.non_race_source_ok:
        result.reason = "valid_empty_non_race"
        # empty coverage is a pass for non-race path
        result.venue_coverage_pass = True
        result.race_coverage_pass = True
    else:
        result.reason = "coverage_fail"
    return result


def http_parts_ok(parts: Iterable[Any]) -> tuple[bool, dict[str, Any]]:
    """At least one of race_list_sub / race_list_sp with non-empty body."""
    present = []
    for p in parts or []:
        src = getattr(p, "source", "") or ""
        html = getattr(p, "html", "") or ""
        if src in ("race_list_sub", "race_list_sp") and html.strip():
            present.append(src)
    ok = bool(present)
    return ok, {"usable_parts": present, "parts_ok": ok}
