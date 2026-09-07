# -*- coding: utf-8 -*-
"""V10.7 Backfill Replay unit tests (synthetic)."""

from __future__ import annotations

import datetime as _dt
import unittest

from app.research.resolver_governance_backfill import (
    BackfillTieRace,
    ResolverGovernanceBackfill,
)


class StubBackfill(ResolverGovernanceBackfill):
    def __init__(self) -> None:
        super().__init__(perm_shuffles=1, max_tie_races=5)

    def _load_tie_races(self):
        # Two tie races with deterministic features.
        base_dt = _dt.datetime(2026, 7, 1, tzinfo=_dt.timezone.utc)

        def make_tr(i: int, winner: int, trainer_w: str, popularity_1: float, popularity_2: float):
            runners = [
                {"horse_number": 1, "model_rank": 1, "win_prob": 0.6},
                {"horse_number": 2, "model_rank": 1, "win_prob": 0.4},
            ]
            g = [
                {"horse_number": 1, "model_rank": 1, "win_prob": 0.6},
                {"horse_number": 2, "model_rank": 1, "win_prob": 0.4},
            ]
            pred_pick = winner  # baseline picks winner for simplicity
            return BackfillTieRace(
                prediction_id=10 + i,
                prediction_created_at=base_dt + _dt.timedelta(days=i),
                race_id=f"r{i}",
                snapshot_id=f"s{i}",
                race_meta={
                    "race_date": None,
                    "venue": "東京",
                    "surface": "芝",
                    "distance": 1600,
                    "class_label": "2歳新馬",
                },
                winner=winner,
                runners=runners,
                tie_group=g,
                tie_size=2,
                strict=(pred_pick == winner),
                soft=True,
                soft_not_strict=False,
                prediction_pick=pred_pick,
            )

        return [
            make_tr(0, winner=1, trainer_w="A", popularity_1=1.0, popularity_2=5.0),
            make_tr(1, winner=2, trainer_w="B", popularity_1=1.0, popularity_2=2.0),
        ]

    def _load_time_filtered_fmap(self, tie_races):
        # snapshot_id -> feature -> horse -> value
        # Popularity lower-better: horse 1 has smaller popularity => preferred.
        return {
            "s0": {
                "popularity": {1: 1.0, 2: 5.0},
                "win_odds": {1: 1.0, 2: 5.0},
                "expected_popularity": {1: 1.0, 2: 5.0},
                "trainer": {1: "A", 2: "B"},
                "sire": {1: "S1", 2: "S2"},
                "damsire": {1: "D1", 2: "D2"},
                "breeder": {1: "Br1", 2: "Br2"},
                "owner": {1: "O1", 2: "O2"},
                "sale_price": {1: 1000.0, 2: 500.0},
                "oikiri_time": {1: 10.0, 2: 11.0},
                "oikiri_rating": {1: "A", 2: "B"},
            },
            "s1": {
                "popularity": {1: 1.0, 2: 2.0},
                "win_odds": {1: 1.0, 2: 2.0},
                "expected_popularity": {1: 1.0, 2: 2.0},
                "trainer": {1: "A", 2: "B"},
                "sire": {1: "S1", 2: "S2"},
                "damsire": {1: "D1", 2: "D2"},
                "breeder": {1: "Br1", 2: "Br2"},
                "owner": {1: "O1", 2: "O2"},
                "sale_price": {1: 1000.0, 2: 1500.0},
                "oikiri_time": {1: 10.0, 2: 9.0},
                "oikiri_rating": {1: "A", 2: "C"},
            },
        }

    def _load_snapshot_feature_totals(self, tie_races):
        # For simplicity: all features complete for both horses, filled depends on presence (all present).
        out = {}
        for tr in tie_races:
            out[tr.snapshot_id] = {}
            for fid in self.features:
                out[tr.snapshot_id][fid] = (2, 2)  # filled=2 horses, total=2 horses
        return out


class BackfillTests(unittest.TestCase):
    def test_backfill_produces_monthly_yearly_segments(self):
        report = StubBackfill().run()
        self.assertEqual(report["tie_races_evaluated"], 2)
        self.assertTrue(report["monthly"])
        self.assertTrue(report["yearly"])
        self.assertTrue(report["segments"])


if __name__ == "__main__":
    unittest.main()

