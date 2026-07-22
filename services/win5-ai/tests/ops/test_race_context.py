# -*- coding: utf-8 -*-
import unittest

from app.ops.race_context import extract_race_context


class RaceContextTest(unittest.TestCase):
    def test_extract_from_bundle_track_condition(self):
        bundle = {
            "race_info": {
                "venue": "東京",
                "surface": "turf",
                "distance": 1600,
            },
            "explain": {
                "meta": {"track_condition": "稍重"},
            },
        }
        ctx = extract_race_context(bundle=bundle)
        self.assertEqual(ctx["surface"], "turf")
        self.assertEqual(ctx["distance"], 1600)
        self.assertEqual(ctx["going"], "稍重")

    def test_result_overrides_bundle_when_present(self):
        ctx = extract_race_context(
            result={"going": "重", "surface": "芝", "distance": 2000},
            bundle={
                "race_info": {"surface": "turf", "distance": 1600},
                "explain": {"meta": {"track_condition": "良"}},
            },
        )
        self.assertEqual(ctx["going"], "重")
        self.assertEqual(ctx["surface"], "芝")
        self.assertEqual(ctx["distance"], 2000)

    def test_csv_extra_aliases(self):
        ctx = extract_race_context(
            extra={"target_surface": "ダート", "target_distance": "1400", "baba": "不良"},
        )
        self.assertEqual(ctx["surface"], "ダート")
        self.assertEqual(ctx["distance"], 1400)
        self.assertEqual(ctx["going"], "不良")


if __name__ == "__main__":
    unittest.main()
