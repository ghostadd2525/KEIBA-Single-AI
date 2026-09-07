# -*- coding: utf-8 -*-
"""Unit tests for Decision Layer M1 (ADR-008). Prediction never mutated."""
from __future__ import annotations

import os
import unittest

from app.decision.fingerprint import prediction_fingerprint, rank_fingerprint, score_fingerprint
from app.decision.flags import snapshot_flags
from app.decision.service import apply_decision, build_prediction_view, dual_shadow


def _horses():
    return [
        {"horse_id": "A", "model_rank": 1, "win_prob": 0.4, "history_score": 1.0, "odds": 2.5},
        {"horse_id": "B", "model_rank": 2, "win_prob": 0.3, "history_score": 2.0, "odds": 5.0},
        {"horse_id": "C", "model_rank": 3, "win_prob": 0.2, "history_score": 0.5, "odds": 8.0},
    ]


class DecisionLayerM1Test(unittest.TestCase):
    def test_flags_default_off(self):
        for k, v in snapshot_flags().items():
            self.assertFalse(v, k)

    def test_flag_off_equals_legacy(self):
        view = build_prediction_view(
            race_id="r1",
            world_id="rank7_world",
            predicted_top1="A",
            winner_id="A",
            horses=_horses(),
        )
        # Ensure env off
        for k in list(os.environ.keys()):
            if k.startswith("W_DECISION_"):
                os.environ.pop(k, None)
        env = apply_decision(view)
        off = apply_decision(view, force_mode="OFF")
        self.assertEqual(env.action, off.action)
        self.assertEqual(env.tickets, off.tickets)
        self.assertEqual(env.explanation.template, "generic_baseline")

    def test_dual_shadow_preserves_fingerprints(self):
        horses = _horses()
        view = build_prediction_view(
            race_id="r1",
            world_id="rank7_world",
            predicted_top1="A",
            winner_id="B",
            horses=horses,
        )
        dual = dual_shadow(view)
        self.assertEqual(dual["decision_off"].prediction_fingerprint, view.prediction_fingerprint)
        self.assertEqual(dual["decision_on"].prediction_fingerprint, view.prediction_fingerprint)
        self.assertEqual(rank_fingerprint(horses), view.rank_fingerprint)
        self.assertEqual(score_fingerprint(horses), view.score_fingerprint)
        # ON diversifies tickets but does not change horse scores
        self.assertEqual([h["win_prob"] for h in horses], [0.4, 0.3, 0.2])
        self.assertEqual(len(dual["decision_on"].pool), 3)  # only 3 horses → pool size 3

    def test_blocked_skip(self):
        view = build_prediction_view(
            race_id="r2",
            world_id="core_world",
            predicted_top1="A",
            winner_id="A",
            horses=_horses(),
        )
        on = apply_decision(view, force_mode="ON")
        self.assertEqual(on.action, "SKIP")
        self.assertEqual(on.tickets, ())


if __name__ == "__main__":
    unittest.main()
