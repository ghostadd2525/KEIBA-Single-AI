# -*- coding: utf-8 -*-
"""Horse number integrity gate tests — ready vs not-ready."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.horse_number_integrity import (
    REASON_HORSE_NUMBER_NOT_READY,
    validate_runners_horse_number_integrity,
)
from pi_keibanet.race_refresh import (
    HorseNumberNotReadyError,
    RefreshConfig,
    write_daily_features,
)


class HorseNumberIntegrityValidateTest(unittest.TestCase):
    def test_ready_when_formal_umaban_present(self) -> None:
        runners = [
            {
                "race_id": "2026-07-26-01-01",
                "horse_id": "2024101281",
                "horse_number": 1,
                "horse_number_source": "umaban",
                "frame_number": 1,
                "horse_name": "ドルチェテソーロ",
            },
            {
                "race_id": "2026-07-26-01-01",
                "horse_id": "2024106131",
                "horse_number": 4,
                "horse_number_source": "umaban",
                "frame_number": 2,
                "horse_name": "ブラックミューズ",
            },
        ]
        report = validate_runners_horse_number_integrity(runners, date="2026-07-26")
        self.assertTrue(report.ok)
        self.assertEqual(report.ready_race_ids, ["2026-07-26-01-01"])
        self.assertEqual(report.blocked_race_ids, [])

    def test_blocked_when_horse_number_missing(self) -> None:
        runners = [
            {
                "race_id": "R-MISS",
                "horse_id": "H1",
                "horse_number": None,
                "horse_number_source": None,
                "frame_number": 0,
                "horse_name": "未確定馬",
                "display_order": 1,
            }
        ]
        report = validate_runners_horse_number_integrity(runners, date="2026-07-26")
        self.assertFalse(report.ok)
        self.assertEqual(report.blocked_race_ids, ["R-MISS"])
        self.assertIn(REASON_HORSE_NUMBER_NOT_READY, report.races[0].reasons)

    def test_blocked_when_fallback_source(self) -> None:
        runners = [
            {
                "race_id": "R-FALLBACK",
                "horse_id": "H1",
                "horse_number": 1,
                "horse_number_source": "fallback",
                "frame_number": 1,
                "horse_name": "連番馬",
            }
        ]
        report = validate_runners_horse_number_integrity(runners, date="2026-07-26")
        self.assertFalse(report.ok)
        self.assertEqual(report.blocked_race_ids, ["R-FALLBACK"])


class WriteDailyFeaturesGateTest(unittest.TestCase):
    @patch("pi_keibanet.race_refresh.build_features")
    def test_ready_generates_features(self, mock_build) -> None:
        mock_build.return_value = pd.DataFrame(
            [
                {
                    "race_id": "R-OK",
                    "horse_id": "H1",
                    "horse_number": 1,
                    "horse_name": "正式馬",
                    "history_score": 0.5,
                }
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            cfg = RefreshConfig(data_root=Path(tmp) / "data", state_root=Path(tmp) / "state")
            (cfg.data_root / "demo_daily_outputs" / "2026-07-26").mkdir(parents=True, exist_ok=True)
            runners = pd.DataFrame(
                [
                    {
                        "race_id": "R-OK",
                        "horse_id": "H1",
                        "horse_number": 1,
                        "horse_number_source": "umaban",
                        "frame_number": 1,
                        "horse_name": "正式馬",
                        "date": "2026-07-26",
                    }
                ]
            )
            history = pd.DataFrame(columns=["race_id", "horse_id"])
            out = write_daily_features(
                cfg,
                "2026-07-26",
                runners,
                history,
                updated_race_ids={"R-OK"},
            )
            self.assertTrue(out.is_file())
            feat = pd.read_csv(out, encoding="utf-8-sig")
            self.assertEqual(len(feat), 1)
            self.assertEqual(int(feat.iloc[0]["horse_number"]), 1)
            mock_build.assert_called_once()

    @patch("pi_keibanet.race_refresh.build_features")
    def test_missing_horse_number_skips_feature_generation(self, mock_build) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = RefreshConfig(data_root=Path(tmp) / "data", state_root=Path(tmp) / "state")
            daily = cfg.data_root / "demo_daily_outputs" / "2026-07-26"
            daily.mkdir(parents=True, exist_ok=True)
            # Existing stale feature row for the blocked race must be purged.
            pd.DataFrame(
                [
                    {
                        "race_id": "R-NG",
                        "horse_id": "H9",
                        "horse_number": 9,
                        "horse_name": "旧データ",
                    },
                    {
                        "race_id": "R-KEEP",
                        "horse_id": "H2",
                        "horse_number": 2,
                        "horse_name": "他レース",
                    },
                ]
            ).to_csv(daily / "demo_runners_pace_market_features.csv", index=False, encoding="utf-8-sig")

            runners = pd.DataFrame(
                [
                    {
                        "race_id": "R-NG",
                        "horse_id": "H1",
                        "horse_number": None,
                        "horse_number_source": None,
                        "frame_number": 0,
                        "horse_name": "未確定",
                        "display_order": 1,
                        "date": "2026-07-26",
                    }
                ]
            )
            history = pd.DataFrame(columns=["race_id", "horse_id"])
            with self.assertRaises(HorseNumberNotReadyError):
                write_daily_features(
                    cfg,
                    "2026-07-26",
                    runners,
                    history,
                    updated_race_ids={"R-NG"},
                )
            mock_build.assert_not_called()
            feat = pd.read_csv(daily / "demo_runners_pace_market_features.csv", encoding="utf-8-sig")
            self.assertNotIn("R-NG", set(feat["race_id"].astype(str)))
            self.assertIn("R-KEEP", set(feat["race_id"].astype(str)))


if __name__ == "__main__":
    unittest.main()
