# -*- coding: utf-8 -*-
"""PAGE-A1 persistence + kaisai-day index (C1/C2/C3). Fail-open; zero extra HTTP."""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from .netkeiba.client import RaceListFetchResult
from .page_a1_coverage import (
    evaluate_coverage,
    extract_source_inventory_from_parts,
    http_parts_ok,
)

JST = ZoneInfo("Asia/Tokyo")

# Seal string for parse contract used with PAGE-A1 listed extraction.
PARSER_VERSION = "page_a1_parse_v2_coverage"

LogFn = Callable[[str], None]


@dataclass
class PageA1PersistResult:
    attempted: bool = False
    raw_snapshots_added: int = 0
    raw_snapshots_deduped: int = 0
    listed_race_count: int = 0
    lifecycle_state: str = ""
    completeness_state: str = ""
    day_kind: str = "UNKNOWN"  # RACE_DAY | NON_RACE_DAY | UNKNOWN
    warning_count: int = 0
    warnings: list[str] = field(default_factory=list)
    index_path: str = ""
    listed_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def now_jst() -> datetime:
    return datetime.now(JST)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def page_a1_dir(state_root: Path, kaisai_date: str) -> Path:
    return state_root / kaisai_date / "page_a1"


def index_path(state_root: Path, kaisai_date: str) -> Path:
    return state_root / kaisai_date / "kaisai_day_index.json"


def listed_path(state_root: Path, kaisai_date: str) -> Path:
    return page_a1_dir(state_root, kaisai_date) / "listed_races.json"


def atomic_write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)


def load_index(state_root: Path, kaisai_date: str) -> dict[str, Any] | None:
    path = index_path(state_root, kaisai_date)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _warn(result: PageA1PersistResult, log: LogFn, msg: str) -> None:
    result.warning_count += 1
    result.warnings.append(msg)
    log(f"[page-a1] WARNING: {msg}")


