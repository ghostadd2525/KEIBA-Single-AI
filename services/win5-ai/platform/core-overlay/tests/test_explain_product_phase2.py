# -*- coding: utf-8 -*-
"""Phase 2 — Product journal → product_stages / decision_trace."""
from __future__ import annotations

import os
import unittest

from ai_platform.core.explain import (
    apply_win5_explain_v2_flags,
    build_explain_payload,
    build_product_stages,
    merge_product_into_trace,
)


class TestExplainProductPhase2(unittest.TestCase):
    def tearDown(self) -> None:
        apply_win5_explain_v2_flags(False)
        os.environ.pop("WIN5_EXPLAIN_V2_ENABLED", None)

    def test_flag_off_still_none_with_journals(self) -> None:
        apply_win5_explain_v2_flags(False)
        payload = build_explain_payload(
            candidates=[{"CandidateID": "A", "Rank": 1, "Confidence": 0.1, "HorseNumber": 1}],
            world={"world": "midupper_world", "sub_world": "midupper_route"},
            confidence={"overall": 0.05, "band": "low", "meta": {"gap12": 0.01}},
            product_journals={
                "pool_entry": {"enabled": True, "fired": True, "inserted": True, "reason": "insert"},
            },
        )
        self.assertIsNone(payload)

    def test_product_stages_from_journals(self) -> None:
        stages = build_product_stages(
            pool_entry={
                "enabled": True,
                "facet": "PE-V2-A",
                "fired": True,
                "inserted": True,
                "reason": "insert",
                "cand_name": "サンプルホース",
                "cand_rank": 11,
                "pool_size_before": 8,
                "pool_size_after": 9,
            },
            repick={
                "enabled": True,
                "facet": "RP-V2-A",
                "fired": True,
                "displaced": True,
                "reason": "displaced",
                "cand_name": "NEAR馬",
                "cand_rank": 9,
                "cand_surv_pos": 10,
                "victim_name": "被害馬",
                "victim_rank": 11,
                "repick_n": 8,
                "repick_size_before": 8,
                "repick_size_after": 8,
            },
            timestamp="2026-07-21T04:00:01.123Z",
        )
        self.assertEqual(len(stages), 3)
        by = {s["stage"]: s for s in stages}
        self.assertEqual(by["candidate_pool"]["status"], "applied")
        self.assertEqual(by["entry"]["status"], "applied")
        self.assertEqual(by["repick"]["status"], "applied")
        self.assertEqual(by["repick"]["timestamp"], "2026-07-21T04:00:01.123Z")
        self.assertIn("NEAR rescue", by["repick"]["delta"]["summary"])

    def test_build_payload_merges_meta_journals(self) -> None:
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
                    "entropy": 2.8,
                    "top1_prob": 0.0657,
                    "field_size": 18,
                    "uncertainty": 0.8,
                },
            },
            meta={
                "_win5_pool_entry_v2_journal": {
                    "enabled": True,
                    "facet": "PE-V2-A",
                    "fired": True,
                    "inserted": True,
                    "reason": "insert",
                    "cand_name": "深穴",
                    "cand_rank": 12,
                    "pool_size_before": 7,
                    "pool_size_after": 8,
                },
                "_win5_repick_v2_journal": {
                    "enabled": True,
                    "facet": "RP-V2-A",
                    "fired": False,
                    "displaced": False,
                    "reason": "no_near_candidate",
                },
            },
        )
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertIsNotNone(payload["product_stages"])
        self.assertEqual(payload["pipeline_version"], "ai-core-migrated/1.0-phase2")
        by = {s["stage"]: s for s in payload["decision_trace_stages"]}
        self.assertEqual(by["candidate_pool"]["status"], "applied")
        self.assertEqual(by["entry"]["status"], "applied")
        self.assertEqual(by["repick"]["status"], "skipped")
        # Phase 1 stages remain
        self.assertEqual(by["delete"]["status"], "locked")

    def test_merge_idempotent(self) -> None:
        base = [
            {"stage": "candidate_pool", "status": "not_applied", "delta": {"summary": "stub"}},
            {"stage": "delete", "status": "locked", "delta": {"summary": "locked"}},
        ]
        product = [
            {
                "stage": "candidate_pool",
                "status": "applied",
                "timestamp": "2026-07-21T04:00:01.123Z",
                "delta": {"summary": "Pool insert"},
            }
        ]
        merged = merge_product_into_trace(base, product)
        self.assertEqual(merged[0]["status"], "applied")
        self.assertEqual(merged[0]["delta"]["summary"], "Pool insert")
        self.assertEqual(merged[1]["stage"], "delete")


if __name__ == "__main__":
    unittest.main()
