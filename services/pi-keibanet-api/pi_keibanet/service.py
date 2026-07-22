# -*- coding: utf-8 -*-
"""Resolve race + build Collector / Web GUI JSON payloads."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from .venues import COURSE_NAME_TO_CODE, collector_race_id
from .race_catalog import (
    assign_venue_label_nos,
    build_race_summary,
    group_races_by_course,
    make_win5_race_id,
    parse_race_id_ref,
    race_label,
)
from .netkeiba.client import NetkeibaClient, NetkeibaFetchError
from .netkeiba.parse import (
    find_numeric_race_id,
    parse_entries_from_shutuba,
    parse_list_races_from_race_list,
    parse_meetings_from_race_list,
    parse_odds_from_entries,
    parse_race_meta_from_shutuba,
    parse_track_condition,
    shutuba_has_race,
)
from .netkeiba.horse_history import (
    build_history_rows,
    fetch_horse_history,
)


class RaceNotFoundError(LookupError):
    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message


def _resolve_ai_platform_root() -> Path | None:
    for key in ("PI_AI_PLATFORM_ROOT", "AI_PLATFORM_ROOT"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            root = Path(raw)
            if root.is_dir():
                return root
    for candidate in (Path(r"C:\win5-ai"), Path("/opt/expect-ai/platform")):
        if candidate.is_dir():
            return candidate
    return None


def _resolve_prediction_data_root() -> Path | None:
    for key in ("PI_DATA_ROOT", "EXPECT_AI_DATA_ROOT"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            root = Path(raw)
            if root.is_dir():
                return root
    platform_root = _resolve_ai_platform_root()
    if platform_root is not None:
        data = platform_root / "data"
        if data.is_dir():
            return data
    win_data = Path(r"C:\win5-ai\data")
    if win_data.is_dir():
        return win_data
    return None


class PiKeibaNetService:
    def __init__(self, client: NetkeibaClient | None = None) -> None:
        self.client = client or NetkeibaClient()

    def resolve(self, *, date: str, venue: str, race_no: int) -> tuple[str, str]:
        if venue not in COURSE_NAME_TO_CODE:
            raise RaceNotFoundError(
                "venue_name_mismatch",
                f"unknown venue: {venue!r}",
            )

        list_html = self.client.fetch_race_list(date)
        numeric = find_numeric_race_id(list_html, date=date, venue=venue, race_no=race_no)
        if not numeric:
            listed = parse_list_races_from_race_list(list_html)
            meetings = parse_meetings_from_race_list(list_html)
            raise RaceNotFoundError(
                "race_no_mismatch",
                (
                    f"race_id not resolved: date={date} venue={venue} race_no={race_no}; "
                    f"listed_races={len(listed)} meetings={[(m.venue, m.kai, m.day) for m in meetings]}"
                ),
            )

        shutuba_html = self.client.fetch_shutuba(numeric)
        if not shutuba_has_race(shutuba_html):
            raise RaceNotFoundError(
                "shutuba_empty",
                f"shutuba has no race content: race_id={numeric} date={date} venue={venue} race_no={race_no}",
            )
        return numeric, shutuba_html

    def list_races(self, *, date: str) -> dict[str, Any]:
        """
        GET /v1/races?date=YYYY-MM-DD

        Returns venues → races tree for GUI selection (published races only).
        """
        if not date or len(date) < 10:
            raise ValueError("date is required (YYYY-MM-DD)")

        list_html = self.client.fetch_race_list(date)
        meetings = parse_meetings_from_race_list(list_html)
        listed = parse_list_races_from_race_list(list_html)

        venues_present = sorted({m.venue for m in meetings} | {r.venue for r in listed})
        meeting_order = [m.venue for m in meetings]
        venue_labels = assign_venue_label_nos(venues_present, preferred_order=meeting_order)

        races: list[dict[str, Any]] = []
        for r in listed:
            win5_id = make_win5_race_id(date, r.venue, r.race_no, venue_labels)
            races.append(
                build_race_summary(
                    race_id=win5_id,
                    race_date=date,
                    course=r.venue,
                    race_number=r.race_no,
                    race_name=getattr(r, "race_name", "") or "",
                    numeric_race_id=r.race_id,
                    status="published",
                    extra={
                        "collector_race_id": collector_race_id(date, r.venue, r.race_no),
                    },
                )
            )

        races.sort(key=lambda x: (
            venue_labels.get(str(x.get("course")), 99),
            int(x.get("race_number") or 0),
        ))

        return {
            "date": date,
            "meetings": [
                {
                    "course": m.venue,
                    "venue": m.venue,
                    "venue_code": m.venue_code,
                    "kai": m.kai,
                    "day": m.day,
                }
                for m in meetings
            ],
            "venues": group_races_by_course(races, preferred_order=meeting_order),
            "races": races,
            "count": len(races),
        }

    def resolve_race_ref(self, race_id: str) -> dict[str, Any]:
        """Resolve Win5 or collector race_id to date/course/race_number + numeric id."""
        parsed = parse_race_id_ref(race_id)
        date = parsed["race_date"]
        race_number = int(parsed["race_number"])
        course = parsed.get("course") or ""

        list_html = self.client.fetch_race_list(date)
        listed = parse_list_races_from_race_list(list_html)
        meetings = parse_meetings_from_race_list(list_html)
        venues_present = sorted({m.venue for m in meetings} | {r.venue for r in listed})
        meeting_order = [m.venue for m in meetings]
        venue_labels = assign_venue_label_nos(venues_present, preferred_order=meeting_order)

        if parsed["format"] == "win5":
            label_no = parsed["label_no"]
            inv = {v: k for k, v in venue_labels.items()}
            course = inv.get(label_no, "")
            if not course:
                candidates = [r for r in listed if r.race_no == race_number]
                if len(candidates) == 1:
                    course = candidates[0].venue
                elif not candidates:
                    raise RaceNotFoundError(
                        "race_no_mismatch",
                        f"no published race for race_id={race_id}",
                    )
                else:
                    raise RaceNotFoundError(
                        "race_id_ambiguous",
                        f"cannot map label_no={label_no} for race_id={race_id}; venues={venues_present}",
                    )

        hit = next((r for r in listed if r.venue == course and r.race_no == race_number), None)
        if not hit:
            raise RaceNotFoundError(
                "race_no_mismatch",
                f"race not in published list: date={date} course={course} race_number={race_number}",
            )

        win5_id = make_win5_race_id(date, course, race_number, venue_labels)
        return {
            "race_id": win5_id,
            "race_date": date,
            "course": course,
            "race_number": race_number,
            "race_label": race_label(course, race_number),
            "race_name": getattr(hit, "race_name", "") or "",
            "numeric_race_id": hit.race_id,
            "collector_race_id": collector_race_id(date, course, race_number),
        }

    def get_race(self, race_id: str, *, enrich: bool = True) -> dict[str, Any]:
        """GET /v1/races/{race_id} — display identity + optional shutuba meta."""
        ref = self.resolve_race_ref(race_id)
        summary = build_race_summary(
            race_id=ref["race_id"],
            race_date=ref["race_date"],
            course=ref["course"],
            race_number=ref["race_number"],
            race_name=ref.get("race_name") or "",
            numeric_race_id=ref["numeric_race_id"],
            status="published",
            extra={"collector_race_id": ref["collector_race_id"]},
        )
        if not enrich:
            return summary

        try:
            html = self.client.fetch_shutuba(ref["numeric_race_id"])
        except NetkeibaFetchError as exc:
            summary["enrich_error"] = str(exc)
            return summary

        if not shutuba_has_race(html):
            summary["status"] = "unpublished"
            summary["unpublished_reason"] = "shutuba_empty"
            return summary

        meta = parse_race_meta_from_shutuba(
            html,
            date=ref["race_date"],
            venue=ref["course"],
            race_no=ref["race_number"],
            numeric_race_id=ref["numeric_race_id"],
        )
        if meta.get("race_name"):
            summary["race_name"] = meta["race_name"]
        summary["distance"] = meta.get("distance")
        summary["surface"] = meta.get("surface") or meta.get("target_surface")
        summary["turn"] = meta.get("turn")
        summary["weather"] = meta.get("weather")
        summary["track_condition"] = meta.get("track_condition")
        summary["field_size"] = meta.get("field_size")
        return summary

    def get_prediction(self, race_id: str) -> dict[str, Any]:
        """
        GET /v1/predictions/{race_id}

        Prediction uses race_id as key; course/race_number/race_label are display-only.
        """
        ref = self.resolve_race_ref(race_id)
        display = build_race_summary(
            race_id=ref["race_id"],
            race_date=ref["race_date"],
            course=ref["course"],
            race_number=ref["race_number"],
            race_name=ref.get("race_name") or "",
            numeric_race_id=ref["numeric_race_id"],
            extra={"collector_race_id": ref["collector_race_id"]},
        )

        ai_root = _resolve_ai_platform_root()
        if ai_root is None:
            return {
                **display,
                "prediction_available": False,
                "error": "prediction_runtime_unavailable",
                "message": "AI platform root not found (set PI_AI_PLATFORM_ROOT or AI_PLATFORM_ROOT)",
            }

        try:
            ai_root_str = str(ai_root)
            if ai_root_str not in sys.path:
                sys.path.insert(0, ai_root_str)
            from ai_platform.core.candidate_evaluation import CorePipeline
            from ai_platform.core.features.feature_loader import FeatureLoader, get_last_failure_reason
        except Exception as exc:
            return {
                **display,
                "prediction_available": False,
                "error": "prediction_runtime_unavailable",
                "message": str(exc),
            }

        data_root = _resolve_prediction_data_root()
        loader = FeatureLoader(data_root=data_root)
        pipeline = CorePipeline(loader=loader)
        result = pipeline.evaluate(ref["race_id"])
        if result is None:
            return {
                **display,
                "prediction_available": False,
                "error": "features_unavailable",
                "message": get_last_failure_reason() or "FeatureLoader returned None",
            }

        return {
            **display,
            "prediction_available": True,
            "prediction": {
                "race_id": result.get("race_id"),
                "candidates": result.get("candidates"),
                "context": result.get("context"),
                "world": result.get("world"),
                "sub_world": result.get("sub_world"),
                "overall_confidence": result.get("overall_confidence"),
                "meta": result.get("meta"),
                "core_version": result.get("core_version"),
                # Version 2 Explainability — additive pass-through only (no transform)
                **(
                    {"explain_payload": result["explain_payload"]}
                    if (
                        result.get("explain_payload") is not None
                        and str(os.environ.get("EXPLAIN_V2_ENABLED", "")).strip().lower()
                        in {"1", "true", "yes", "on"}
                    )
                    else {}
                ),
            },
        }

    def race_meta(self, *, date: str, venue: str, race_no: int) -> dict[str, Any]:
        numeric, html = self.resolve(date=date, venue=venue, race_no=race_no)
        meta = parse_race_meta_from_shutuba(
            html,
            date=date,
            venue=venue,
            race_no=race_no,
            numeric_race_id=numeric,
        )
        return {
            **meta,
            "race_date": date,
            "course": venue,
            "race_number": race_no,
            "race_label": race_label(venue, race_no),
            "race_name": meta.get("race_name") or "",
        }

    def entries_core(self, *, date: str, venue: str, race_no: int) -> dict[str, Any]:
        numeric, html = self.resolve(date=date, venue=venue, race_no=race_no)
        entries = [
            {k: v for k, v in row.items() if not str(k).startswith("_")}
            for row in parse_entries_from_shutuba(html)
        ]
        if not entries:
            raise RaceNotFoundError(
                "parse_entries_empty",
                f"entries parse empty: date={date} venue={venue} race_no={race_no} race_id={numeric}",
            )
        return {
            "race_id": collector_race_id(date, venue, race_no),
            "date": date,
            "race_date": date,
            "venue": venue,
            "course": venue,
            "race_no": race_no,
            "race_number": race_no,
            "race_label": race_label(venue, race_no),
            "entries": entries,
            "numeric_race_id": numeric,
        }

    def odds(self, *, date: str, venue: str, race_no: int) -> dict[str, Any]:
        _, html = self.resolve(date=date, venue=venue, race_no=race_no)
        raw_entries = parse_entries_from_shutuba(html)
        odds_rows = parse_odds_from_entries(raw_entries)
        if not odds_rows:
            odds_rows = [
                {"horse_number": e["horse_number"], "win": 99.9}
                for e in raw_entries
                if e.get("horse_number") is not None
            ]
        if not odds_rows:
            raise RaceNotFoundError("parse_entries_empty", "odds empty")
        return {
            "race_id": collector_race_id(date, venue, race_no),
            "date": date,
            "race_date": date,
            "venue": venue,
            "course": venue,
            "race_no": race_no,
            "race_number": race_no,
            "race_label": race_label(venue, race_no),
            "odds": odds_rows,
        }

    def track(self, *, date: str, venue: str, race_no: int) -> dict[str, Any]:
        _, html = self.resolve(date=date, venue=venue, race_no=race_no)
        return {
            "race_id": collector_race_id(date, venue, race_no),
            "date": date,
            "race_date": date,
            "venue": venue,
            "course": venue,
            "race_no": race_no,
            "race_number": race_no,
            "race_label": race_label(venue, race_no),
            "condition": parse_track_condition(html),
        }

    def entries_full(self, *, date: str, venue: str, race_no: int) -> dict[str, Any]:
        """entries_core + sex/age/trainer/horse_url (Win5AI runners.csv compatible)."""
        numeric, html = self.resolve(date=date, venue=venue, race_no=race_no)
        raw_entries = parse_entries_from_shutuba(html)
        if not raw_entries:
            raise RaceNotFoundError(
                "parse_entries_empty",
                f"entries parse empty: date={date} venue={venue} race_no={race_no}",
            )
        meta = parse_race_meta_from_shutuba(
            html, date=date, venue=venue, race_no=race_no, numeric_race_id=numeric,
        )
        entries = []
        for row in raw_entries:
            entries.append({
                "horse_number": row.get("horse_number"),
                "frame_number": row.get("frame", 0),
                "horse_name": row.get("horse_name", ""),
                "jockey": row.get("jockey", ""),
                "weight_carried": row.get("weight", 0.0),
                "horse_id": row.get("horse_id", ""),
                "horse_url": row.get("_horse_url", ""),
                "sex": row.get("_sex", ""),
                "age": row.get("_age"),
                "odds": row.get("_odds"),
                "popularity": row.get("_popularity"),
            })
        return {
            **meta,
            "race_date": date,
            "course": venue,
            "race_number": race_no,
            "race_label": race_label(venue, race_no),
            "race_name": meta.get("race_name") or "",
            "entries": entries,
        }

    def horse_history(
        self,
        *,
        entries: list[dict[str, Any]],
        race_context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch horse history for all entries — same as demo_horse_history_fetcher.py output."""
        all_rows: list[dict[str, Any]] = []
        for entry in entries:
            horse_id = str(entry.get("horse_id", "")).strip()
            if not horse_id:
                continue
            try:
                parsed = fetch_horse_history(self.client, horse_id)
            except NetkeibaFetchError as exc:
                print(f"[pi-keibanet] horse_history fetch failed: horse_id={horse_id}: {exc}")
                continue
            runner = {**entry}
            if race_context:
                runner.update(race_context)
            rows = build_history_rows(runner, parsed)
            all_rows.extend(rows)
        return all_rows


__all__ = ["NetkeibaFetchError", "PiKeibaNetService", "RaceNotFoundError"]
