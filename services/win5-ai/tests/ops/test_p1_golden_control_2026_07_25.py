# -*- coding: utf-8 -*-
"""
P1 golden: 2026-07-25-01-05 must keep existing Feature lookup.

Production daily CSV は Catalog/Win5 ID をキーにする。
JRA Core 2026-07-25-04-05 に lookup を載せ替えてはならない。
RESTORED_V2 / キシダンチョウ のスコアは変更しない（配線のみ）。
"""
from __future__ import annotations

import os
import unittest

from tests.ops.helpers import import_sample_data, isolated_env

CONTROL_ID = "2026-07-25-01-05"
CONTROL_FEATURE_KEY = "2026-07-25-01-05"
CONTROL_JRA_CORE = "2026-07-25-04-05"
CONTROL_NUMERIC = "202604070105"
CONTROL_TOP1 = "キシダンチョウ"


class P1GoldenControl20260725Test(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["CATALOG_INDEX_DISABLE_PI"] = "1"

    def test_control_refs_keep_catalog_feature_lookup(self) -> None:
        with isolated_env():
            from app.data.catalog_index import reset_catalog_index_for_tests
            from app.data.race_resolver import RaceResolver, reset_resolver_for_tests

            reset_catalog_index_for_tests()
            reset_resolver_for_tests()
            ident = RaceResolver().resolve(CONTROL_ID)
            self.assertIsNotNone(ident)
            assert ident is not None
            self.assertEqual(ident.catalog_race_id, CONTROL_ID)
            self.assertEqual(ident.feature_lookup_key, CONTROL_FEATURE_KEY)
            self.assertEqual(ident.numeric_race_id, CONTROL_NUMERIC)
            self.assertEqual(ident.core_race_id, CONTROL_JRA_CORE)
            self.assertEqual(ident.venue_ja, "新潟")
            self.assertEqual(ident.race_no, 5)
            self.assertNotEqual(ident.feature_lookup_key, ident.core_race_id)

    def test_feature_loader_hits_catalog_key_not_jra_core(self) -> None:
        from app.data.race_refs import matches_feature_lookup

        row = {
            "race_id": CONTROL_FEATURE_KEY,
            "numeric_race_id": CONTROL_NUMERIC,
            "horse_name": CONTROL_TOP1,
        }
        self.assertTrue(
            matches_feature_lookup(
                race_id=row["race_id"],
                lookup_key=CONTROL_FEATURE_KEY,
                numeric_race_id=row["numeric_race_id"],
            )
        )
        self.assertFalse(
            matches_feature_lookup(
                race_id=row["race_id"],
                lookup_key=CONTROL_JRA_CORE,
            ),
            "CoreRaceRef must not match a Catalog-keyed feature row",
        )
        self.assertEqual(row["horse_name"], CONTROL_TOP1)

    def test_diagnose_uses_feature_lookup_key(self) -> None:
        with isolated_env(engine="real"):
            from app.data.catalog_index import reset_catalog_index_for_tests
            from app.data.race_resolver import reset_resolver_for_tests
            from app.engine.adapters import single_prediction_mapper as mapper

            reset_catalog_index_for_tests()
            reset_resolver_for_tests()
            diag = mapper.diagnose_inference(CONTROL_ID)
            self.assertEqual(diag.get("feature_lookup_key"), CONTROL_FEATURE_KEY)
            self.assertEqual(diag.get("core_race_id"), CONTROL_JRA_CORE)
            self.assertNotEqual(diag.get("feature_lookup_key"), diag.get("core_race_id"))

    def test_legacy_core_sample_still_looks_up_core_string(self) -> None:
        with isolated_env():
            from app.data.db import migrate
            from app.data.catalog_index import reset_catalog_index_for_tests
            from app.data.race_resolver import resolve_identity, reset_resolver_for_tests

            reset_catalog_index_for_tests()
            reset_resolver_for_tests()
            migrate()
            import_sample_data()
            ident = resolve_identity("2026-07-19-04-11")
            self.assertIsNotNone(ident)
            assert ident is not None
            self.assertEqual(ident.core_race_id, "2026-07-19-04-11")
            self.assertEqual(ident.feature_lookup_key, "2026-07-19-04-11")
            self.assertEqual(ident.venue_ja, "福島")
            self.assertEqual(ident.id_namespace, "core")


if __name__ == "__main__":
    unittest.main()
