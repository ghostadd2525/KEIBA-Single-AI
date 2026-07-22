# -*- coding: utf-8 -*-
"""Tests for horse_history parser and features builder (Win5AI compatibility)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.netkeiba.horse_history import (
    OUT_COLUMNS,
    build_history_rows,
    parse_history_table_html,
)


SAMPLE_HORSE_TABLE = """
<table class="db_h_race_results">
<tr><th>日付</th><th>開催</th><th>レース名</th><th>クラス</th><th>枠</th><th>馬番</th>
<th>距離</th><th>馬場</th><th>着順</th><th>人気</th><th>オッズ</th>
<th>上り3F</th><th>着差</th><th>斤量</th><th>通過</th><th>タイム</th>
<th>騎手</th><th>馬体重</th><th>天気</th></tr>
<tr><td>2026/06/01</td><td>東京</td><td>皐月賞</td><td>GI</td><td>3</td><td>5</td>
<td>芝2000</td><td>良</td><td>2</td><td>1</td><td>2.5</td>
<td>33.8</td><td>0.1</td><td>57</td><td>3-3-2-2</td><td>2:00.5</td>
<td>ルメール</td><td>480(+2)</td><td>晴</td></tr>
<tr><td>2026/04/15</td><td>中山</td><td>弥生賞</td><td>GII</td><td>5</td><td>8</td>
<td>芝2000</td><td>稍重</td><td>1</td><td>2</td><td>4.1</td>
<td>34.2</td><td>0.0</td><td>56</td><td>4-4-3-3</td><td>2:01.8</td>
<td>戸崎</td><td>478(0)</td><td>曇</td></tr>
<tr><td>2026/02/10</td><td>東京</td><td>共同通信杯</td><td>GIII</td><td>1</td><td>2</td>
<td>芝1800</td><td>良</td><td>3</td><td>5</td><td>12.0</td>
<td>34.5</td><td>0.3</td><td>56</td><td>6-5-4-4</td><td>1:48.2</td>
<td>横山武</td><td>476(-4)</td><td>晴</td></tr>
</table>
"""


class HorseHistoryParserTest(unittest.TestCase):
    def test_parse_basic(self):
        rows = parse_history_table_html(SAMPLE_HORSE_TABLE)
        self.assertEqual(len(rows), 3)

    def test_columns_match_legacy(self):
        rows = parse_history_table_html(SAMPLE_HORSE_TABLE)
        r = rows[0]
        for col in [
            "history_date", "history_place", "history_race_name", "history_class",
            "history_finish", "history_popularity", "history_odds",
            "history_last3f", "history_distance", "history_surface",
            "history_course_condition", "history_time", "history_jockey",
            "history_horse_weight", "history_weather",
            "corner1", "corner2", "corner3", "corner4",
        ]:
            self.assertIn(col, r, f"Missing column: {col}")

    def test_finish_parsed_as_int(self):
        rows = parse_history_table_html(SAMPLE_HORSE_TABLE)
        self.assertEqual(rows[0]["history_finish"], 2)
        self.assertEqual(rows[1]["history_finish"], 1)

    def test_distance_parsed(self):
        rows = parse_history_table_html(SAMPLE_HORSE_TABLE)
        self.assertEqual(rows[0]["history_distance"], 2000)
        self.assertEqual(rows[0]["history_surface"], "芝")

    def test_corner_positions(self):
        rows = parse_history_table_html(SAMPLE_HORSE_TABLE)
        self.assertEqual(rows[0]["corner4"], 2.0)
        self.assertEqual(rows[0]["corner1"], 3.0)

    def test_build_history_rows_attaches_context(self):
        parsed = parse_history_table_html(SAMPLE_HORSE_TABLE)
        runner = {
            "race_id": "20260701_10_東京",
            "numeric_race_id": "202605030110",
            "date": "2026-07-01",
            "venue": "東京",
            "race_no": 10,
            "horse_number": 5,
            "horse_name": "テスト馬",
            "horse_id": "2024100001",
            "_horse_url": "https://db.netkeiba.com/horse/2024100001/",
            "_sex": "牡",
            "_age": 3,
            "weight": 57.0,
            "jockey": "ルメール",
        }
        rows = build_history_rows(runner, parsed)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["horse_name"], "テスト馬")
        self.assertEqual(rows[0]["horse_id"], "2024100001")
        self.assertEqual(rows[0]["history_index"], 0)
        for col in OUT_COLUMNS:
            self.assertIn(col, rows[0], f"Missing OUT_COLUMNS entry: {col}")

    def test_fetch_horse_history_uses_ajax_json(self):
        import json
        from pi_keibanet.netkeiba.horse_history import fetch_horse_history

        class MockClient:
            def fetch(self, url, *, label=""):
                self.last_url = url
                frag = SAMPLE_HORSE_TABLE
                return json.dumps({"status": "OK", "data": frag})

        client = MockClient()
        rows = fetch_horse_history(client, "2022103522")
        self.assertIn("ajax_horse_results.html", client.last_url)
        self.assertIn("id=2022103522", client.last_url)
        self.assertEqual(len(rows), 3)


class FeaturesBuilderTest(unittest.TestCase):
    def test_build_features_basic(self):
        import pandas as pd
        from pi_keibanet.features import build_features

        runners = pd.DataFrame([{
            "race_id": "20260701_10_東京",
            "horse_id": "2024100001",
            "horse_name": "テスト馬",
            "horse_number": 5,
            "frame_number": 3,
            "date": "2026-07-01",
            "target_distance": 2000,
            "target_surface": "芝",
            "weight_carried": 57.0,
            "jockey": "ルメール",
            "odds": 2.5,
            "popularity": 1,
        }])

        history = pd.DataFrame([
            {"horse_id": "2024100001", "history_date": "2026/06/01",
             "history_finish": 2, "history_distance": 2000, "history_surface": "芝",
             "history_passing": "3-3-2-2", "history_race_name": "皐月賞", "history_class": "GI",
             "corner4": 2.0},
            {"horse_id": "2024100001", "history_date": "2026/04/15",
             "history_finish": 1, "history_distance": 2000, "history_surface": "芝",
             "history_passing": "4-4-3-3", "history_race_name": "弥生賞", "history_class": "GII",
             "corner4": 3.0},
            {"horse_id": "2024100001", "history_date": "2026/02/10",
             "history_finish": 3, "history_distance": 1800, "history_surface": "芝",
             "history_passing": "6-5-4-4", "history_race_name": "共同通信杯", "history_class": "GIII",
             "corner4": 4.0},
        ])

        result = build_features(runners, history)
        self.assertEqual(len(result), 1)

        row = result.iloc[0]
        self.assertEqual(row["history_count"], 3)
        self.assertEqual(row["last_finish"], 2)
        self.assertAlmostEqual(row["last3_avg_finish"], 2.0, places=1)
        self.assertAlmostEqual(row["avg_finish"], 2.0, places=1)
        self.assertIn(row["running_style"], ["逃げ", "先行", "差し", "追込"])
        self.assertGreater(row["history_score"], 0)
        self.assertGreater(row["distance_score"], 0)
        self.assertIn("grade_points_last3", result.columns)
        self.assertIn("pace_collapse_risk_v2", result.columns)
        self.assertIn("gate_risk_score", result.columns)

    def test_feature_columns_match_model_schema(self):
        """Verify all 28 model features are present in output."""
        import pandas as pd
        from pi_keibanet.features import build_features

        runners = pd.DataFrame([{
            "race_id": "R1", "horse_id": "H1", "horse_name": "A",
            "horse_number": 1, "frame_number": 1,
            "date": "2026-01-01", "target_distance": 1600, "target_surface": "芝",
        }])
        history = pd.DataFrame(columns=[
            "horse_id", "history_date", "history_finish", "history_distance",
            "history_surface", "history_passing", "history_race_name", "history_class",
        ])

        result = build_features(runners, history)

        model_features = [
            "horse_number", "history_count", "history_score", "distance_score",
            "grade_points_last3", "grade_distance_style_points_last3",
            "stayer_grade_points_last3", "style_distance_fit_weight",
            "style_confidence", "front_rate", "last_finish", "last3_avg_finish",
            "avg_finish", "same_distance_count", "same_distance_avg_finish",
            "same_surface_count", "same_surface_avg_finish",
            "pace_collapse_risk_v2", "gate_risk_score",
            "running_style",
        ]
        for f in model_features:
            self.assertIn(f, result.columns, f"Missing model feature: {f}")


if __name__ == "__main__":
    unittest.main()
