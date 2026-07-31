# -*- coding: utf-8 -*-
"""V10.6 Resolver Governance unit tests."""
from __future__ import annotations

import unittest

from app.research.resolver_governance import ResolverGovernance


class StubGovernance(ResolverGovernance):
    def _load_v104(self) -> dict[str, object]:
        return {
            "evidence_priority": ["trainer", "owner", "popularity"],
            "tiers": {"S": ["trainer", "owner"], "A": ["popularity"], "B": [], "C": []},
            "features": [
                {"feature_id": "trainer", "tier": "S", "coverage": 1.0, "missing_rate": 0.0},
                {"feature_id": "owner", "tier": "S", "coverage": 1.0, "missing_rate": 0.0},
                {"feature_id": "popularity", "tier": "A", "coverage": 1.0, "missing_rate": 0.0},
            ],
        }

    def _load_v105(self) -> dict[str, object]:
        return {
            "summary": {"n_tie_races": 3},
            "resolver_records": [
                {
                    "race_id": "r1",
                    "race_date": "2026-07-25",
                    "prediction_id": 1,
                    "tie_size": 2,
                    "winner": 2,
                    "prediction_pick": 1,
                    "shadow_pick": 2,
                    "outcome": "win",
                    "status": "resolved",
                    "used_feature": "trainer",
                    "used_tier": "S",
                    "cascade_stop": "trainer",
                },
                {
                    "race_id": "r2",
                    "race_date": "2026-07-26",
                    "prediction_id": 2,
                    "tie_size": 2,
                    "winner": 1,
                    "prediction_pick": 1,
                    "shadow_pick": 1,
                    "outcome": "draw",
                    "status": "resolved",
                    "used_feature": "owner",
                    "used_tier": "S",
                    "cascade_stop": "owner",
                },
                {
                    "race_id": "r3",
                    "race_date": "2026-07-27",
                    "prediction_id": 3,
                    "tie_size": 2,
                    "winner": 2,
                    "prediction_pick": 1,
                    "shadow_pick": 1,
                    "outcome": "draw",
                    "status": "fallback_baseline",
                    "used_feature": None,
                    "used_tier": None,
                    "cascade_stop": "fallback",
                },
            ],
        }

    def __init__(self) -> None:
        super().__init__()
        races = [
            {
                "snapshot_id": "s1",
                "prediction_id": 1,
                "race_id": "r1",
                "race_date": "2026-07-25",
                "winner": 2,
                "runners": [
                    {"horse_number": 1, "model_rank": 1, "win_prob": 0.55},
                    {"horse_number": 2, "model_rank": 1, "win_prob": 0.45},
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
                "race_id": "r2",
                "race_date": "2026-07-26",
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
            {
                "snapshot_id": "s3",
                "prediction_id": 3,
                "race_id": "r3",
                "race_date": "2026-07-27",
                "winner": 2,
                "runners": [
                    {"horse_number": 1, "model_rank": 1, "win_prob": 0.60},
                    {"horse_number": 2, "model_rank": 1, "win_prob": 0.40},
                ],
                "tie_group": [
                    {"horse_number": 1, "model_rank": 1, "win_prob": 0.60},
                    {"horse_number": 2, "model_rank": 1, "win_prob": 0.40},
                ],
                "tie_size": 2,
            },
        ]
        fmap = {
            "s1": {"trainer": {1: "A", 2: "B"}, "owner": {1: "X", 2: "Y"}, "popularity": {1: 1, 2: 2}},
            "s2": {"trainer": {1: "A", 2: "A"}, "owner": {1: "Y", 2: "X"}, "popularity": {1: 1, 2: 2}},
            "s3": {"trainer": {1: None, 2: None}, "owner": {1: None, 2: None}, "popularity": {1: 1, 2: 1}},
        }
        self.ranking.build_corpus = lambda: (races, fmap)
        self.ranking.prior_for_race = lambda **kwargs: {"A": 0.1, "B": 0.8, "X": 0.1, "Y": 0.9}

    def _race_meta(self, race_ids: list[str]) -> dict[str, dict[str, object]]:
        return {
            "r1": {"race_date": "2026-07-25", "venue": "新潟", "surface": "芝", "distance": 1600, "class_label": "2歳新馬"},
            "r2": {"race_date": "2026-07-26", "venue": "札幌", "surface": "ダート", "distance": 1700, "class_label": "3歳未勝利"},
            "r3": {"race_date": "2026-07-27", "venue": "中京", "surface": "芝", "distance": 1200, "class_label": "2勝クラス"},
        }


class ResolverGovernanceTests(unittest.TestCase):
    def test_governance_outputs_status_and_segments(self):
        report = StubGovernance().analyze()
        self.assertEqual(report["cumulative"]["tie_races"], 3)
        self.assertEqual(report["cumulative"]["resolver_win"], 1)
        self.assertEqual(report["dashboard"]["current_status"], "sample_insufficient")
        self.assertTrue(any(x["segment"] == "age_group:2yo_newcomer" for x in report["segments"]))
        self.assertGreaterEqual(len(report["periods"]["weekly"]), 1)
        self.assertGreaterEqual(report["cumulative"]["confidence_distribution"]["p50"], 0.0)


if __name__ == "__main__":
    unittest.main()
