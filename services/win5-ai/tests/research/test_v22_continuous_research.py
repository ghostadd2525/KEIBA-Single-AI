# -*- coding: utf-8 -*-
"""V22 Continuous Research Operation unit tests."""
from __future__ import annotations

import unittest

from app.research.continuous_research_operation import (
    MATURITY_GATE,
    assess_data_quality,
    build_review_queue,
    candidate_transitions,
    collect_notifications,
    evaluate_maturity,
    weakness_rank_changes,
)


class MaturityGateTests(unittest.TestCase):
    def _entry(self, **over):
        base = {
            "knowledge_id": "kb-test",
            "source_key": "feat:Popularity",
            "confidence": "High",
            "observation": "test",
            "graph": {"features": ["Popularity"]},
            "evidence": {
                "n": 120,
                "coverage": 0.95,
                "reliability": 85.0,
                "wilson_ci": {"low": 0.20, "high": 0.40},
            },
        }
        base.update(over)
        if "evidence" in over:
            ev = dict(base["evidence"])
            ev.update(over["evidence"])
            base["evidence"] = ev
        return base

    def test_mature_pass(self):
        r = evaluate_maturity(
            self._entry(), leak_risk=0.3, governance_pass=True
        )
        self.assertTrue(r["mature"])

    def test_n_gate(self):
        r = evaluate_maturity(
            self._entry(evidence={"n": 50}),
            leak_risk=0.3,
            governance_pass=True,
        )
        self.assertFalse(r["checks"]["evidence_n"])
        self.assertFalse(r["mature"])

    def test_gate_constants(self):
        self.assertEqual(MATURITY_GATE["min_n"], 100)
        self.assertEqual(MATURITY_GATE["min_coverage"], 0.90)
        self.assertEqual(MATURITY_GATE["min_reliability"], 80.0)


class DiffHelperTests(unittest.TestCase):
    def test_weakness_rank(self):
        prev = [{"axis": "going", "segment": "良", "priority_rank": 1}]
        curr = [{"axis": "going", "segment": "良", "priority_rank": 3}]
        ch = weakness_rank_changes(prev, curr)
        self.assertEqual(len(ch), 1)
        self.assertEqual(ch[0]["delta"], -2)

    def test_candidate_transitions(self):
        d = candidate_transitions(
            {"a": "Validated", "b": "Production_Candidate"},
            {"a": "Production_Candidate", "b": "Validated"},
        )
        self.assertEqual(len(d["promote"]), 1)
        self.assertEqual(len(d["demote"]), 1)

    def test_notifications_filter(self):
        notes = collect_notifications(
            weekly_diff={
                "added": [
                    {"confidence": "High", "source_key": "x"},
                    {"confidence": "Low", "source_key": "y"},
                ],
                "changed": [],
            },
            weakness_changes=[{"key": "a|b", "delta": 2, "rank_before": 5, "rank_after": 3}],
            candidate_delta={
                "promote": [{"knowledge_id": "k1", "before": "Validated", "after": "Production_Candidate"}],
                "demote": [],
            },
            data_quality={"quality_drop": True, "drop_detail": ["coverage_wow_drop"]},
        )
        types = {n["type"] for n in notes}
        self.assertIn("new_high_knowledge", types)
        self.assertIn("weakness_rank_change", types)
        self.assertIn("candidate_promote", types)
        self.assertIn("data_quality_drop", types)
        self.assertEqual(sum(1 for n in notes if n["type"] == "new_high_knowledge"), 1)

    def test_review_queue_requires_governance(self):
        entry = {
            "knowledge_id": "kb-1",
            "confidence": "High",
            "graph": {"features": ["Popularity"]},
            "evidence": {
                "n": 120,
                "coverage": 0.95,
                "reliability": 85.0,
                "wilson_ci": {"low": 0.2, "high": 0.4},
            },
        }
        q = build_review_queue(
            [entry],
            leak_by_feature={"Popularity": 0.2},
            validation_by_id={},
            review_by_id={},
            resolver_status="sample_insufficient",
        )
        self.assertEqual(q, [])

        q2 = build_review_queue(
            [entry],
            leak_by_feature={"Popularity": 0.2},
            validation_by_id={
                "kb-1": {"passed": True, "state_after": "Validated"}
            },
            review_by_id={},
            resolver_status="sample_insufficient",
        )
        self.assertEqual(len(q2), 1)
        self.assertFalse(q2[0]["ai_implementation"])

    def test_data_quality_drop(self):
        dq = assess_data_quality(
            meta_summary={"mean_coverage_before": 0.7, "mean_coverage_after": 0.72},
            prev_ops={"coverage": {"mean_after": 0.80}, "reliability": {"mean_score": 70}},
            reliability_rows=[{"reliability_score": 60}],
        )
        self.assertTrue(dq["quality_drop"])
        self.assertIn("coverage_wow_drop", dq["drop_detail"])


if __name__ == "__main__":
    unittest.main()
