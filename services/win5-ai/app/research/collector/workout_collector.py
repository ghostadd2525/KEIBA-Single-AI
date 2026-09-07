# -*- coding: utf-8 -*-
"""Phase2 Workout Collector — oikiri type=1."""
from __future__ import annotations

import os
import re
from datetime import datetime, time, timezone, timedelta
from html import unescape
from typing import Any

from ..anti_leak import accept_observation, anti_leak_ok, parse_iso
from .netkeiba_client import ResearchNetkeibaClient, ResearchNetkeibaError

JST = timezone(timedelta(hours=9))


def _asof_enabled() -> bool:
    raw = (os.environ.get("RESEARCH_HARVEST_ASOF") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _strip(s: str) -> str:
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()


def _parse_workout_date(date_cell: str) -> datetime | None:
    """Parse '2026/07/22(水)' → datetime at 18:00 JST (typical publish window)."""
    m = re.match(r"(\d{4})/(\d{2})/(\d{2})", (date_cell or "").strip())
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return datetime(y, mo, d, 18, 0, 0, tzinfo=JST)


def _extract_sessions_from_window(win: str) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", win, re.S):
        tds = [_strip(x) for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if not tds or not re.match(r"\d{4}/\d{2}/\d{2}", tds[0] or ""):
            continue
        # Time cell: prefer td with multiple NN.N patterns
        time_cell = ""
        times: list[str] = []
        for td in tds:
            cand = re.findall(r"\d{2}\.\d", td)
            if len(cand) >= 2 and len(cand) > len(times):
                times = cand
                time_cell = td
        if not times and len(tds) > 4:
            time_cell = tds[4]
            times = re.findall(r"\d{2}\.\d", time_cell)
        eval_text = ""
        letter = None
        for td in tds:
            if re.fullmatch(r"[ABCDE]", td or ""):
                letter = td
            elif any(
                k in (td or "")
                for k in ("仕上", "順調", "気配", "動き", "まずまず", "平凡")
            ):
                eval_text = td
        if letter is None:
            lm = re.search(r"\b([ABCDE])\b", " ".join(tds[-3:]))
            letter = lm.group(1) if lm else None
        wdt = _parse_workout_date(tds[0])
        sessions.append(
            {
                "date": tds[0],
                "course": tds[1] if len(tds) > 1 else "",
                "times": times,
                "time_raw": time_cell,
                "eval_text": eval_text,
                "letter": letter,
                "observed_dt": wdt,
            }
        )
    return sessions


def parse_oikiri_html(
    html: str,
    *,
    horse_ids: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Return horse_id → latest session.
    If horse_ids given, only extract windows for those IDs (race entrants).
    """
    by_horse: dict[str, dict[str, Any]] = {}
    target_ids = set(horse_ids) if horse_ids else set(re.findall(r"/horse/(\d{10})", html))

    for hid in target_ids:
        # Anchor on horse link; take a window that covers Head rows + sessions
        positions = [m.start() for m in re.finditer(rf"/horse/{re.escape(hid)}", html)]
        if not positions:
            continue
        best_sessions: list[dict[str, Any]] = []
        name = None
        for pos in positions[:3]:
            # Include preceding Head block (name often before first dated row)
            win = html[max(0, pos - 800) : pos + 7000]
            name_m = re.search(
                rf"/horse/{re.escape(hid)}[^>]*>\s*([^<]+)",
                win,
            )
            if name_m and not name:
                name = _strip(name_m.group(1))
            sessions = _extract_sessions_from_window(win)
            if len(sessions) > len(best_sessions):
                best_sessions = sessions

        if not best_sessions:
            by_horse[hid] = {}
            continue

        best_sessions.sort(
            key=lambda s: s["observed_dt"]
            or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        latest = best_sessions[0]
        obs = latest.get("observed_dt")
        by_horse[hid] = {
            "horse_id": hid,
            "name": name,
            "oikiri_time": latest["times"][0] if latest.get("times") else None,
            "oikiri_time_raw": latest.get("time_raw"),
            "oikiri_times": latest.get("times") or [],
            "oikiri_rating": latest.get("letter") or latest.get("eval_text") or None,
            "oikiri_eval_text": latest.get("eval_text"),
            "oikiri_letter": latest.get("letter"),
            "workout_date": latest.get("date"),
            "observed_at": obs.isoformat() if obs else None,
            "sessions_n": len(best_sessions),
        }
    return by_horse


def _pick_session_before_prediction(
    parsed: dict[str, Any],
    prediction_created_at: str,
) -> dict[str, Any] | None:
    """Use parsed latest if anti-leak ok; else None (caller may asof-clamp static-like)."""
    if not parsed:
        return None
    obs = parsed.get("observed_at")
    if obs and anti_leak_ok(observed_at=obs, prediction_created_at=prediction_created_at):
        return parsed
    return None


def collect_workout_intelligence(
    *,
    runners: list[dict[str, Any]],
    numeric_race_id: str | None,
    prediction_created_at: str,
    fetched_at: str,
    client: ResearchNetkeibaClient | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    """
    Enrich runners with oikiri_time / oikiri_rating from oikiri.html?type=1.
    Only sessions with observed_at <= prediction_created_at are accepted.
    """
    nk = client or ResearchNetkeibaClient()
    violations = 0

    for row in runners:
        row.setdefault("oikiri_time", None)
        row.setdefault("oikiri_rating", None)

    if not numeric_race_id:
        for row in runners:
            for fid in ("oikiri_time", "oikiri_rating"):
                row.setdefault("missing", []).append(
                    {
                        "field": fid,
                        "reason": "numeric_race_id_missing",
                        "source_id": "netkeiba_oikiri",
                    }
                )
        sources = [
            {
                "feature_id": "oikiri",
                "source_id": "netkeiba_oikiri",
                "success": False,
                "observed_at": None,
                "fetched_at": fetched_at,
                "asof_clamped": False,
                "meta": {"error": "numeric_race_id_missing"},
            }
        ]
        return runners, sources, 0

    try:
        html = nk.fetch_oikiri(str(numeric_race_id), type_=1)
    except ResearchNetkeibaError as exc:
        for row in runners:
            for fid in ("oikiri_time", "oikiri_rating"):
                row.setdefault("missing", []).append(
                    {
                        "field": fid,
                        "reason": f"fetch_failed:{exc}",
                        "source_id": "netkeiba_oikiri",
                    }
                )
        return (
            runners,
            [
                {
                    "feature_id": "oikiri",
                    "source_id": "netkeiba_oikiri",
                    "success": False,
                    "observed_at": None,
                    "fetched_at": fetched_at,
                    "asof_clamped": False,
                    "meta": {"error": str(exc)},
                }
            ],
            0,
        )

    by_hid = parse_oikiri_html(
        html,
        horse_ids={
            str(r.get("horse_id")).strip()
            for r in runners
            if r.get("horse_id")
        },
    )
    # Also index by horse_number via runners' horse_id
    filled_time = 0
    filled_rating = 0

    for row in runners:
        hid = str(row.get("horse_id") or "").strip()
        parsed = by_hid.get(hid) if hid else None
        usable = _pick_session_before_prediction(parsed or {}, prediction_created_at)

        # Historical backfill: if workout date fails anti-leak only because
        # we lack exact publish clock, allow asof clamp when RESEARCH_HARVEST_ASOF=1
        # AND workout calendar date <= prediction calendar date.
        asof_clamped = False
        if parsed and not usable and _asof_enabled():
            obs_dt = parse_iso(parsed.get("observed_at"))
            pred_dt = parse_iso(prediction_created_at)
            if obs_dt and pred_dt:
                # Compare dates in JST
                obs_day = obs_dt.astimezone(JST).date()
                pred_day = pred_dt.astimezone(JST).date()
                if obs_day <= pred_day:
                    usable = dict(parsed)
                    usable["observed_at"] = prediction_created_at
                    asof_clamped = True

        if not usable:
            # Try: data exists but after prediction → anti-leak reject
            if parsed and parsed.get("oikiri_time"):
                violations += 1
                reason = "anti_leak_rejected"
            elif not hid:
                reason = "horse_id_missing"
            elif not parsed:
                reason = "not_published"
            else:
                reason = "anti_leak_rejected"
            for fid in ("oikiri_time", "oikiri_rating"):
                row.setdefault("missing", []).append(
                    {
                        "field": fid,
                        "reason": reason,
                        "source_id": "netkeiba_oikiri",
                    }
                )
            continue

        obs = usable.get("observed_at") or prediction_created_at
        time_val, _, time_miss = accept_observation(
            value=usable.get("oikiri_time"),
            observed_at=obs,
            prediction_created_at=prediction_created_at,
        )
        rating_raw = usable.get("oikiri_letter") or usable.get("oikiri_rating")
        rating_val, _, rating_miss = accept_observation(
            value=rating_raw,
            observed_at=obs,
            prediction_created_at=prediction_created_at,
        )
        if time_miss == "anti_leak_rejected" or rating_miss == "anti_leak_rejected":
            violations += 1

        if time_val is not None:
            try:
                row["oikiri_time"] = float(time_val)
            except (TypeError, ValueError):
                row["oikiri_time"] = time_val
            filled_time += 1
            if asof_clamped:
                row["oikiri_asof_clamped"] = True
        else:
            row.setdefault("missing", []).append(
                {
                    "field": "oikiri_time",
                    "reason": time_miss or "not_published",
                    "source_id": "netkeiba_oikiri",
                }
            )

        if rating_val is not None:
            row["oikiri_rating"] = str(rating_val)
            filled_rating += 1
        else:
            row.setdefault("missing", []).append(
                {
                    "field": "oikiri_rating",
                    "reason": rating_miss or "not_published",
                    "source_id": "netkeiba_oikiri",
                }
            )

    sources = [
        {
            "feature_id": "oikiri",
            "source_id": "netkeiba_oikiri",
            "success": filled_time > 0 or filled_rating > 0,
            "observed_at": prediction_created_at if _asof_enabled() else fetched_at,
            "fetched_at": fetched_at,
            "asof_clamped": _asof_enabled(),
            "meta": {
                "numeric_race_id": numeric_race_id,
                "horses_parsed": len(by_hid),
                "filled_time": filled_time,
                "filled_rating": filled_rating,
            },
        }
    ]
    return runners, sources, violations
