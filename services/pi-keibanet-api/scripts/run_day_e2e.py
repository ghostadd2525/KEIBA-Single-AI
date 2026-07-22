# -*- coding: utf-8 -*-
"""
Day E2E: PI API → entries → horse_history → features → FeatureLoader check.

Usage:
  python scripts/run_day_e2e.py --date 2026-07-25
  python scripts/run_day_e2e.py --date 2026-07-25 --venues 新潟,中京,札幌
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pi_keibanet.netkeiba.client import NetkeibaClient, NetkeibaFetchError
from pi_keibanet.netkeiba.parse import (
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


VENUE_ORDER = ["新潟", "中京", "札幌"]


@dataclass
class RaceResult:
    venue: str
    race_no: int
    numeric_race_id: str = ""
    race_id: str = ""
    status: str = ""  # OK / UNPUBLISHED / ERROR
    unpublished_reason: str = ""
    entries_ok: bool = False
    entries_count: int = 0
    horse_ids: list[str] = field(default_factory=list)
    history_ok: int = 0
    history_fail: int = 0
    history_fail_reasons: list[str] = field(default_factory=list)
    features_ok: bool = False
    features_error: str = ""
    feature_loader_ok: bool = False
    feature_loader_source: str = ""
    feature_loader_rows: int = 0
    feature_loader_error: str = ""
    error: str = ""

    def summary_lines(self) -> list[str]:
        label = f"{self.venue}{self.race_no}R"
        if self.status == "UNPUBLISHED":
            reason = self.unpublished_reason or "shutuba_empty"
            return [f"{label}", f"未公開（{reason}）", ""]
        if self.status == "ERROR":
            return [f"{label}", f"ERROR: {self.error}", ""]
        lines = [
            f"{label}",
            f"entries: {'OK' if self.entries_ok else 'NG'} ({self.entries_count}頭)",
            f"history: {self.history_ok}/{self.entries_count}"
            + (f" (fail={self.history_fail})" if self.history_fail else ""),
            f"features: {'OK' if self.features_ok else 'NG'}",
            f"FeatureLoader: {'OK' if self.feature_loader_ok else 'NG'}"
            + (f" ({self.feature_loader_source}, {self.feature_loader_rows}rows)"
               if self.feature_loader_ok else ""),
        ]
        if self.history_fail_reasons:
            lines.append("history_fail: " + "; ".join(self.history_fail_reasons[:5]))
        if self.features_error:
            lines.append(f"features_error: {self.features_error}")
        if self.feature_loader_error:
            lines.append(f"loader_error: {self.feature_loader_error}")
        lines.append("")
        return lines


def resolve_win5_race_id(date: str, venue: str, race_no: int, numeric_race_id: str) -> str:
    """Assign Win5-compatible race_id using venue order for the day."""
    venues_seen = []
    # Prefer meeting order from VENUE_ORDER
    label_no = 1
    if venue in VENUE_ORDER:
        label_no = VENUE_ORDER.index(venue) + 1
    return win5_pipeline_race_id(date, label_no, race_no)


def build_expected_targets(
    meetings: list,
    listed: list,
    venues: list[str],
) -> list[dict[str, Any]]:
    """Build full 1R-12R targets per venue; mark unlisted as unpublished candidates."""
    listed_map: dict[tuple[str, int], str] = {
        (r.venue, r.race_no): r.race_id for r in listed
    }
    targets: list[dict[str, Any]] = []
    for venue in venues:
        if venue not in {m.venue for m in meetings} and venue not in {r.venue for r in listed}:
            continue
        meeting = next((m for m in meetings if m.venue == venue), None)
        for race_no in range(1, 13):
            nrid = listed_map.get((venue, race_no), "")
            if not nrid and meeting:
                # Construct expected numeric race id for unpublished races
                year = "2026"  # filled by caller date later
                nrid = ""
            targets.append({
                "venue": venue,
                "race_no": race_no,
                "numeric_race_id": listed_map.get((venue, race_no), ""),
                "listed": (venue, race_no) in listed_map,
            })
    return targets


def construct_numeric_race_id(date: str, meeting, race_no: int) -> str:
    year = date.replace("-", "")[:4]
    return f"{year}{meeting.venue_code}{meeting.kai}{meeting.day}{race_no:02d}"


def check_feature_loader(features_path: Path, race_id: str, data_root: Path) -> tuple[bool, str, int, str]:
    """Copy features into FeatureLoader daily path and try load."""
    try:
        ai_platform = Path(r"C:\win5-ai\ai_platform")
        if str(ai_platform) not in sys.path:
            sys.path.insert(0, str(ai_platform.parent))
        from ai_platform.core.features.feature_loader import FeatureLoader, get_last_failure_reason

        daily_dir = data_root / "demo_daily_outputs" / race_id[:10]
        daily_dir.mkdir(parents=True, exist_ok=True)
        dest = daily_dir / "demo_runners_pace_market_features.csv"
        shutil.copy2(features_path, dest)

        loader = FeatureLoader(data_root=data_root)
        result = loader.load(race_id)
        if result is None:
            return False, "", 0, get_last_failure_reason() or "load_failed"
        return True, result.feature_source, len(result.frame), ""
    except Exception as exc:
        return False, "", 0, f"{type(exc).__name__}: {exc}"


def run_day(
    date: str,
    venues: list[str],
    output_dir: Path,
    report_dir: Path,
    *,
    skip_unpublished_fetch: bool = False,
) -> list[RaceResult]:
    client = NetkeibaClient(min_interval_sec=2.0)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    print(f"[e2e] Fetching race list for {date} ...")
    list_html = client.fetch_race_list(date)
    meetings = parse_meetings_from_race_list(list_html)
    listed = parse_list_races_from_race_list(list_html)

    print(f"[e2e] Meetings: {[m.venue for m in meetings]}")
    print(f"[e2e] Listed races: {len(listed)}")
    for r in sorted(listed, key=lambda x: (x.venue, x.race_no)):
        print(f"  - {r.venue} {r.race_no}R ({r.race_id})")

    meeting_by_venue = {m.venue: m for m in meetings}
    targets = build_expected_targets(meetings, listed, venues)

    # Fill constructed ids for unlisted races
    for t in targets:
        if not t["numeric_race_id"] and t["venue"] in meeting_by_venue:
            t["numeric_race_id"] = construct_numeric_race_id(
                date, meeting_by_venue[t["venue"]], t["race_no"]
            )

    all_runners: list[dict] = []
    all_history: list[dict] = []
    all_meta: list[dict] = []
    results: list[RaceResult] = []

    for t in targets:
        venue = t["venue"]
        race_no = t["race_no"]
        nrid = t["numeric_race_id"]
        rr = RaceResult(venue=venue, race_no=race_no, numeric_race_id=nrid)

        print(f"\n[e2e] === {venue} {race_no}R ({nrid}) listed={t['listed']} ===")

        if not t["listed"]:
            rr.status = "UNPUBLISHED"
            rr.unpublished_reason = "race_list_not_listed"
            results.append(rr)
            continue

        if not nrid:
            rr.status = "UNPUBLISHED"
            rr.unpublished_reason = "no_numeric_race_id"
            results.append(rr)
            continue

        # --- entries ---
        try:
            html = client.fetch_shutuba(nrid)
        except NetkeibaFetchError as e:
            msg = str(e)
            if "404" in msg or "HTTP 404" in msg:
                rr.status = "UNPUBLISHED"
                rr.unpublished_reason = "shutuba_404"
            else:
                rr.status = "ERROR"
                rr.error = f"shutuba_fetch: {e}"
            results.append(rr)
            continue

        if not shutuba_has_race(html):
            rr.status = "UNPUBLISHED"
            rr.unpublished_reason = "shutuba_empty"
            results.append(rr)
            continue

        race_id = resolve_win5_race_id(date, venue, race_no, nrid)
        rr.race_id = race_id

        try:
            meta = parse_race_meta_from_shutuba(
                html, date=date, venue=venue, race_no=race_no, numeric_race_id=nrid
            )
            meta["race_id"] = race_id
            entries = parse_entries_from_shutuba(html)
        except Exception as e:
            rr.status = "ERROR"
            rr.error = f"parse_entries: {e}"
            results.append(rr)
            continue

        if not entries:
            rr.status = "UNPUBLISHED"
            rr.unpublished_reason = "entries_empty"
            results.append(rr)
            continue

        runners = []
        for e in entries:
            hid = str(e.get("horse_id") or "").strip()
            row = {
                "race_id": race_id,
                "numeric_race_id": nrid,
                "date": date,
                "course": venue,
                "race_number": race_no,
                "race_name": meta.get("race_name", ""),
                "target_surface": meta.get("surface", ""),
                "target_distance": meta.get("distance"),
                "turn": meta.get("turn", "unknown"),
                "weather": meta.get("weather", "unknown"),
                "track_condition": meta.get("track_condition", "unknown"),
                "frame_number": e.get("frame", 0),
                "horse_number": e.get("horse_number"),
                "horse_name": e.get("horse_name", ""),
                "horse_url": e.get("_horse_url", f"https://db.netkeiba.com/horse/{hid}/"),
                "horse_id": hid,
                "sex": e.get("_sex", ""),
                "age": e.get("_age"),
                "weight_carried": e.get("weight", 0.0),
                "jockey": e.get("jockey", ""),
                "odds": e.get("_odds"),
                "popularity": e.get("_popularity"),
            }
            runners.append(row)
            if hid:
                rr.horse_ids.append(hid)

        rr.entries_ok = True
        rr.entries_count = len(runners)
        all_runners.extend(runners)
        all_meta.append(meta)
        print(f"[e2e] entries: {rr.entries_count} horses, race_id={race_id}")

        # --- history ---
        race_history: list[dict] = []
        for i, row in enumerate(runners, 1):
            hid = row["horse_id"]
            hname = row["horse_name"]
            if not hid:
                rr.history_fail += 1
                rr.history_fail_reasons.append(f"{hname}: no_horse_id")
                continue
            print(f"[e2e] history {i}/{len(runners)}: {hname} ({hid})")
            try:
                parsed = fetch_horse_history(client, hid)
            except NetkeibaFetchError as e:
                rr.history_fail += 1
                rr.history_fail_reasons.append(f"{hname}({hid}): fetch {e}")
                continue
            except Exception as e:
                rr.history_fail += 1
                rr.history_fail_reasons.append(f"{hname}({hid}): {type(e).__name__}: {e}")
                continue
            if not parsed:
                rr.history_fail += 1
                rr.history_fail_reasons.append(f"{hname}({hid}): empty_history")
                continue
            rows = build_history_rows(row, parsed)
            race_history.extend(rows)
            all_history.extend(rows)
            rr.history_ok += 1
            print(f"[e2e]   {len(parsed)} history rows")

        # --- features ---
        try:
            runners_df = pd.DataFrame(runners)
            history_df = pd.DataFrame(race_history) if race_history else pd.DataFrame(columns=HISTORY_COLUMNS)
            races_df = pd.DataFrame([meta])
            features_df = build_features(runners_df, history_df, races_df)
            if features_df is None or features_df.empty:
                rr.features_ok = False
                rr.features_error = "empty_features"
            else:
                rr.features_ok = True
                # Per-race features file for FeatureLoader check
                race_feat_path = output_dir / f"features_{nrid}.csv"
                features_df.to_csv(race_feat_path, index=False, encoding="utf-8-sig")

                data_root = report_dir / "feature_loader_data"
                ok, src, nrows, err = check_feature_loader(race_feat_path, race_id, data_root)
                rr.feature_loader_ok = ok
                rr.feature_loader_source = src
                rr.feature_loader_rows = nrows
                rr.feature_loader_error = err
        except Exception as e:
            rr.features_ok = False
            rr.features_error = f"{type(e).__name__}: {e}"
            traceback.print_exc()

        rr.status = "OK" if rr.entries_ok and rr.features_ok else "ERROR"
        if rr.status == "ERROR" and not rr.error:
            rr.error = rr.features_error or "pipeline_incomplete"
        results.append(rr)

    # Write combined CSVs
    runners_df = pd.DataFrame(all_runners)
    history_df = pd.DataFrame(all_history) if all_history else pd.DataFrame(columns=HISTORY_COLUMNS)
    features_all = pd.DataFrame()
    if not runners_df.empty:
        races_df = pd.DataFrame(all_meta) if all_meta else None
        try:
            features_all = build_features(runners_df, history_df, races_df)
        except Exception as e:
            print(f"[e2e] WARNING: combined features failed: {e}")

    runners_path = output_dir / "runners.csv"
    history_path = output_dir / "horse_history_raw.csv"
    features_path = output_dir / "runners_pace_market_features.csv"
    runners_df.to_csv(runners_path, index=False, encoding="utf-8-sig")
    history_df.to_csv(history_path, index=False, encoding="utf-8-sig")
    if not features_all.empty:
        features_all.to_csv(features_path, index=False, encoding="utf-8-sig")
        # Also install for FeatureLoader daily path under win5-ai data if possible
        try:
            daily = Path(r"C:\win5-ai\data\demo_daily_outputs") / date
            daily.mkdir(parents=True, exist_ok=True)
            shutil.copy2(features_path, daily / "demo_runners_pace_market_features.csv")
            print(f"[e2e] FeatureLoader daily CSV → {daily}")
        except Exception as e:
            print(f"[e2e] daily CSV copy skipped: {e}")

    print(f"[e2e] Wrote {runners_path} ({len(runners_df)} rows)")
    print(f"[e2e] Wrote {history_path} ({len(history_df)} rows)")
    print(f"[e2e] Wrote {features_path} ({len(features_all)} rows)")

    return results


def write_report(date: str, meetings: list, results: list[RaceResult], path: Path) -> None:
    lines: list[str] = []
    lines.append(f"# PI → Prediction E2E レポート ({date})")
    lines.append("")
    lines.append("## 1. 開催一覧")
    lines.append("")
    if meetings:
        for m in meetings:
            lines.append(f"- {m.venue}（{m.kai}回 {m.day}日目, code={m.venue_code}）")
    else:
        lines.append("- （取得なし）")
    lines.append("")

    published = [r for r in results if r.status == "OK"]
    unpublished = [r for r in results if r.status == "UNPUBLISHED"]
    errors = [r for r in results if r.status == "ERROR"]

    lines.append("## サマリー")
    lines.append("")
    lines.append(f"- 公開済み・処理成功: {len(published)}")
    lines.append(f"- 未公開: {len(unpublished)}")
    lines.append(f"- システムエラー: {len(errors)}")
    lines.append("")

    lines.append("## レース別結果")
    lines.append("")

    current_venue = None
    for rr in results:
        if rr.venue != current_venue:
            current_venue = rr.venue
            lines.append(f"### {rr.venue}")
            lines.append("")
        for line in rr.summary_lines():
            lines.append(line)

    lines.append("## 詳細 JSON")
    lines.append("")
    lines.append("```json")
    payload = []
    for rr in results:
        d = asdict(rr)
        payload.append(d)
    lines.append(json.dumps(payload, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[e2e] Report → {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Day E2E PI→Prediction pipeline")
    parser.add_argument("--date", required=True)
    parser.add_argument("--venues", default="新潟,中京,札幌")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--report-dir", default=None)
    args = parser.parse_args()

    venues = [v.strip() for v in args.venues.split(",") if v.strip()]
    out = Path(args.output_dir) if args.output_dir else ROOT / "data" / "pipeline" / args.date
    report = Path(args.report_dir) if args.report_dir else ROOT / "data" / "e2e" / args.date

    # Re-fetch meetings for report header
    client = NetkeibaClient(min_interval_sec=1.0)
    list_html = client.fetch_race_list(args.date)
    meetings = parse_meetings_from_race_list(list_html)

    results = run_day(args.date, venues, out, report)

    # Print console summary in requested format
    print("\n" + "=" * 60)
    print(f"E2E RESULT {args.date}")
    print("=" * 60)
    for rr in results:
        label = f"{rr.venue}{rr.race_no}R"
        if rr.status == "UNPUBLISHED":
            print(f"\n{label}")
            print(f"未公開（{rr.unpublished_reason or 'shutuba_empty'}）")
        elif rr.status == "ERROR":
            print(f"\n{label}")
            print(f"ERROR: {rr.error}")
        else:
            print(f"\n{label}")
            print(f"entries: OK ({rr.entries_count}頭, race_id={rr.race_id})")
            print(f"history: {rr.history_ok}/{rr.entries_count}")
            print(f"features: {'OK' if rr.features_ok else 'NG'}")
            print(f"FeatureLoader: {'OK' if rr.feature_loader_ok else 'NG'}")

    write_report(args.date, meetings, results, report / "e2e_report.md")
    (report / "e2e_results.json").write_text(
        json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
