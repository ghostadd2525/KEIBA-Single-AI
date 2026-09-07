# -*- coding: utf-8 -*-
"""V11.1 Historical Bundle Ingest unit tests."""
from __future__ import annotations

import unittest

from app.research.historical_bundle_ingest import (
    _as_canonical_bundle,
    _has_model_rank_runners,
    _normalize_horse_numbers,
)


class HistoricalIngestHelpers(unittest.TestCase):
    def test_normalize_horse_numbers_and_winner(self):
        runners = [
            {"horse_id": "a", "model_rank": 1, "win_prob": 0.2, "horse_number": 0},
            {"horse_id": "b", "model_rank": 1, "win_prob": 0.2, "horse_number": 0},
            {"horse_id": "c", "model_rank": 3, "win_prob": 0.1, "horse_number": 5},
        ]
        out, winner = _normalize_horse_numbers(runners, winner_horse_id="b")
        self.assertEqual(winner, 2)
        self.assertEqual({r["horse_number"] for r in out}, {1, 2, 5})

    def test_canonical_bundle_has_model_rank(self):
        bundle = _as_canonical_bundle(
            race_id="2024-01-06-京都-10",
            runners=[
                {"horse_number": 1, "model_rank": 1, "win_prob": 0.2},
                {"horse_number": 2, "model_rank": 2, "win_prob": 0.1},
            ],
        )
        ok, runners = _has_model_rank_runners(bundle)
        self.assertTrue(ok)
        self.assertEqual(len(runners), 2)


if __name__ == "__main__":
    unittest.main()