def _meeting_dicts(meetings: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in meetings:
        out.append(
            {
                "venue": getattr(m, "venue", "") or "",
                "venue_code": getattr(m, "venue_code", "") or "",
                "kai": getattr(m, "kai", "") or "",
                "day": getattr(m, "day", "") or "",
            }
        )
    return out


def _listed_race_dicts(
    listed: list[Any],
    *,
    listed_at: str,
    raw_refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """PAGE-A1 listed inventory only — must never imply shutuba/published success."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in listed:
        rid = str(getattr(r, "race_id", "") or "")
        if not rid or rid in seen:
            continue
        seen.add(rid)
        rows.append(
            {
                "race_id": rid,
                "race_name": getattr(r, "race_name", "") or "",
                "venue": getattr(r, "venue", "") or "",
                "race_number": int(getattr(r, "race_no", 0) or 0),
                "post_time": getattr(r, "post_time", "") or "",
                "listed_at": listed_at,
                "source": "netkeiba_page_a1",
                "raw_snapshot_refs": list(raw_refs),
                # Explicit: not published / not shutuba-ok
                "listed_not_published": True,
            }
        )
    rows.sort(key=lambda x: (x["venue"], x["race_number"], x["race_id"]))
    return rows


def _decide_completeness(
    *,
    fetch_ok: bool,
    raw_persisted: bool,
    parse_ok: bool,
    parts_n: int,
    parts_ok: bool = False,
    coverage: Any | None = None,
) -> tuple[str, dict[str, Any]]:
    """COMPLETE only with source-declared venue/race coverage PASS.

    Forbidden: race_count thresholds (12/24/36), past_date heuristics.
    UNKNOWN coverage → never COMPLETE.
    """
    cov = coverage
    evidence: dict[str, Any] = {
        "fetch_ok": fetch_ok,
        "raw_persisted": raw_persisted,
        "parse_ok": parse_ok,
        "source_parts_n": parts_n,
        "parts_ok": parts_ok,
        "forbidden_heuristics_not_used": [
            "race_count_12",
            "race_count_24",
            "race_count_36",
            "past_date",
            "prediction_success",
            "race_id_exists_alone",
        ],
    }
    if cov is not None:
        evidence["coverage"] = cov.to_dict() if hasattr(cov, "to_dict") else cov

    if not fetch_ok:
        return "INVALID", evidence
    if not raw_persisted:
        return "PARTIAL", evidence
    if not parts_ok:
        evidence["non_complete_reason"] = "expected_http_parts_missing"
        return "PARTIAL", evidence
    if not parse_ok:
        return "PARTIAL", evidence
    if cov is None:
        evidence["non_complete_reason"] = "coverage_unknown"
        return "PARTIAL", evidence
    if not getattr(cov, "inventory_known", False):
        evidence["non_complete_reason"] = "source_inventory_unknown"
        return "PARTIAL", evidence
    if getattr(cov, "duplicate_race_ids", None):
        evidence["non_complete_reason"] = "duplicate_race_id"
        return "PARTIAL", evidence
    if getattr(cov, "venue_race_number_conflicts", None):
        evidence["non_complete_reason"] = "venue_or_race_number_conflict"
        return "PARTIAL", evidence
    if getattr(cov, "conflicts", None):
        evidence["non_complete_reason"] = "coverage_conflict"
        return "PARTIAL", evidence
    # Valid empty non-race: coverage marks non_race_source_ok
    if getattr(cov, "non_race_source_ok", False):
        evidence["non_complete_reason"] = None
        evidence["valid_empty"] = True
        return "COMPLETE", evidence
    if not getattr(cov, "venue_coverage_pass", False):
        evidence["non_complete_reason"] = "venue_coverage_fail"
        return "PARTIAL", evidence
    if not getattr(cov, "race_coverage_pass", False):
        evidence["non_complete_reason"] = "race_coverage_fail"
        return "PARTIAL", evidence
    if not getattr(cov, "coverage_pass", False):
        evidence["non_complete_reason"] = "coverage_fail"
        return "PARTIAL", evidence
    evidence["non_complete_reason"] = None
    return "COMPLETE", evidence


def persist_page_a1_after_fetch(
    *,
    state_root: Path,
    kaisai_date: str,
    fetch_result: RaceListFetchResult,
    meetings: list[Any] | None = None,
    listed: list[Any] | None = None,
    parse_ok: bool = True,
    parse_error: str | None = None,
    lifecycle_force: str | None = None,
    logger: LogFn | None = None,
) -> PageA1PersistResult:
    """
    C1/C2: persist RAW + listed_races + kaisai_day_index.
    Fail-open: never raises to caller for I/O failures.
    """
    log = logger or print
    result = PageA1PersistResult(attempted=True)
    fetched_at = now_jst().isoformat()
    raw_refs: list[dict[str, Any]] = []
    latest_hash = ""

    try:
        base = page_a1_dir(state_root, kaisai_date)
        raw_dir = base / "raw"
        meta_dir = base / "meta"
        raw_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _warn(result, log, f"mkdir_failed: {exc}")
        result.lifecycle_state = "LIVE"
        result.completeness_state = "PARTIAL"
        return result

    # Persist per-part RAW (hash-dedupe)
    for part in fetch_result.parts:
        try:
            h = content_hash(part.html)
            latest_hash = h
            fname = f"{h[:16]}_{part.source}.html"
            path = raw_dir / fname
            meta_name = f"{h[:16]}_{part.source}.json"
            meta_p = meta_dir / meta_name
            if path.is_file():
                result.raw_snapshots_deduped += 1
            else:
                atomic_write_text(path, part.html)
                result.raw_snapshots_added += 1
            meta = {
                "fetched_at": fetched_at,
                "kaisai_date": kaisai_date,
                "source": part.source,
                "request_identity": {"url": part.url, "method": "GET"},
                "content_hash": h,
                "html_bytes": len(part.html.encode("utf-8")),
                "parser_version": PARSER_VERSION,
                "raw_path": str(path.relative_to(state_root)).replace("\\", "/"),
            }
            if not meta_p.is_file():
                atomic_write_json(meta_p, meta)
            raw_refs.append(
                {
                    "source": part.source,
                    "content_hash": h,
                    "path": meta["raw_path"],
                }
            )
        except OSError as exc:
            _warn(result, log, f"raw_write_failed source={part.source}: {exc}")

    # Also persist merged body once (discover-visible response)
    try:
        merged = fetch_result.merged_html or ""
        if merged:
            mh = content_hash(merged)
            latest_hash = mh
            mpath = raw_dir / f"{mh[:16]}_merged.html"
            if mpath.is_file():
                result.raw_snapshots_deduped += 1
            else:
                atomic_write_text(mpath, merged)
                result.raw_snapshots_added += 1
            raw_refs.append(
                {
                    "source": "race_list_merged",
                    "content_hash": mh,
                    "path": str(mpath.relative_to(state_root)).replace("\\", "/"),
                }
            )
            atomic_write_json(
                meta_dir / f"{mh[:16]}_merged.json",
                {
                    "fetched_at": fetched_at,
                    "kaisai_date": kaisai_date,
                    "source": "race_list_merged",
                    "request_identity": {
                        "parts": [
                            {"source": p.source, "url": p.url} for p in fetch_result.parts
                        ]
                    },
                    "content_hash": mh,
                    "html_bytes": len(merged.encode("utf-8")),
                    "parser_version": PARSER_VERSION,
                    "raw_path": str(mpath.relative_to(state_root)).replace("\\", "/"),
                },
            )
    except OSError as exc:
        _warn(result, log, f"merged_raw_write_failed: {exc}")

    raw_persisted = any(
        (state_root / r["path"]).is_file() for r in raw_refs if r.get("path")
    )

    meetings = meetings or []
    listed = listed or []
    if parse_error:
        parse_ok = False

    parts_ok, parts_meta = http_parts_ok(fetch_result.parts)
    inventory, inv_meta = extract_source_inventory_from_parts(fetch_result.parts)
    coverage = evaluate_coverage(inventory, canonical_listed=listed, meetings=meetings)

    completeness, evidence = _decide_completeness(
        fetch_ok=True,
        raw_persisted=raw_persisted,
        parse_ok=parse_ok,
        parts_n=len(fetch_result.parts),
        parts_ok=parts_ok,
        coverage=coverage,
    )
    evidence["parts_meta"] = parts_meta
    evidence["source_inventory_meta"] = inv_meta
    evidence["source_inventory"] = inventory.to_dict()
    if parse_error:
        evidence["parse_error"] = parse_error

    listed_rows = _listed_race_dicts(listed, listed_at=fetched_at, raw_refs=raw_refs)
    result.listed_race_count = len(listed_rows)
    race_ids = sorted({r["race_id"] for r in listed_rows})

    # Additive day_kind (FINAL != COMPLETE; RACE vs NON_RACE separate from completeness)
    # NON_RACE only when COMPLETE + source-valid empty (not parse-zero alone).
    if completeness == "COMPLETE" and coverage.non_race_source_ok:
        day_kind = "NON_RACE_DAY"
    elif parse_ok and completeness == "COMPLETE" and len(race_ids) >= 1:
        day_kind = "RACE_DAY"
    elif parse_ok and len(race_ids) >= 1:
        day_kind = "RACE_DAY"
    else:
        day_kind = "UNKNOWN"
    result.day_kind = day_kind

    listed_payload = {
        "kaisai_date": kaisai_date,
        "listed_at": fetched_at,
        "source": "netkeiba_page_a1",
        "parser_version": PARSER_VERSION,
        "note": "listed != published; shutuba success not implied",
        "race_count": len(listed_rows),
        "day_kind": day_kind,
        "races": listed_rows,
    }
    try:
        lp = listed_path(state_root, kaisai_date)
        atomic_write_json(lp, listed_payload)
        result.listed_path = str(lp)
    except OSError as exc:
        _warn(result, log, f"listed_races_write_failed: {exc}")
        completeness = "PARTIAL"
        evidence["listed_write_ok"] = False
    else:
        evidence["listed_write_ok"] = True

    prev = load_index(state_root, kaisai_date) or {}
    first_seen = prev.get("first_seen_at") or fetched_at
    lifecycle = prev.get("lifecycle_state") or "LIVE"
    if lifecycle not in ("LIVE", "FINAL"):
        lifecycle = "LIVE"
    if lifecycle_force in ("LIVE", "FINAL"):
        lifecycle = lifecycle_force

    # Do not demote day_kind from RACE_DAY / NON_RACE_DAY to UNKNOWN on weaker later writes
    prev_kind = prev.get("day_kind") or "UNKNOWN"
    if prev_kind in ("RACE_DAY", "NON_RACE_DAY") and day_kind == "UNKNOWN":
        day_kind = prev_kind
        result.day_kind = day_kind

    index = {
        "kaisai_date": kaisai_date,
        "lifecycle_state": lifecycle,
        "completeness_state": completeness,
        "day_kind": day_kind,
        "source": "netkeiba_page_a1",
        "first_seen_at": first_seen,
        "last_seen_at": fetched_at,
        "finalised_at": prev.get("finalised_at") or None,
        "meetings": _meeting_dicts(meetings),
        "meeting_count": len(meetings),
        "listed_race_ids": race_ids,
        "race_count": len(race_ids),
        "completeness_evidence": evidence,
        "parser_version": PARSER_VERSION,
        "raw_snapshot_refs": raw_refs,
        "latest_content_hash": latest_hash,
        "recovery_status": "known" if completeness in ("COMPLETE", "PARTIAL") else "unknown",
    }
    # Preserve FINAL if already finalised; do not demote unless force FINAL
    if prev.get("lifecycle_state") == "FINAL" and lifecycle_force != "LIVE":
        index["lifecycle_state"] = "FINAL"
        index["finalised_at"] = prev.get("finalised_at") or fetched_at
    if lifecycle == "FINAL" and not index.get("finalised_at"):
        index["finalised_at"] = fetched_at

    try:
        ip = index_path(state_root, kaisai_date)
        atomic_write_json(ip, index)
        result.index_path = str(ip)
    except OSError as exc:
        _warn(result, log, f"kaisai_day_index_write_failed: {exc}")

    result.lifecycle_state = index["lifecycle_state"]
    result.completeness_state = index["completeness_state"]
    log(
        "[page-a1] "
        f"kaisai_date={kaisai_date} attempted=1 "
        f"raw_added={result.raw_snapshots_added} raw_deduped={result.raw_snapshots_deduped} "
        f"listed_race_count={result.listed_race_count} day_kind={result.day_kind} "
        f"lifecycle={result.lifecycle_state} completeness={result.completeness_state} "
        f"warnings={result.warning_count}"
    )
    return result


_DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def promote_past_live_to_final(
    *,
    state_root: Path,
    today: str,
    logger: LogFn | None = None,
) -> list[dict[str, Any]]:
    """
    C3: for each day dir with kaisai_date < today and lifecycle LIVE,
    set FINAL without refetch and without changing completeness_state.
    """
    log = logger or print
    promoted: list[dict[str, Any]] = []
    if not state_root.is_dir():
        return promoted
    now = now_jst().isoformat()
    try:
        day_dirs = sorted(p for p in state_root.iterdir() if p.is_dir() and _DATE_DIR_RE.match(p.name))
    except OSError as exc:
        log(f"[page-a1] WARNING: FINAL scan failed: {exc}")
        return promoted

    for day in day_dirs:
        kaisai_date = day.name
        if kaisai_date >= today:
            continue
        idx = load_index(state_root, kaisai_date)
        if not idx:
            continue
        if idx.get("lifecycle_state") != "LIVE":
            continue
        # lifecycle only — never upgrade completeness
        idx["lifecycle_state"] = "FINAL"
        idx["finalised_at"] = now
        try:
            atomic_write_json(index_path(state_root, kaisai_date), idx)
            promoted.append(
                {
                    "kaisai_date": kaisai_date,
                    "lifecycle_state": "FINAL",
                    "completeness_state": idx.get("completeness_state"),
                }
            )
            log(
                f"[page-a1] FINALISE kaisai_date={kaisai_date} "
                f"completeness={idx.get('completeness_state')} (unchanged)"
            )
        except OSError as exc:
            log(f"[page-a1] WARNING: FINALISE failed {kaisai_date}: {exc}")
    return promoted


__all__ = [
    "PARSER_VERSION",
    "PageA1PersistResult",
    "atomic_write_json",
    "content_hash",
    "index_path",
    "listed_path",
    "load_index",
    "persist_page_a1_after_fetch",
    "promote_past_live_to_final",
]
