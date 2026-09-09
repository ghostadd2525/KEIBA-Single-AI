# -*- coding: utf-8 -*-
"""
PHASE PROD-PREDICTION-RECOVERY-01 — Catalog vs Core ID namespace contract.

2026-08-16 全36レース: Catalog ID → venue/race → Core ID。
形式 YYYY-MM-DD-NN-NN から意味を推測しない。
"""
from __future__ import annotations

import os
import unittest

from tests.ops.helpers import isolated_env, import_sample_data

DATE = "2026-08-16"
TARGET_CATALOG_ID = "2026-08-16-03-10"
TARGET_CORE_ID = "2026-08-16-01-10"
MAIDEN_CATALOG_ID = "2026-08-16-03-05"
MAIDEN_CORE_ID = "2026-08-16-01-05"

# 8/16 開催順（Catalog label_no）。JRA venue code ではない。
MEETINGS = (
    ("新潟", "01", "04", "2026040208"),
    ("中京", "02", "07", "2026070208"),
    ("札幌", "03", "01", "2026010108"),
)


def _expected_rows() -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for course, label, jra, numeric_prefix in MEETINGS:
        for race_no in range(1, 13):
            rows.append(
                {
                    "catalog_id": f"{DATE}-{label}-{race_no:02d}",
                    "course": course,
                    "race_no": race_no,
                    "jra_venue_code": jra,
                    "core_id": f"{DATE}-{jra}-{race_no:02d}",
                    "numeric_race_id": f"{numeric_prefix}{race_no:02d}",
                }
            )
    return rows


