# -*- coding: utf-8 -*-
"""Unit tests — Pool+Entry v2 (Flag OFF identity)."""
from __future__ import annotations

import unittest

import v2_pool_entry_v2 as pe


class TestPoolEntryV2Identity(unittest.TestCase):
    def setUp(self) -> None:
        pe.apply_win5_pool_entry_v2_flags(False)

    def test_flag_off_identity(self) -> None:
        pool = [{"horse_name": "A", "model_rank": 1}]
        cands = [{"horse_name": "B", "model_rank": 11}]
        meta: dict = {}
        out = pe.apply_win5_pool_entry_v2(pool, cands, meta)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["horse_name"], "A")
        j = meta.get("_win5_pool_entry_v2_journal") or {}
        self.assertFalse(j.get("fired"))
        self.assertEqual(j.get("reason"), "disabled")

    def test_flag_toggle(self) -> None:
        info = pe.apply_win5_pool_entry_v2_flags(True)
        self.assertTrue(info["WIN5_POOL_ENTRY_V2_ENABLED"])
        pe.apply_win5_pool_entry_v2_flags(False)
        info2 = pe.apply_win5_pool_entry_v2_flags(None)
        self.assertFalse(info2["WIN5_POOL_ENTRY_V2_ENABLED"])


if __name__ == "__main__":
    unittest.main()
