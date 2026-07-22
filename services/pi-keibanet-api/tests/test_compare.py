# -*- coding: utf-8 -*-
"""Tests for Win5AI vs PI compare module."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.compare import (
    CAUSE_FEATURE,
    CAUSE_MISSING,
    CAUSE_NETKEIBA,
    CAUSE_PARSE,
    compare_all,
    compare_dataset,
    write_diff_csv,
    write_report_md,
    _values_equal,
)


class ValuesEqualTest(unittest.TestCase):
    def test_numeric_close(self):
        eq, diff, _ = _values_equal("odds", 14.3, 14.31)
        self.assertTrue(eq)

    def test_url_normalize(self):
        eq, _, _ = _values_equal(
            "horse_url",
            "https://db.netkeiba.com/horse/2022103522",
            "https://db.netkeiba.com/horse/2022103522/",
        )
        self.assertTrue(eq)

    def test_date_normalize(self):
        eq, _, _ = _values_equal("history_date", "2026/06/01", "2026-06-01")
        self.assertTrue(eq)

    def test_string_mismatch(self):
        eq, _, _ = _values_equal("jockey", "菊沢", "柴田")
        self.assertFalse(eq)


class CompareDatasetTest(unittest.TestCase):
    def _make_runners(self, horse_id: str, jockey: str = "菊沢") -> dict:
        return {
            "numeric_race_id": "202603020810",
            "horse_id": horse_id,
            "horse_name": "テスト馬",
            "horse_number": 1,
            "frame_number": 1,
            "jockey": jockey,
            "odds": 14.3,
            "popularity": 5,
            "sex": "牡",
            "age": 4,
            "weight_carried": 58.0,
        }

    def test_perfect_match(self):
        legacy = pd.DataFrame([self._make_runners("2022103522")])
        pi = pd.DataFrame([self._make_runners("2022103522")])
        report = compare_dataset("runners", legacy, pi)
        self.assertEqual(report.match_rate, 1.0)
        self.assertEqual(len(report.diffs), 0)

    def test_parse_diff(self):
        legacy = pd.DataFrame([self._make_runners("2022103522", jockey="菊沢")])
        pi = pd.DataFrame([self._make_runners("2022103522", jockey="柴田")])
        report = compare_dataset("runners", legacy, pi)
        self.assertLess(report.match_rate, 1.0)
        jockey_diffs = [d for d in report.diffs if d.column == "jockey"]
        self.assertEqual(len(jockey_diffs), 1)
        self.assertEqual(jockey_diffs[0].cause, CAUSE_PARSE)

    def test_horse_id_only_legacy(self):
        legacy = pd.DataFrame([
            self._make_runners("2022103522"),
            self._make_runners("2022104781"),
        ])
        pi = pd.DataFrame([self._make_runners("2022103522")])
        report = compare_dataset("runners", legacy, pi)
        horse_diffs = [d for d in report.diffs if d.column == "(horse_id)"]
        self.assertEqual(len(horse_diffs), 1)
        self.assertEqual(horse_diffs[0].cause, CAUSE_NETKEIBA)

    def test_feature_diff(self):
        legacy = pd.DataFrame([{
            "numeric_race_id": "202603020810",
            "horse_id": "2022103522",
            "history_count": 20,
            "last_finish": 6.0,
            "history_score": 0.765704,
            "running_style": "先行",
        }])
        pi = pd.DataFrame([{
            "numeric_race_id": "202603020810",
            "horse_id": "2022103522",
            "history_count": 20,
            "last_finish": 7.0,
            "history_score": 0.765704,
            "running_style": "先行",
        }])
        report = compare_dataset("runners_pace_market_features", legacy, pi)
        finish_diffs = [d for d in report.diffs if d.column == "last_finish"]
        self.assertEqual(len(finish_diffs), 1)
        self.assertEqual(finish_diffs[0].cause, CAUSE_FEATURE)

    def test_history_join_by_date_name(self):
        legacy = pd.DataFrame([
            {
                "horse_id": "H1",
                "history_index": 0,
                "history_date": "2026/06/01",
                "history_race_name": "皐月賞",
                "history_finish": 2,
            },
            {
                "horse_id": "H1",
                "history_index": 1,
                "history_date": "2026/04/15",
                "history_race_name": "弥生賞",
                "history_finish": 1,
            },
        ])
        pi = pd.DataFrame([
            {
                "horse_id": "H1",
                "history_index": 5,
                "history_date": "2026-06-01",
                "history_race_name": "皐月賞",
                "history_finish": 2,
            },
            {
                "horse_id": "H1",
                "history_index": 9,
                "history_date": "2026/04/15",
                "history_race_name": "弥生賞",
                "history_finish": 1,
            },
        ])
        report = compare_dataset("horse_history_raw", legacy, pi)
        self.assertEqual(report.match_rate, 1.0)


class CompareAllTest(unittest.TestCase):
    def test_end_to_end_with_temp_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            legacy_dir = tmp_path / "legacy"
            pi_dir = tmp_path / "pi"
            legacy_dir.mkdir()
            pi_dir.mkdir()

            nrid = "202603020810"
            runners = pd.DataFrame([{
                "race_id": "2026-07-19-01-10",
                "numeric_race_id": nrid,
                "date": "2026-07-19",
                "course": "福島",
                "race_number": 10,
                "horse_id": "2022103522",
                "horse_name": "ジェットブレード",
                "jockey": "菊沢",
                "odds": 14.3,
                "popularity": 5,
                "frame_number": 1,
                "horse_number": 1,
                "sex": "牡",
                "age": 4,
                "weight_carried": 58.0,
            }])
            runners.to_csv(legacy_dir / "runners.csv", index=False)
            runners.to_csv(pi_dir / "runners.csv", index=False)

            history = pd.DataFrame([{
                "numeric_race_id": nrid,
                "horse_id": "2022103522",
                "history_index": 0,
                "history_date": "2026/05/01",
                "history_race_name": "テストレース",
                "history_finish": 3,
                "history_surface": "芝",
                "history_distance": 2000,
            }])
            history.to_csv(legacy_dir / "horse_history_raw.csv", index=False)
            history.to_csv(pi_dir / "horse_history_raw.csv", index=False)

            features = pd.DataFrame([{
                "numeric_race_id": nrid,
                "horse_id": "2022103522",
                "history_count": 20,
                "last_finish": 6.0,
                "history_score": 0.76,
                "running_style": "先行",
            }])
            features.to_csv(legacy_dir / "runners_pace_market_features.csv", index=False)
            features.to_csv(pi_dir / "runners_pace_market_features.csv", index=False)

            result = compare_all(
                date="2026-07-19",
                venue="福島",
                race_no=10,
                legacy_dir=legacy_dir,
                pi_dir=pi_dir,
                normalize_legacy=False,
            )

            self.assertEqual(result.numeric_race_id, nrid)
            self.assertGreaterEqual(result.overall_match_rate, 0.99)
            self.assertTrue(result.passes_target)

            out_dir = tmp_path / "report"
            write_report_md(result, out_dir / "compare_report.md", legacy_dir=legacy_dir, pi_dir=pi_dir)
            write_diff_csv(result, out_dir / "compare_diff.csv")

            self.assertTrue((out_dir / "compare_report.md").exists())
            report_text = (out_dir / "compare_report.md").read_text(encoding="utf-8")
            self.assertIn("PASS", report_text)
            self.assertIn("runners", report_text)


if __name__ == "__main__":
    unittest.main()
