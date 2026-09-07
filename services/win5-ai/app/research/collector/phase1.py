# -*- coding: utf-8 -*-
"""Phase1 Evidence collectors (market + trainer + V10.3 horse/workout)."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from ..anti_leak import accept_observation, anti_leak_ok
from .horse_collector import collect_horse_intelligence
from .netkeiba_client import ResearchNetkeibaClient
from .pi_client import ResearchPiClient
from .workout_collector import collect_workout_intelligence


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _asof_enabled() -> bool:
    raw = (os.environ.get("RESEARCH_HARVEST_ASOF") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _resolve_observed_at(
    *,
    source_observed_at: str | None,
    prediction_created_at: str,
    fetched_at: str,
) -> tuple[str, bool]:
    """Return (observed_at, asof_clamped)."""
    if source_observed_at and anti_leak_ok(
        observed_at=source_observed_at, prediction_created_at=prediction_created_at
    ):
        return source_observed_at, False
    if _asof_enabled():
        return prediction_created_at, True
    return source_observed_at or fetched_at, False


def _derive_expected_popularity(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked: list[tuple[float, int]] = []
    for row in entries:
        odds = row.get("win_odds")
        if odds is None:
            continue
        try:
            ranked.append((float(odds), int(row["horse_number"])))
        except (TypeError, ValueError):
            continue
    ranked.sort(key=lambda x: (x[0], x[1]))
    out: list[dict[str, Any]] = []
    last_rank = 0
    last_odds: float | None = None
    for idx, (odds, horse_number) in enumerate(ranked, start=1):
        if last_odds is None or odds != last_odds:
            last_rank = idx
            last_odds = odds
        out.append({"horse_number": horse_number, "expected_popularity": last_rank})
    return out


def collect_phase1_from_board(
    *,
    board: dict[str, Any],
    prediction_created_at: str,
    fetched_at: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    """
    Returns (runner_observations, source_records, anti_leak_violations).
    Passes through horse_id / horse_url / numeric_race_id for V10.3 collectors.
    """
    fetched = fetched_at or _iso_now()
    market_obs, market_clamped = _resolve_observed_at(
        source_observed_at=board.get("odds_updated_at"),
        prediction_created_at=prediction_created_at,
        fetched_at=fetched,
    )
    trainer_obs, trainer_clamped = _resolve_observed_at(
        source_observed_at=prediction_created_at if _asof_enabled() else fetched,
        prediction_created_at=prediction_created_at,
        fetched_at=fetched,
    )
    entries = list(board.get("entries") or [])
    violations = 0
    by_horse: dict[int, dict[str, Any]] = {}
    numeric_race_id = (
        board.get("numeric_race_id")
        or board.get("netkeiba_race_id")
        or (board.get("race") or {}).get("numeric_race_id")
    )

    for row in entries:
        try:
            hn = int(row.get("horse_number"))
        except (TypeError, ValueError):
            continue
        horse_id = str(row.get("horse_id") or "").strip() or None
        horse_url = str(row.get("horse_url") or "").strip() or None
        if not horse_id and horse_url:
            import re

            m = re.search(r"/horse/(\d+)", horse_url)
            if m:
                horse_id = m.group(1)

        by_horse[hn] = {
            "horse_number": hn,
            "horse_id": horse_id,
            "horse_url": horse_url,
            "popularity": None,
            "win_odds": None,
            "expected_popularity": None,
            "trainer": None,
            "sire": None,
            "damsire": None,
            "breeder": None,
            "owner": None,
            "sale_price": None,
            "oikiri_time": None,
            "oikiri_rating": None,
            "missing": [],
        }

        pop_raw = row.get("popularity")
        pop_val, _, pop_miss = accept_observation(
            value=pop_raw if pop_raw not in ("", None) else None,
            observed_at=market_obs,
            prediction_created_at=prediction_created_at,
        )
        if pop_miss == "anti_leak_rejected":
            violations += 1
        if pop_val is not None:
            by_horse[hn]["popularity"] = int(pop_val)
        elif pop_raw in ("", None):
            by_horse[hn]["missing"].append(
                {"field": "popularity", "reason": "not_yet_published", "source_id": "jra_odds_api"}
            )
        else:
            by_horse[hn]["missing"].append(
                {"field": "popularity", "reason": pop_miss or "parse_failed", "source_id": "jra_odds_api"}
            )

        odds_raw = row.get("odds")
        try:
            odds_num = float(odds_raw) if odds_raw not in ("", None) else None
        except (TypeError, ValueError):
            odds_num = None
        odds_val, _, odds_miss = accept_observation(
            value=odds_num,
            observed_at=market_obs,
            prediction_created_at=prediction_created_at,
        )
        if odds_miss == "anti_leak_rejected":
            violations += 1
        if odds_val is not None:
            by_horse[hn]["win_odds"] = float(odds_val)
        elif odds_raw in ("", None):
            by_horse[hn]["missing"].append(
                {"field": "win_odds", "reason": "not_yet_published", "source_id": "jra_odds_api"}
            )
        else:
            by_horse[hn]["missing"].append(
                {"field": "win_odds", "reason": odds_miss or "parse_failed", "source_id": "jra_odds_api"}
            )

        trainer_raw = row.get("trainer")
        trainer_val, _, trainer_miss = accept_observation(
            value=str(trainer_raw).strip() if trainer_raw not in ("", None) else None,
            observed_at=trainer_obs,
            prediction_created_at=prediction_created_at,
        )
        if trainer_miss == "anti_leak_rejected":
            violations += 1
        if trainer_val:
            by_horse[hn]["trainer"] = trainer_val
        else:
            by_horse[hn]["missing"].append(
                {
                    "field": "trainer",
                    "reason": trainer_miss or "not_exposed",
                    "source_id": "netkeiba_shutuba",
                }
            )

    exp_rows = _derive_expected_popularity(
        [{"horse_number": hn, "win_odds": r.get("win_odds")} for hn, r in by_horse.items()]
    )
    for item in exp_rows:
        hn = item["horse_number"]
        if hn not in by_horse:
            continue
        val, _, miss = accept_observation(
            value=item["expected_popularity"],
            observed_at=market_obs,
            prediction_created_at=prediction_created_at,
        )
        if miss == "anti_leak_rejected":
            violations += 1
        if val is not None:
            by_horse[hn]["expected_popularity"] = int(val)
        else:
            by_horse[hn]["missing"].append(
                {
                    "field": "expected_popularity",
                    "reason": miss or "win_odds_missing",
                    "source_id": "derived_expected_pop",
                }
            )

    runners = list(by_horse.values())
    sources: list[dict[str, Any]] = [
        {
            "feature_id": "market_bundle",
            "source_id": "pi_race_board",
            "success": bool(entries),
            "observed_at": market_obs,
            "fetched_at": fetched,
            "asof_clamped": market_clamped,
            "meta": {"numeric_race_id": numeric_race_id},
        },
        {
            "feature_id": "trainer",
            "source_id": "netkeiba_shutuba",
            "success": any(r.get("trainer") for r in runners),
            "observed_at": trainer_obs,
            "fetched_at": fetched,
            "asof_clamped": trainer_clamped,
        },
    ]

    # Attach race-level numeric id for workout collector
    for r in runners:
        r["_numeric_race_id"] = numeric_race_id

    return runners, sources, violations


def fetch_and_collect(
    *,
    client: ResearchPiClient,
    race_id: str,
    prediction_created_at: str,
    netkeiba: ResearchNetkeibaClient | None = None,
    enable_horse: bool = True,
    enable_workout: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, float | None, str | None]:
    board, latency_ms, err = client.fetch_race_board(race_id)
    if board is None:
        return [], [], 0, latency_ms, err or "fetch_failed"

    fetched = _iso_now()
    runners, sources, violations = collect_phase1_from_board(
        board=board,
        prediction_created_at=prediction_created_at,
        fetched_at=fetched,
    )

    nk = netkeiba or ResearchNetkeibaClient()
    numeric_race_id = None
    if runners:
        numeric_race_id = runners[0].get("_numeric_race_id")
    if not numeric_race_id:
        numeric_race_id = board.get("numeric_race_id") or board.get("netkeiba_race_id")

    if enable_horse:
        runners, horse_sources, horse_violations = collect_horse_intelligence(
            runners=runners,
            prediction_created_at=prediction_created_at,
            fetched_at=fetched,
            client=nk,
        )
        sources.extend(horse_sources)
        violations += horse_violations

    if enable_workout:
        runners, workout_sources, workout_violations = collect_workout_intelligence(
            runners=runners,
            numeric_race_id=str(numeric_race_id) if numeric_race_id else None,
            prediction_created_at=prediction_created_at,
            fetched_at=fetched,
            client=nk,
        )
        sources.extend(workout_sources)
        violations += workout_violations

    # Strip internal keys from runners before snapshot
    for r in runners:
        r.pop("_numeric_race_id", None)

    return runners, sources, violations, latency_ms, None
