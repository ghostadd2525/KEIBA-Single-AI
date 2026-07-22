# -*- coding: utf-8 -*-
"""Tests for production race refresh (Phase A)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.race_refresh import (
    RefreshConfig,
    RaceSnapshotEntry,
    compute_entries_fingerprint,
    in_refresh_window,
    load_snapshot,
    merge_day_frames,
    run_refresh,
    save_snapshot,
    select_races_for_update,
    write_report_json,
)


class RefreshWindowTest(unittest.TestCase):
    def test_inside_window(self):
        now = datetime(2026, 7, 21, 10, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        self.assertTrue(in_refresh_window(now, start_hour=8, end_hour=20))

    def test_outside_window(self):
        now = datetime(2026, 7, 21, 21, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
        self.assertFalse(in_refresh_window(now, start_hour=8, end_hour=20))


class FingerprintTest(unittest.TestCase):
    def test_same_entries_same_fingerprint(self):
        entries = [
            {"horse_id": "H1", "horse_number": 1, "_odds": 2.5, "_popularity": 1, "jockey": "A", "weight": 57},
            {"horse_id": "H2", "horse_number": 2, "_odds": 5.0, "_popularity": 2, "jockey": "B", "weight": 55},
        ]
        self.assertEqual(
            compute_entries_fingerprint(entries),
            compute_entries_fingerprint(list(reversed(entries))),
        )

    def test_odds_change_changes_fingerprint(self):
        base = [{"horse_id": "H1", "horse_number": 1, "_odds": 2.5, "_popularity": 1, "jockey": "A", "weight": 57}]
        changed = [{"horse_id": "H1", "horse_number": 1, "_odds": 3.0, "_popularity": 1, "jockey": "A", "weight": 57}]
        self.assertNotEqual(compute_entries_fingerprint(base), compute_entries_fingerprint(changed))


class SnapshotTest(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = RefreshConfig(
                data_root=Path(tmp) / "data",
                state_root=Path(tmp) / "state",
            )
            snap = {
                "2026-07-25-01-06": RaceSnapshotEntry(
                    race_id="2026-07-25-01-06",
                    numeric_race_id="202607250106",
                    course="新潟",
                    race_number=6,
                    fingerprint="abc123",
                    features_ok=True,
                    updated_at="2026-07-21T10:00:00+09:00",
                )
            }
            save_snapshot(cfg, "2026-07-25", snap)
            loaded = load_snapshot(cfg, "2026-07-25")
            self.assertEqual(loaded["2026-07-25-01-06"].fingerprint, "abc123")
            self.assertTrue(loaded["2026-07-25-01-06"].features_ok)


class DiffSelectionTest(unittest.TestCase):
    def _published(self, race_id: str, fp: str) -> dict:
        return {
            "race_id": race_id,
            "numeric_race_id": "N1",
            "course": "新潟",
            "race_number": 6,
            "entries": [{"horse_id": "H1", "horse_number": 1}],
            "fingerprint": fp,
        }

    def test_new_race_selected(self):
        published = [{"race_id": "R1", "entries": [{"horse_id": "H1", "horse_number": 1}]}]
        to_update, unchanged = select_races_for_update(published, {})
        self.assertEqual(len(to_update), 1)
        self.assertEqual(unchanged, 0)

    def test_unchanged_skipped(self):
        fp = compute_entries_fingerprint([{"horse_id": "H1", "horse_number": 1}])
        published = [{"race_id": "R1", "entries": [{"horse_id": "H1", "horse_number": 1}]}]
        snapshot = {
            "R1": RaceSnapshotEntry(
                race_id="R1",
                numeric_race_id="N1",
                course="新潟",
                race_number=6,
                fingerprint=fp,
                features_ok=True,
            )
        }
        to_update, unchanged = select_races_for_update(published, snapshot)
        self.assertEqual(len(to_update), 0)
        self.assertEqual(unchanged, 1)


class MergeFramesTest(unittest.TestCase):
    def test_replace_race_id_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = RefreshConfig(
                data_root=Path(tmp) / "data",
                state_root=Path(tmp) / "state",
            )
            date = "2026-07-25"
            (cfg.state_root / date).mkdir(parents=True, exist_ok=True)
            old_runners = pd.DataFrame([
                {"race_id": "R1", "horse_id": "H1", "horse_number": 1},
                {"race_id": "R2", "horse_id": "H9", "horse_number": 9},
            ])
            old_runners.to_csv(cfg.state_root / date / "runners.csv", index=False)

            new_runners = [{"race_id": "R1", "horse_id": "H2", "horse_number": 2}]
            runners_df, _ = merge_day_frames(cfg, date, {"R1"}, new_runners, [])
            ids = set(runners_df["race_id"].astype(str))
            self.assertIn("R1", ids)
            self.assertIn("R2", ids)
            r1 = runners_df[runners_df["race_id"] == "R1"]
            self.assertEqual(str(r1.iloc[0]["horse_id"]), "H2")


class RunRefreshIntegrationTest(unittest.TestCase):
    def test_outside_window_skips_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = RefreshConfig(
                data_root=Path(tmp) / "data",
                state_root=Path(tmp) / "state",
            )
            now = datetime(2026, 7, 21, 22, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
            report = run_refresh("2026-07-25", config=cfg, now=now, force=False)
            self.assertFalse(report.in_window)
            self.assertEqual(report.updated_count, 0)

    @patch("pi_keibanet.race_refresh.verify_feature_loader", return_value=[])
    @patch("pi_keibanet.race_refresh.process_race_pipeline")
    @patch("pi_keibanet.race_refresh.discover_published_races")
    @patch("pi_keibanet.race_refresh.build_features")
    def test_refresh_updates_features(
        self,
        mock_build_features,
        mock_discover,
        mock_process,
        _mock_verify,
    ):
        entries = [{"horse_id": "H1", "horse_number": 1, "_odds": 2.0, "_popularity": 1, "jockey": "A", "weight": 57}]
        published = [{
            "race_id": "2026-07-25-01-06",
            "numeric_race_id": "202607250106",
            "course": "新潟",
            "race_number": 6,
            "race_name": "テスト",
            "entries": entries,
            "shutuba_html": "<html></html>",
        }]
        mock_discover.return_value = ([MagicMock()], published, 2)
        mock_process.return_value = (
            [{"race_id": "2026-07-25-01-06", "horse_id": "H1", "horse_number": 1, "date": "2026-07-25"}],
            [],
            {},
        )
        mock_build_features.return_value = pd.DataFrame([
            {"race_id": "2026-07-25-01-06", "horse_id": "H1", "horse_number": 1, "history_count": 1}
        ])

        with tempfile.TemporaryDirectory() as tmp:
            cfg = RefreshConfig(
                data_root=Path(tmp) / "data",
                state_root=Path(tmp) / "state",
            )
            now = datetime(2026, 7, 21, 10, 0, tzinfo=ZoneInfo("Asia/Tokyo"))
            report = run_refresh("2026-07-25", config=cfg, now=now, force=True)
            self.assertEqual(report.updated_count, 1)
            self.assertEqual(report.skipped_unpublished, 2)
            self.assertEqual(report.features_generated, 1)
            daily = cfg.data_root / "demo_daily_outputs" / "2026-07-25" / "demo_runners_pace_market_features.csv"
            self.assertTrue(daily.is_file())
            json_path = write_report_json(report, cfg)
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["updated_count"], 1)


if __name__ == "__main__":
    unittest.main()
