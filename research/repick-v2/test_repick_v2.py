# -*- coding: utf-8 -*-
"""Unit tests for RePick v2 (ISSUE-REPICK-V2-001)."""
from __future__ import annotations

import inspect
import unittest

import v2_repick_v2 as rv2


def _h(name: str, rank: int, surv: float, wp: float = 0.1) -> dict:
    return {
        "horse_name": name,
        "model_rank": rank,
        "_world_survival_score": surv,
        "win_prob": wp,
    }


class TestRepickV2(unittest.TestCase):
    def setUp(self) -> None:
        rv2.apply_win5_repick_v2_flags(False, slot=False, rank6=False)

    def tearDown(self) -> None:
        rv2.apply_win5_repick_v2_flags(False, slot=False, rank6=False)

    def test_flag_off_identity(self) -> None:
        n = 5
        rescored = [_h(f"H{i}", i, 10 - i) for i in range(1, 9)]
        selected = list(rescored[:n])
        meta = {"race_id": "test-race", "winner": "MUST_NOT_USE"}
        out = rv2.apply_win5_repick_v2(selected, rescored, n, meta)
        self.assertEqual([h["horse_name"] for h in out], [h["horse_name"] for h in selected])
        self.assertEqual(meta["_win5_repick_v2_journal"]["reason"], "disabled")
        self.assertFalse(meta["_win5_repick_v2_journal"]["fired"])

    def test_near_displacement_n_invariant(self) -> None:
        rv2.apply_win5_repick_v2_flags(True)
        n = 5
        # surv order: A..E selected; F rank8 at pos 6 (NEAR); G deep; H far
        rescored = [
            _h("A", 1, 9.0),
            _h("B", 2, 8.0),
            _h("C", 3, 7.0),
            _h("D", 4, 6.0),
            _h("E", 12, 5.0),  # deep in selected → preferred victim
            _h("F", 8, 4.0),  # NEAR N+1, rank710
            _h("G", 11, 3.0),
            _h("H", 9, 1.0),  # FAR (pos 8 > N+2)
        ]
        selected = list(rescored[:n])
        meta = {"race_id": "t-near", "winner": "H"}  # winner present but must not drive pick
        out = rv2.apply_win5_repick_v2(selected, rescored, n, meta)
        names = [h["horse_name"] for h in out]
        self.assertEqual(len(out), n)
        self.assertIn("F", names)
        self.assertNotIn("E", names)
        j = meta["_win5_repick_v2_journal"]
        self.assertTrue(j["fired"])
        self.assertEqual(j["facet"], "RV2-A")
        self.assertEqual(j["cand_name"], "F")
        self.assertEqual(j["victim_name"], "E")
        self.assertEqual(j["anonymous"], 1)
        self.assertEqual(j["repick_size_before"], j["repick_size_after"])

    def test_does_not_prefer_winner_over_near_anonymous(self) -> None:
        rv2.apply_win5_repick_v2_flags(True)
        n = 5
        rescored = [
            _h("A", 1, 9.0),
            _h("B", 2, 8.0),
            _h("C", 3, 7.0),
            _h("D", 4, 6.0),
            _h("E", 12, 5.0),
            _h("NEAR", 8, 4.5),  # pos 6 NEAR
            _h("WIN", 9, 4.0),  # pos 7 NEAR but farther — winner in meta
        ]
        selected = list(rescored[:n])
        meta = {"race_id": "t-anon", "winner": "WIN", "winner_name": "WIN"}
        out = rv2.apply_win5_repick_v2(selected, rescored, n, meta)
        names = [h["horse_name"] for h in out]
        self.assertIn("NEAR", names)
        self.assertNotIn("WIN", names)
        self.assertEqual(meta["_win5_repick_v2_journal"]["cand_name"], "NEAR")

    def test_no_victim_keeps_size(self) -> None:
        rv2.apply_win5_repick_v2_flags(True)
        n = 3
        rescored = [
            _h("A", 1, 9.0),
            _h("B", 2, 8.0),
            _h("C", 3, 7.0),
            _h("F", 8, 4.0),
        ]
        selected = list(rescored[:n])
        for h in selected:
            h["_phase249_rp1_rank6_protect_flag"] = 1
            h["_v2_tw_flag"] = 1
        meta = {"race_id": "t-novictim"}
        out = rv2.apply_win5_repick_v2(selected, rescored, n, meta)
        self.assertEqual([h["horse_name"] for h in out], [h["horse_name"] for h in selected])
        self.assertEqual(meta["_win5_repick_v2_journal"]["reason"], "no_victim")

    def test_source_has_no_winner_decision_paths(self) -> None:
        src = inspect.getsource(rv2.apply_win5_repick_v2)
        src_sel = inspect.getsource(rv2._select_anonymous_near_candidate)
        banned = [
            'meta.get("winner"',
            "meta.get('winner'",
            'meta.get("winner_name"',
            "TR7N_PHASE283",
            "G1_RACES",
        ]
        for b in banned:
            self.assertNotIn(b, src)
            self.assertNotIn(b, src_sel)


if __name__ == "__main__":
    unittest.main()
