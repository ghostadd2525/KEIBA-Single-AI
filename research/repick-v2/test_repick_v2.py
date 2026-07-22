# -*- coding: utf-8 -*-
"""Unit tests for RePick v2 RP-V2-A (V2.1 narrowing)."""
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


class TestRepickV2A(unittest.TestCase):
    def setUp(self) -> None:
        rv2.apply_win5_repick_v2_flags(False, slot=False, rank6=False)
        rv2.reset_fire_caps()

    def tearDown(self) -> None:
        rv2.apply_win5_repick_v2_flags(False, slot=False, rank6=False)
        rv2.reset_fire_caps()

    def test_flag_off_identity(self) -> None:
        n = 5
        rescored = [_h(f"H{i}", i, 10 - i) for i in range(1, 9)]
        selected = list(rescored[:n])
        meta = {"race_id": "2026-01-01-test-01", "winner": "MUST_NOT_USE"}
        out = rv2.apply_win5_repick_v2(selected, rescored, n, meta)
        self.assertEqual([h["horse_name"] for h in out], [h["horse_name"] for h in selected])
        self.assertEqual(meta["_win5_repick_v2_journal"]["reason"], "disabled")
        self.assertFalse(meta["_win5_repick_v2_journal"]["fired"])

    def test_near_n_plus_1_displacement(self) -> None:
        rv2.apply_win5_repick_v2_flags(True)
        n = 5
        rescored = [
            _h("A", 1, 9.0),
            _h("B", 2, 8.0),
            _h("C", 3, 7.0),
            _h("D", 4, 6.0),
            _h("E", 12, 5.0),  # deep victim
            _h("F", 8, 4.0),  # N+1 NEAR
            _h("G", 11, 3.0),
            _h("H", 9, 1.0),  # N+3 — not eligible under TN-A
        ]
        selected = list(rescored[:n])
        meta = {"race_id": "2026-01-01-test-02", "winner": "H"}
        out = rv2.apply_win5_repick_v2(selected, rescored, n, meta)
        names = [h["horse_name"] for h in out]
        self.assertEqual(len(out), n)
        self.assertIn("F", names)
        self.assertNotIn("E", names)
        j = meta["_win5_repick_v2_journal"]
        self.assertTrue(j["fired"])
        self.assertEqual(j["facet"], "RP-V2-A")
        self.assertEqual(j["cand_name"], "F")
        self.assertEqual(j["victim_name"], "E")

    def test_n_plus_2_not_selected_under_tn_a(self) -> None:
        rv2.apply_win5_repick_v2_flags(True)
        n = 5
        rescored = [
            _h("A", 1, 9.0),
            _h("B", 2, 8.0),
            _h("C", 3, 7.0),
            _h("D", 4, 6.0),
            _h("E", 12, 5.0),
            _h("FAR", 15, 4.5),  # N+1 but rank outside 7-10
            _h("N2", 8, 4.0),  # N+2 only — TN-A must reject
        ]
        selected = list(rescored[:n])
        meta = {"race_id": "2026-01-01-test-03"}
        out = rv2.apply_win5_repick_v2(selected, rescored, n, meta)
        self.assertEqual([h["horse_name"] for h in out], [h["horse_name"] for h in selected])
        self.assertEqual(meta["_win5_repick_v2_journal"]["reason"], "no_near_candidate")

    def test_tn_c_requires_deep_victim(self) -> None:
        rv2.apply_win5_repick_v2_flags(True)
        n = 5
        rescored = [
            _h("A", 1, 9.0),
            _h("B", 2, 8.0),
            _h("C", 3, 7.0),
            _h("D", 4, 6.0),
            _h("E", 5, 5.0),  # no rank>=11 in selected
            _h("F", 8, 4.0),
        ]
        selected = list(rescored[:n])
        meta = {"race_id": "2026-01-01-test-04"}
        out = rv2.apply_win5_repick_v2(selected, rescored, n, meta)
        self.assertEqual([h["horse_name"] for h in out], [h["horse_name"] for h in selected])
        self.assertEqual(meta["_win5_repick_v2_journal"]["reason"], "no_deep_victim")

    def test_mid_cap(self) -> None:
        rv2.apply_win5_repick_v2_flags(True)
        n = 5
        rescored = [
            _h("A", 1, 9.0),
            _h("B", 7, 8.0),  # mid
            _h("C", 8, 7.0),  # mid → already 2
            _h("D", 4, 6.0),
            _h("E", 12, 5.0),
            _h("F", 9, 4.0),
        ]
        selected = list(rescored[:n])
        meta = {"race_id": "2026-01-01-test-05"}
        out = rv2.apply_win5_repick_v2(selected, rescored, n, meta)
        self.assertEqual([h["horse_name"] for h in out], [h["horse_name"] for h in selected])
        self.assertEqual(meta["_win5_repick_v2_journal"]["reason"], "mid_cap")

    def test_source_has_no_winner_decision_paths(self) -> None:
        src = inspect.getsource(rv2.apply_win5_repick_v2)
        src_sel = inspect.getsource(rv2._select_rp_v2_a_near_candidate)
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
