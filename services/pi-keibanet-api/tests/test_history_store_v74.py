# -*- coding: utf-8 -*-
"""Version7.4 History store / CSV-first tests (PE/CE untouched)."""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pi_keibanet.history_store import (
    CompositeHistoryStore,
    CsvHistoryStore,
    is_weekend_jst,
)
from pi_keibanet.service import PiKeibaNetService


class WeekendHelperTest(unittest.TestCase):
    def test_weekend_detection(self):
        self.assertTrue(is_weekend_jst("2026-07-26"))  # Sun
        self.assertTrue(is_weekend_jst("2026-07-25"))  # Sat
        self.assertFalse(is_weekend_jst("2026-07-24"))  # Fri


class CsvHistoryStoreTest(unittest.TestCase):
    def test_load_race_rows_from_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            day = Path(tmp) / "2026-07-26"
            day.mkdir()
            hist = day / "horse_history_raw.csv"
            with hist.open("w", encoding="utf-8-sig", newline="") as fh:
                w = csv.DictWriter(
                    fh,
                    fieldnames=[
                        "race_id",
                        "horse_id",
                        "horse_number",
                        "horse_name",
                        "history_date",
                        "history_place",
                        "history_race_name",
                        "history_finish",
                        "history_odds",
                        "history_distance",
                        "history_surface",
                        "history_last3f",
                    ],
                )
                w.writeheader()
                w.writerow(
                    {
                        "race_id": "2026-07-26-01-07",
                        "horse_id": "2021104893",
                        "horse_number": "1",
                        "horse_name": "テスト馬",
                        "history_date": "26/06/21",
                        "history_place": "阪神",
                        "history_race_name": "しらさぎS",
                        "history_finish": "9",
                        "history_odds": "6.3",
                        "history_distance": "1600",
                        "history_surface": "芝",
                        "history_last3f": "34.6",
                    }
                )

            store = CsvHistoryStore()
            with mock.patch(
                "pi_keibanet.history_store._refresh_paths",
                return_value=(hist, day / "runners.csv"),
            ):
                rows = store.load_race_rows("2026-07-26-01-07", date="2026-07-26")
            self.assertIsNotNone(rows)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["horse_id"], "2021104893")

    def test_missing_csv_returns_none(self):
        store = CsvHistoryStore()
        missing = Path("/tmp/definitely-missing-v74/horse_history_raw.csv")
        with mock.patch(
            "pi_keibanet.history_store._refresh_paths",
            return_value=(missing, missing.parent / "runners.csv"),
        ):
            self.assertIsNone(store.load_race_rows("2026-07-26-01-01", date="2026-07-26"))


class GroupFromRowsTest(unittest.TestCase):
    def test_group_preserves_contract(self):
        svc = PiKeibaNetService.__new__(PiKeibaNetService)
        rows = [
            {
                "horse_id": "2021104893",
                "horse_number": "1",
                "horse_name": "ファーヴェント",
                "history_date": "26/06/21",
                "history_place": "阪神",
                "history_race_name": "しらさぎS",
                "history_finish": "9",
                "history_odds": "6.3",
                "history_distance": "1600",
                "history_surface": "芝",
                "history_last3f": "34.6",
            }
        ]
        entries = [
            {"horse_id": "2021104893", "horse_number": 1, "horse_name": "ファーヴェント"},
            {"horse_id": "2022100001", "horse_number": 2, "horse_name": "新馬"},
        ]
        out = svc._history_grouped_from_rows(rows, entries=entries, limit=3)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["horse_number"], 1)
        self.assertEqual(len(out[0]["recent"]), 1)
        self.assertEqual(out[0]["recent"][0]["race_name"], "しらさぎS")
        self.assertEqual(out[1]["horse_number"], 2)
        self.assertEqual(out[1]["recent"], [])


class CompositeOrderTest(unittest.TestCase):
    def test_csv_before_db(self):
        csv_store = mock.Mock()
        csv_store.name = "csv"
        csv_store.load_race_rows.return_value = [{"horse_id": "1"}]
        db_store = mock.Mock()
        db_store.name = "db"
        db_store.load_race_rows.return_value = [{"horse_id": "2"}]
        store = CompositeHistoryStore(csv_store=csv_store, db_store=db_store)
        rows, source = store.resolve_static("r1", date="2026-07-26")
        self.assertEqual(source, "csv")
        self.assertEqual(rows[0]["horse_id"], "1")
        db_store.load_race_rows.assert_not_called()


if __name__ == "__main__":
    unittest.main()
