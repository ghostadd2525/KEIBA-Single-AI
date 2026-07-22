# -*- coding: utf-8 -*-
"""
Win5AI compatible pipeline: entries → horse_history → features CSV.

Usage:
  python scripts/run_pipeline.py --date 2026-07-19 --venue 福島 --race-no 10
  python scripts/run_pipeline.py --date 2026-07-19  # all venues/races for the day

Output:
  data/pipeline/{date}/runners.csv
  data/pipeline/{date}/horse_history_raw.csv
  data/pipeline/{date}/runners_pace_market_features.csv
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pi_keibanet.netkeiba.client import NetkeibaClient, NetkeibaFetchError
from pi_keibanet.netkeiba.parse import (
    find_numeric_race_id,
    parse_entries_from_shutuba,
    parse_list_races_from_race_list,
    parse_meetings_from_race_list,
    parse_race_meta_from_shutuba,
    shutuba_has_race,
)
from pi_keibanet.netkeiba.horse_history import (
    OUT_COLUMNS as HISTORY_COLUMNS,
    build_history_rows,
    fetch_horse_history,
)
from pi_keibanet.features import build_features
from pi_keibanet.venues import COURSE_NAME_TO_CODE, win5_pipeline_race_id


def _resolve_win5_race_id(
    date: str,
    race_no: int,
    numeric_race_id: str,
    legacy_dir: Path | None = None,
) -> str:
    """Resolve Win5AI race_id; prefer legacy runners.csv when available."""
    if legacy_dir is None:
        legacy_dir = Path("C:/win5-ai/data")
    runners_path = legacy_dir / "runners.csv"
    if runners_path.exists():
        try:
            df = pd.read_csv(runners_path, encoding="utf-8-sig")
            if "numeric_race_id" in df.columns and "race_id" in df.columns:
                nrid = str(numeric_race_id).strip()
                hit = df[df["numeric_race_id"].astype(str).str.strip() == nrid]
                if not hit.empty:
                    return str(hit.iloc[0]["race_id"]).strip()
        except Exception:
            pass
    return win5_pipeline_race_id(date, 1, race_no)


def collect_races(client: NetkeibaClient, date: str, venue: str | None, race_no: int | None):
    """Resolve available races for the given date."""
    list_html = client.fetch_race_list(date)
    listed = parse_list_races_from_race_list(list_html)
    meetings = parse_meetings_from_race_list(list_html)

    targets = []
    for race in listed:
        if venue and race.venue != venue:
            continue
        if race_no is not None and race.race_no != race_no:
            continue
        targets.append({"venue": race.venue, "race_no": race.race_no, "numeric_race_id": race.race_id})

    return targets


def run_pipeline(date: str, venue: str | None, race_no: int | None, output_dir: Path):
    client = NetkeibaClient(min_interval_sec=2.0)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[pipeline] Resolving races for {date} ...")
    targets = collect_races(client, date, venue, race_no)
    if not targets:
        print("[pipeline] No races found.")
        return

    print(f"[pipeline] Found {len(targets)} race(s)")

    # Step 1: entries
    all_runners = []
    all_race_meta = []
    for t in targets:
        nrid = t["numeric_race_id"]
        v = t["venue"]
        rn = t["race_no"]
        try:
            html = client.fetch_shutuba(nrid)
        except NetkeibaFetchError as e:
            print(f"[pipeline] SKIP shutuba fetch failed: {v} {rn}R: {e}")
            continue
        if not shutuba_has_race(html):
            print(f"[pipeline] SKIP shutuba empty: {v} {rn}R")
            continue

        meta = parse_race_meta_from_shutuba(html, date=date, venue=v, race_no=rn, numeric_race_id=nrid)
        meta["race_id"] = _resolve_win5_race_id(date, rn, nrid)
        all_race_meta.append(meta)

        entries = parse_entries_from_shutuba(html)
        for e in entries:
            all_runners.append({
                "race_id": meta["race_id"],
                "numeric_race_id": nrid,
                "date": date,
                "course": v,
                "race_number": rn,
                "race_name": meta.get("race_name", ""),
                "target_surface": meta.get("surface", ""),
                "target_distance": meta.get("distance"),
                "turn": meta.get("turn", "unknown"),
                "weather": meta.get("weather", "unknown"),
                "track_condition": meta.get("track_condition", "unknown"),
                "frame_number": e.get("frame", 0),
                "horse_number": e.get("horse_number"),
                "horse_name": e.get("horse_name", ""),
                "horse_url": e.get("_horse_url", f"https://db.netkeiba.com/horse/{e.get('horse_id', '')}/"),
                "horse_id": e.get("horse_id", ""),
                "sex": e.get("_sex", ""),
                "age": e.get("_age"),
                "weight_carried": e.get("weight", 0.0),
                "jockey": e.get("jockey", ""),
                "odds": e.get("_odds"),
                "popularity": e.get("_popularity"),
            })

    if not all_runners:
        print("[pipeline] No runners collected.")
        return

    runners_df = pd.DataFrame(all_runners)
    runners_df = runners_df.drop_duplicates(subset=["numeric_race_id", "horse_id"], keep="last")
    runners_path = output_dir / "runners.csv"
    runners_df.to_csv(runners_path, index=False, encoding="utf-8-sig")
    print(f"[pipeline] runners.csv: {len(runners_df)} rows → {runners_path}")

    # Step 2: horse history
    all_history = []
    unique_horses = runners_df.drop_duplicates(subset=["horse_id"], keep="last")
    total = len(unique_horses)

    for i, (_, row) in enumerate(unique_horses.iterrows(), 1):
        hid = str(row.get("horse_id", "")).strip()
        hname = row.get("horse_name", "")
        if not hid:
            continue
        print(f"[pipeline] horse {i}/{total}: {hname} ({hid})")
        try:
            parsed = fetch_horse_history(client, hid)
        except NetkeibaFetchError as e:
            print(f"[pipeline]   SKIP: {e}")
            continue
        if not parsed:
            print(f"[pipeline]   no history rows")
            continue
        rows = build_history_rows(row.to_dict(), parsed)
        all_history.extend(rows)
        print(f"[pipeline]   {len(parsed)} history rows")

    history_df = pd.DataFrame(all_history)
    if history_df.empty:
        print("[pipeline] WARNING: no horse history collected")
        history_df = pd.DataFrame(columns=HISTORY_COLUMNS)

    history_path = output_dir / "horse_history_raw.csv"
    history_df.to_csv(history_path, index=False, encoding="utf-8-sig")
    print(f"[pipeline] horse_history_raw.csv: {len(history_df)} rows → {history_path}")

    # Step 3: features
    races_df = pd.DataFrame(all_race_meta) if all_race_meta else None
    features_df = build_features(runners_df, history_df, races_df)
    features_path = output_dir / "runners_pace_market_features.csv"
    features_df.to_csv(features_path, index=False, encoding="utf-8-sig")
    print(f"[pipeline] runners_pace_market_features.csv: {len(features_df)} rows → {features_path}")
    print("[pipeline] Done.")


def main():
    parser = argparse.ArgumentParser(description="Win5AI compatible pipeline")
    parser.add_argument("--date", required=True, help="Race date (YYYY-MM-DD)")
    parser.add_argument("--venue", default=None, help="Venue name (e.g. 福島)")
    parser.add_argument("--race-no", type=int, default=None, help="Race number")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    args = parser.parse_args()

    if args.output_dir:
        out = Path(args.output_dir)
    else:
        out = Path(__file__).resolve().parent.parent / "data" / "pipeline" / args.date

    run_pipeline(args.date, args.venue, args.race_no, out)


if __name__ == "__main__":
    main()
