# -*- coding: utf-8 -*-
"""I3 — Detail wiring verification (list LOCK, flag matrix)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


class I3DetailWiringAuditTest(unittest.TestCase):
    def test_list_lock_no_single(self):
        races = (REPO / "public" / "races.html").read_text(encoding="utf-8")
        self.assertNotIn("single-detail.js", races)
        self.assertNotIn("single.js", races)
        self.assertNotIn("ExpectApi.Single", races)
        self.assertIn("expect_race_list_cache_v4", races)
        self.assertIn("RACE_LIST_CACHE_TTL_MS = 5 * 60 * 1000", races)

    def test_detail_wires_single_detail(self):
        race = (REPO / "public" / "race.html").read_text(encoding="utf-8")
        self.assertIn("single-detail.js", race)
        self.assertIn("ExpectApi.SingleDetail.getWithMeta", race)
        # Must not remove Prediction client (fallback)
        self.assertIn("prediction.js", race)
        self.assertIn("prediction-bind.js", race)

    def test_flag_default_off(self):
        ui = (REPO / "public" / "assets" / "api" / "ui-features.js").read_text(encoding="utf-8")
        self.assertRegex(ui, r"single_ai_detail:\s*false")
        beta = (REPO / "public" / "config" / "beta.json").read_text(encoding="utf-8")
        self.assertIn('"single_ai_detail": false', beta)

    def test_single_detail_module_flag_and_fallback(self):
        src = (REPO / "public" / "assets" / "api" / "single-detail.js").read_text(encoding="utf-8")
        self.assertIn('FLAG = "single_ai_detail"', src)
        self.assertIn("Prediction.getWithMeta", src)
        self.assertIn("/api/single/detail/", src)
        self.assertIn("prediction_fallback", src)

    def test_bff_detail_route_exists(self):
        p = REPO / "functions" / "api" / "single" / "detail" / "[raceId].js"
        self.assertTrue(p.exists())
        text = p.read_text(encoding="utf-8")
        self.assertIn("SingleDetailAdapter", text)
        self.assertIn("onRequestGet", text)
        self.assertIn("onRequestPost", text)

    def test_cache_keys_unchanged(self):
        races = (REPO / "public" / "races.html").read_text(encoding="utf-8")
        prefetch = (REPO / "public" / "assets" / "api" / "race-prefetch.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('RACE_LIST_CACHE_KEY = "expect_race_list_cache_v4"', races)
        self.assertIn('SS_PB = "expect_pb_prefetch_v1"', prefetch)


if __name__ == "__main__":
    unittest.main()
