# -*- coding: utf-8 -*-
"""PC-3B Training Dataset Builder tests."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from tests.ops.helpers import isolated_env


class TrainingDatasetBuilderTest(unittest.TestCase):
    def _write_source(self, root: Path, name: str) -> None:
        feat = pd.DataFrame(
            [
                {"race_id": "2026-01-01-01-01", "horse_name": "馬A", "pace_score": 1.0},
                {"race_id": "2026-01-01-01-01", "horse_name": "馬B", "pace_score": 2.0},
                {"race_id": "2026-01-02-01-01", "horse_name": "馬C", "pace_score": 1.5},
            ]
        )
        result = pd.DataFrame(
            [
                {
                    "race_id": "2026-01-01-01-01",
                    "horse_name": "馬A",
                    "finish_rank": 1,
                    "target_win": 1,
                    "result_date": "2026-01-01",
                },
                {
                    "race_id": "2026-01-01-01-01",
                    "horse_name": "馬B",
                    "finish_rank": 2,
                    "target_win": 0,
                    "result_date": "2026-01-01",
                },
                {
                    "race_id": "2026-01-02-01-01",
                    "horse_name": "馬C",
                    "finish_rank": 1,
                    "target_win": 1,
                    "result_date": "2026-01-02",
                },
            ]
        )
        prefix = "" if name == "main" else "demo_"
        feat.to_csv(root / f"{prefix}runners_pace_market_features.csv", index=False)
        result.to_csv(root / f"{prefix}win5_resultwithdate.csv", index=False)

    def test_build_splits_and_report(self):
        with isolated_env(), tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            self._write_source(data_dir, "main")
            out_dir = Path(tmp) / "training"

            from app.data.training.dataset_builder import SourceSpec, TrainingDatasetBuilder

            builder = TrainingDatasetBuilder(data_dir=data_dir)
            builder.output_dir = out_dir
            result = builder.build(
                sources=[
                    SourceSpec(
                        "main",
                        data_dir / "runners_pace_market_features.csv",
                        data_dir / "win5_resultwithdate.csv",
                    )
                ],
                min_rows_for_training=2,
            )
            self.assertTrue(result.report["ready_for_training"])
            self.assertEqual(result.report["totals"]["rows"], 3)
            self.assertEqual(len(result.train) + len(result.validation) + len(result.test), 3)
            self.assertTrue((out_dir / "dataset_report.json").exists())


if __name__ == "__main__":
    unittest.main()
