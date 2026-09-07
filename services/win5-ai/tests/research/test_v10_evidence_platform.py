# -*- coding: utf-8 -*-
"""Version10 Research Evidence Platform tests."""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.research.anti_leak import accept_observation, anti_leak_ok
from app.research.collector.assembler import assemble_snapshot
from app.research.collector.phase1 import collect_phase1_from_board
from app.research.config import evidence_root, repo_root
from app.research.quality import compute_runner_feature_metrics


class AntiLeakTests(unittest.TestCase):
    def test_rejects_future_observation(self):
        pred = "2026-07-26T10:00:00+09:00"
        obs = "2026-07-26T11:00:00+09:00"
        self.assertFalse(anti_leak_ok(observed_at=obs, prediction_created_at=pred))
        val, _, reason = accept_observation(value=5.6, observed_at=obs, prediction_created_at=pred)
        self.assertIsNone(val)
        self.assertEqual(reason, "anti_leak_rejected")

    def test_accepts_past_observation(self):
        pred = "2026-07-26T11:00:00+09:00"
        obs = "2026-07-26T10:00:00+09:00"
        val, out_obs, reason = accept_observation(value=3.2, observed_at=obs, prediction_created_at=pred)
        self.assertEqual(val, 3.2)
        self.assertEqual(out_obs, obs)
        self.assertIsNone(reason)


class Phase1CollectorTests(unittest.TestCase):
    def test_collects_market_and_trainer(self):
        board = {
            "odds_updated_at": "2026-07-26T09:00:00+09:00",
            "entries": [
                {"horse_number": 1, "odds": 2.5, "popularity": 1, "trainer": "A厩舎"},
                {"horse_number": 2, "odds": 5.0, "popularity": 2, "trainer": "B厩舎"},
            ],
        }
        runners, _, violations = collect_phase1_from_board(
            board=board,
            prediction_created_at="2026-07-26T10:00:00+09:00",
            fetched_at="2026-07-26T09:30:00+09:00",
        )
        self.assertEqual(violations, 0)
        self.assertEqual(len(runners), 2)
        r1 = next(r for r in runners if r["horse_number"] == 1)
        self.assertEqual(r1["win_odds"], 2.5)
        self.assertEqual(r1["popularity"], 1)
        self.assertEqual(r1["trainer"], "A厩舎")
        self.assertEqual(r1["expected_popularity"], 1)


class AssemblerTests(unittest.TestCase):
    def test_partial_when_odds_missing(self):
        job = {
            "job_id": "j1",
            "prediction_id": 1,
            "race_id": "2026-07-26-01-02",
            "prediction_created_at": "2026-07-26T10:00:00+09:00",
            "attempt": 1,
        }
        runners = [{"horse_number": 1, "trainer": "X", "popularity": None, "win_odds": None, "expected_popularity": None, "missing": []}]
        payload = assemble_snapshot(job=job, runners=runners, sources=[], anti_leak_violations=0)
        self.assertEqual(payload["capture_status"], "partial")


class QualityTests(unittest.TestCase):
    def test_coverage(self):
        runners = [
            {"horse_number": 1, "popularity": 1, "win_odds": 2.0, "expected_popularity": 1, "trainer": "T"},
            {"horse_number": 2, "popularity": None, "win_odds": None, "expected_popularity": None, "trainer": None},
        ]
        q = compute_runner_feature_metrics(runners, prediction_created_at="2026-07-26T10:00:00+09:00")
        # 4 filled of (2 runners × len(PHASE1_FEATURES))
        from app.research.config import PHASE1_FEATURES

        expected = 4 / (2 * len(PHASE1_FEATURES))
        self.assertAlmostEqual(q["coverage"], expected, places=4)


class PathTests(unittest.TestCase):
    def test_repo_root_has_services(self):
        root = repo_root()
        self.assertTrue((root / "services").is_dir())

    def test_evidence_root_under_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["RESEARCH_EVIDENCE_ROOT"] = tmp
            self.assertEqual(evidence_root(), Path(tmp))
            os.environ.pop("RESEARCH_EVIDENCE_ROOT", None)


if __name__ == "__main__":
    unittest.main()
