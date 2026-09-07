# -*- coding: utf-8 -*-
"""Tests for stable win5_leg assignment."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.features import _attach_win5_leg_from_races, stable_win5_leg_from_race_id


class StableWin5LegTest(unittest.TestCase):
    def test_parse_examples(self):
        self.assertEqual(stable_win5_leg_from_race_id("2026-07-25-01-06"), 6)
        self.assertEqual(stable_win5_leg_from_race_id("2026-07-25-02-07"), 19)
        self.assertEqual(stable_win5_leg_from_race_id("2026-07-25-03-12"), 36)

    def test_invalid_returns_nan(self):
        self.assertTrue(pd.isna(stable_win5_leg_from_race_id("bad")))
        self.assertTrue(pd.isna(stable_win5_leg_from_race_id("2026-07-25")))

    def test_attach_ignores_row_order(self):
        rows = [
            {"race_id": "2026-07-25-02-07", "date": "2026-07-25"},
            {"race_id": "2026-07-25-01-01", "date": "2026-07-25"},
            {"race_id": "2026-07-25-01-06", "date": "2026-07-25"},
        ]
        a = _attach_win5_leg_from_races(pd.DataFrame(rows))
        b = _attach_win5_leg_from_races(pd.DataFrame(list(reversed(rows))))
        map_a = dict(zip(a["race_id"], a["win5_leg"]))
        map_b = dict(zip(b["race_id"], b["win5_leg"]))
        self.assertEqual(map_a, map_b)
        self.assertEqual(int(map_a["2026-07-25-01-01"]), 1)
        self.assertEqual(int(map_a["2026-07-25-01-06"]), 6)
        self.assertEqual(int(map_a["2026-07-25-02-07"]), 19)

    def test_adding_early_race_does_not_shift_later(self):
        specials = pd.DataFrame(
            [
                {"race_id": "2026-07-25-01-06", "date": "2026-07-25"},
                {"race_id": "2026-07-25-02-07", "date": "2026-07-25"},
            ]
        )
        with_maiden = pd.concat(
            [
                pd.DataFrame([{"race_id": "2026-07-25-01-01", "date": "2026-07-25"}]),
                specials,
            ],
            ignore_index=True,
        )
        before = _attach_win5_leg_from_races(specials)
        after = _attach_win5_leg_from_races(with_maiden)
        before_map = dict(zip(before["race_id"], before["win5_leg"]))
        after_map = dict(zip(after["race_id"], after["win5_leg"]))
        self.assertEqual(before_map["2026-07-25-01-06"], after_map["2026-07-25-01-06"])
        self.assertEqual(before_map["2026-07-25-02-07"], after_map["2026-07-25-02-07"])


if __name__ == "__main__":
    unittest.main()
