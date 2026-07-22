# -*- coding: utf-8 -*-
"""Unit tests — Core explain_payload Flag OFF identity + ON shape."""
from __future__ import annotations

import os
import unittest

from ai_platform.core.explain import (
    apply_win5_explain_v2_flags,
    build_explain_payload,
    is_explain_v2_enabled,
)


class TestExplainPayload(unittest.TestCase):
    def tearDown(self) -> None:
        apply_win5_explain_v2_flags(False)
        os.environ.pop("WIN5_EXPLAIN_V2_ENABLED", None)

    def test_flag_off_returns_none(self) -> None:
        apply_win5_explain_v2_flags(False)
        self.assertFalse(is_explain_v2_enabled())
        payload = build_explain_payload(
            candidates=[{"CandidateID": "A", "Rank": 1, "Confidence": 0.1, "HorseNumber": 1}],
            world={"world": "midupper_world", "sub_world": "midupper_route"},
            confidence={
                "overall": 0.05,
                "band": "low",
                "meta": {"gap12": 0.01, "entropy": 2.5, "top1_prob": 0.1, "field_size": 16, "uncertainty": 0.5},
            },
        )
        self.assertIsNone(payload)

    def test_flag_on_has_required_fields(self) -> None:
        apply_win5_explain_v2_flags(True)
        payload = build_explain_payload(
            candidates=[
                {
                    "CandidateID": "コルドンブルー",
                    "Rank": 1,
                    "Confidence": 0.0657,
                    "HorseNumber": 4,
                }
            ],
            world={"world": "midupper_world", "sub_world": "midupper_route"},
            confidence={
                "overall": 0.042,
                "band": "low",
                "meta": {
                    "gap12": 0.004883,
                    "entropy": 2.887667,
                    "top1_prob": 0.0657,
                    "top2_sum": 0.126,
                    "field_size": 18,
                    "uncertainty": 0.8,
                },
            },
            meta={"race_required_pick": 2, "spread_need_label": "strong_spread"},
        )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["schema_version"], "core-explain-payload/1.0")
        self.assertIn("decision_key", payload)
        self.assertEqual(payload["decision_key"]["key"], "ce_rank1_gap_lead")
        comps = payload["confidence_components"]
        self.assertTrue(
            any(c.get("key") == "gap12" and "contribution" in c and "weight" in c for c in comps)
        )
        stages = payload["decision_trace_stages"]
        self.assertTrue(all("stage" in s and "status" in s and "delta" in s for s in stages))
        self.assertTrue(any(s["stage"] == "delete" and s["status"] == "locked" for s in stages))


if __name__ == "__main__":
    unittest.main()
