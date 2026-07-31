# -*- coding: utf-8 -*-
"""V10.5 Shadow Tie Resolver unit tests."""
from __future__ import annotations

import unittest

from app.research.shadow_resolver import ShadowTieResolver


class StubResolver(ShadowTieResolver):
    def load_v104_priority(self) -> dict:
        return {
            "evidence_priority": ["trainer", "popularity"],
            "features": [
                {"feature_id": "trainer", "tier": "S"},
                {"feature_id": "popularity", "tier": "A"},
            ],
            "tiers": {"S": ["trainer"], "A": ["popularity"], "B": [], "C": []},
        }

    def __init__(self) -> None:
        super().__init__()

        races = [
            {
                "snapshot_id": "s1",
                "prediction_id": 1,
                "race_id": "202601010101",
                "race_date": "2026-01-01",
                "winner": 2,
                "runners": [
                    {"horse_number": 1, "model_rank": 1, "win_prob": 0.55},
                    {"horse_number": 2, "model_rank": 1, "win_prob": 0.45},
                    {"horse_number": 3, "model_rank": 2, "win_prob": 0.20},
                ],
                "tie_group": [
                    {"horse_number": 1, "model_rank": 1, "win_prob": 0.55},
                    {"horse_number": 2, "model_rank": 1, "win_prob": 0.45},
                ],
                "tie_size": 2,
            },
            {
                "snapshot_id": "s2",
                "prediction_id": 2,
                "race_id": "202601020101",
                "race_date": "2026-01-02",
                "winner": 1,
                "runners": [
                    {"horse_number": 1, "model_rank": 1, "win_prob": 0.51},
                    {"horse_number": 2, "model_rank": 1, "win_prob": 0.49},
                ],
                "tie_group": [
                    {"horse_number": 1, "model_rank": 1, "win_prob": 0.51},
                    {"horse_number": 2, "model_rank": 1, "win_prob": 0.49},
                ],
                "tie_size": 2,
            },
        ]
        fmap = {
            "s1": {"trainer": {1: "A", 2: "B"}, "popularity": {1: 1, 2: 2}},
            "s2": {"trainer": {1: "A", 2: "A"}, "popularity": {1: 1, 2: 2}},
        }
        self.ranking.build_corpus = lambda: (races, fmap)
        self.ranking.prior_for_race = lambda **kwargs: {"A": 0.1, "B": 0.8}


class ShadowResolverTests(unittest.TestCase):
    def test_shadow_resolver_tracks_win_draw_and_usage(self):
        report = StubResolver().analyze()

        self.assertEqual(report["corpus"]["n_tie_races"], 2)
        self.assertEqual(report["summary"]["baseline_strict_hits"], 1)
        self.assertEqual(report["summary"]["shadow_strict_hits"], 2)
        self.assertEqual(report["summary"]["resolver_win"], 1)
        self.assertEqual(report["summary"]["resolver_lose"], 0)
        self.assertEqual(report["summary"]["resolver_draw"], 1)
        self.assertEqual(report["tier_usage"]["S"], 1)
        self.assertEqual(report["cascade_stop_usage"]["trainer"], 1)
        self.assertEqual(report["cascade_stop_usage"]["popularity"], 1)


if __name__ == "__main__":
    unittest.main()