class CatalogCoreBridge20260816Test(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["CATALOG_INDEX_DISABLE_PI"] = "1"

    def test_36_race_catalog_to_core_mapping(self) -> None:
        with isolated_env():
            from app.data.catalog_index import get_catalog_index, reset_catalog_index_for_tests
            from app.data.race_resolver import (
                RaceResolver,
                _VENUE_CODE_TO_JA,
                reset_resolver_for_tests,
            )

            reset_catalog_index_for_tests()
            reset_resolver_for_tests()
            idx = get_catalog_index()
            resolver = RaceResolver()
            expected = _expected_rows()

            self.assertEqual(len(expected), 36)
            catalog_ids = [str(r["catalog_id"]) for r in expected]
            self.assertEqual(len(set(catalog_ids)), 36, "36/36 unique source IDs")

            # レガシー Core map は 03=函館のまま（cleanup しない）
            self.assertEqual(_VENUE_CODE_TO_JA.get("03"), "函館")

            core_ids: list[str] = []
            contamination = 0
            for row in expected:
                cid = str(row["catalog_id"])
                ident = resolver.resolve(cid)
                self.assertIsNotNone(ident, cid)
                assert ident is not None
                self.assertEqual(ident.id_namespace, "catalog", cid)
                self.assertEqual(ident.venue_ja, row["course"], cid)
                self.assertEqual(ident.race_no, row["race_no"], cid)
                self.assertEqual(ident.core_race_id, row["core_id"], cid)
                self.assertEqual(ident.catalog_race_id, cid, cid)
                self.assertEqual(ident.numeric_race_id, row["numeric_race_id"], cid)
                self.assertEqual(ident.feature_lookup_key, cid, cid)
                self.assertIsNotNone(ident.catalog_ref, cid)
                self.assertIsNotNone(ident.numeric_ref, cid)
                self.assertIsNotNone(ident.core_ref, cid)
                self.assertIsNotNone(ident.feature_lookup_ref, cid)
                assert ident.feature_lookup_ref is not None
                assert ident.core_ref is not None
                self.assertEqual(ident.feature_lookup_ref.as_id(), cid, cid)
                self.assertEqual(ident.core_ref.as_id(), row["core_id"], cid)
                self.assertNotEqual(
                    ident.feature_lookup_key,
                    ident.core_race_id,
                    f"FeatureLookup must not be Core for 3-venue day: {cid}",
                )
                self.assertEqual(ident.venue_code, row["jra_venue_code"], cid)
                self.assertNotEqual(
                    ident.venue_ja,
                    _VENUE_CODE_TO_JA.get(cid.split("-")[3]),
                    f"must not use Win5 label_no as legacy venue code: {cid}",
                )
                core_ids.append(str(ident.core_race_id))

                # Catalog label の開催場と Core JRA 開催場が食い違うこと自体は正常。
                # 別開催場の identity が混ざるのが contamination。
                cat_course = str(row["course"])
                if ident.venue_ja != cat_course:
                    contamination += 1

            self.assertEqual(contamination, 0, "cross-venue contamination must be 0")
            self.assertEqual(len(core_ids), 36)
            self.assertEqual(len(set(core_ids)), 36, "36 unique Core IDs")
            feature_keys = [str(resolver.resolve(str(r["catalog_id"])).feature_lookup_key) for r in expected]
            self.assertEqual(len(set(feature_keys)), 36, "36 unique FeatureLookupRef")
            self.assertEqual(set(feature_keys), set(catalog_ids))

            catalog_set = set(catalog_ids)
            core_set = set(core_ids)
            collisions = catalog_set & core_set
            self.assertIn(
                "2026-08-16-01-10",
                collisions,
                "Catalog 新潟10R and Core 札幌10R share the same string",
            )
            niigata_ten = resolver.resolve("2026-08-16-01-10")
            assert niigata_ten is not None
            self.assertEqual(niigata_ten.venue_ja, "新潟")
            self.assertEqual(niigata_ten.core_race_id, "2026-08-16-04-10")
            self.assertEqual(niigata_ten.id_namespace, "catalog")

            sapporo_ten = resolver.resolve(TARGET_CATALOG_ID)
            assert sapporo_ten is not None
            self.assertEqual(sapporo_ten.venue_ja, "札幌")
            self.assertEqual(sapporo_ten.core_race_id, TARGET_CORE_ID)
            self.assertEqual(sapporo_ten.feature_lookup_key, TARGET_CATALOG_ID)
            self.assertEqual(sapporo_ten.numeric_race_id, "202601010810")
            self.assertEqual(sapporo_ten.race_no, 10)

            # 同一 Core 文字列を Catalog 経由で取ると新潟、Catalog 03-10 経由だと札幌
            self.assertNotEqual(niigata_ten.venue_ja, sapporo_ten.venue_ja)

            catalog_by_course = {"新潟": [], "中京": [], "札幌": []}
            for row, ident_core in zip(expected, core_ids):
                catalog_by_course[str(row["course"])].append(ident_core)
            for course, cores in catalog_by_course.items():
                for core_id in cores:
                    jra = core_id.split("-")[3]
                    mapped_course = {
                        "04": "新潟",
                        "07": "中京",
                        "01": "札幌",
                    }[jra]
                    self.assertEqual(mapped_course, course, core_id)

            self.assertEqual(len(idx.all_for_date(DATE)), 36)

    def test_target_race_namespaces(self) -> None:
        with isolated_env():
            from app.data.race_resolver import RaceResolver, reset_resolver_for_tests
            from app.data.catalog_index import reset_catalog_index_for_tests

            reset_catalog_index_for_tests()
            reset_resolver_for_tests()
            resolver = RaceResolver()

            catalog = resolver.resolve(TARGET_CATALOG_ID)
            venue_q = resolver.resolve("2026-08-16-札幌-10")
            slug = resolver.resolve("20260816_sapporo_10")
            numeric = resolver.resolve("202601010810")
            for ident, ns in (
                (catalog, "catalog"),
                (venue_q, "venue_qualified"),
                (slug, "slug"),
                (numeric, "numeric"),
            ):
                self.assertIsNotNone(ident, ns)
                assert ident is not None
                self.assertEqual(ident.id_namespace, ns)
                self.assertEqual(ident.venue_ja, "札幌")
                self.assertEqual(ident.race_no, 10)
                self.assertEqual(ident.core_race_id, TARGET_CORE_ID)
                self.assertEqual(ident.feature_lookup_key, TARGET_CATALOG_ID)
                self.assertEqual(ident.numeric_race_id, "202601010810")
                self.assertNotEqual(ident.venue_ja, "函館")

    def test_maiden_identity_only_no_routing_change(self) -> None:
        """
        MAIDEN_ROUTING_SUSPECT: 札幌5R 2歳新馬。
        今回は race identity のみ確認。routing / race_type は修正しない。
        """
        with isolated_env():
            from app.data.catalog_index import get_catalog_index, reset_catalog_index_for_tests
            from app.data.race_resolver import RaceResolver, reset_resolver_for_tests

            reset_catalog_index_for_tests()
            reset_resolver_for_tests()
            row = get_catalog_index().lookup_catalog_id(MAIDEN_CATALOG_ID)
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row.course, "札幌")
            self.assertEqual(row.race_no, 5)
            self.assertIn("新馬", row.race_name)
            ident = RaceResolver().resolve(MAIDEN_CATALOG_ID)
            self.assertIsNotNone(ident)
            assert ident is not None
            self.assertEqual(ident.venue_ja, "札幌")
            self.assertEqual(ident.race_no, 5)
            self.assertEqual(ident.core_race_id, MAIDEN_CORE_ID)
            self.assertEqual(ident.id_namespace, "catalog")
            self.assertFalse(hasattr(ident, "race_type") and getattr(ident, "race_type"))

    def test_legacy_core_sample_not_reinterpreted(self) -> None:
        with isolated_env():
            from app.data.db import migrate
            from app.data.race_resolver import resolve_identity, reset_resolver_for_tests
            from app.data.catalog_index import reset_catalog_index_for_tests

            reset_catalog_index_for_tests()
            reset_resolver_for_tests()
            migrate()
            import_sample_data()
            ident = resolve_identity("2026-07-19-04-11")
            self.assertIsNotNone(ident)
            assert ident is not None
            self.assertEqual(ident.core_race_id, "2026-07-19-04-11")
            self.assertEqual(ident.venue_ja, "福島")


class TargetPredictionFallbackTest(unittest.TestCase):
    def test_target_uses_feature_lookup_not_core(self) -> None:
        with isolated_env(engine="real"):
            os.environ["CATALOG_INDEX_DISABLE_PI"] = "1"
            from app.data.catalog_index import reset_catalog_index_for_tests
            from app.data.race_resolver import reset_resolver_for_tests
            from app.engine.adapters import single_prediction_mapper as mapper

            reset_catalog_index_for_tests()
            reset_resolver_for_tests()

            diag = mapper.diagnose_inference(TARGET_CATALOG_ID)
            self.assertEqual(diag.get("core_race_id"), TARGET_CORE_ID)
            self.assertEqual(diag.get("feature_lookup_key"), TARGET_CATALOG_ID)
            self.assertEqual(diag.get("numeric_race_id"), "202601010810")
            self.assertNotEqual(diag.get("fallback_reason"), "race_not_found")
            self.assertNotEqual(diag.get("detail"), "no resolvable core race_id")
            self.assertNotEqual(diag.get("feature_lookup_key"), diag.get("core_race_id"))


if __name__ == "__main__":
    unittest.main()
