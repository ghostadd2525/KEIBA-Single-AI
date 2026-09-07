#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare baseline vs candidate daily feature CSVs for known specials.

Exit 0 when guarded races are preserved (row counts + key columns within tolerance).
Exit 1 on regression (missing race, row-count drift, or large history/odds drift).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

DEFAULT_GUARD_RACES = [
    "2026-07-25-01-06",
    "2026-07-25-01-07",
    "2026-07-25-01-08",
    "2026-07-25-02-06",
    "2026-07-25-02-07",
    "2026-07-25-02-08",
    "2026-07-25-03-10",
    "2026-07-25-03-11",
    "2026-07-25-03-12",
]

COMPARE_COLS = [
    "history_score",
    "distance_score",
    "history_count",
    "win5_leg",
    "odds",
    "odds_today",
    "popularity",
]


def _load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def _max_abs_diff(a: pd.Series, b: pd.Series) -> float:
    an = pd.to_numeric(a, errors="coerce")
    bn = pd.to_numeric(b, errors="coerce")
    if len(an) != len(bn):
        return float("inf")
    return float((an - bn).abs().max(skipna=True) if len(an) else 0.0)


def compare_race(
    baseline: pd.DataFrame,
    candidate: pd.DataFrame,
    race_id: str,
    *,
    history_tol: float,
) -> list[str]:
    errors: list[str] = []
    b = baseline[baseline["race_id"].astype(str) == race_id].copy()
    c = candidate[candidate["race_id"].astype(str) == race_id].copy()
    if b.empty:
        errors.append(f"{race_id}: missing in baseline")
        return errors
    if c.empty:
        errors.append(f"{race_id}: missing in candidate")
        return errors
    if len(b) != len(c):
        errors.append(f"{race_id}: row_count baseline={len(b)} candidate={len(c)}")

    # Align on horse key when possible
    key = "horse_id" if "horse_id" in b.columns and "horse_id" in c.columns else None
    if key is None and "horse_number" in b.columns and "horse_number" in c.columns:
        key = "horse_number"
    if key is not None:
        b = b.sort_values(key).reset_index(drop=True)
        c = c.sort_values(key).reset_index(drop=True)

    for col in COMPARE_COLS:
        if col not in b.columns or col not in c.columns:
            continue
        diff = _max_abs_diff(b[col], c[col])
        if col == "win5_leg":
            if diff > 0:
                errors.append(f"{race_id}: win5_leg changed (max_abs_diff={diff})")
            continue
        tol = 0.0 if col in ("history_count", "popularity") else history_tol
        if diff > tol:
            errors.append(f"{race_id}: {col} max_abs_diff={diff} > tol={tol}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare daily feature CSVs for guarded races")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (informational)")
    parser.add_argument("--baseline", required=True, help="Baseline features CSV path")
    parser.add_argument("--candidate", required=True, help="Candidate features CSV path")
    parser.add_argument(
        "--race-ids",
        default=",".join(DEFAULT_GUARD_RACES),
        help="Comma-separated race_ids to guard",
    )
    parser.add_argument(
        "--history-tol",
        type=float,
        default=1e-6,
        help="Max abs diff allowed for float score/odds columns",
    )
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    candidate_path = Path(args.candidate)
    if not baseline_path.is_file():
        print(f"[compare] baseline missing: {baseline_path}", file=sys.stderr)
        return 1
    if not candidate_path.is_file():
        print(f"[compare] candidate missing: {candidate_path}", file=sys.stderr)
        return 1

    baseline = _load(baseline_path)
    candidate = _load(candidate_path)
    race_ids = [x.strip() for x in args.race_ids.split(",") if x.strip()]

    print(f"[compare] date={args.date or '—'}")
    print(f"[compare] baseline={baseline_path}")
    print(f"[compare] candidate={candidate_path}")
    print(f"[compare] baseline_races={baseline['race_id'].nunique()} candidate_races={candidate['race_id'].nunique()}")

    all_errors: list[str] = []
    for race_id in race_ids:
        errs = compare_race(baseline, candidate, race_id, history_tol=args.history_tol)
        if errs:
            all_errors.extend(errs)
        else:
            print(f"[compare] OK {race_id}")

    if all_errors:
        print("[compare] FAIL")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print("[compare] PASS - guarded races preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
