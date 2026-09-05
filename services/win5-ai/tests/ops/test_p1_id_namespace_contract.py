# -*- coding: utf-8 -*-
"""P1 compatibility: meeting counts, order change, collisions, aliases, multi-date."""
from __future__ import annotations

import os
import unittest

from tests.ops.helpers import isolated_env


def _index_from_meetings(date: str, meetings: list[tuple[str, str, str, str]]):
    from app.data.catalog_index import CatalogIndex

    idx = CatalogIndex()
    rows = []
    for course, label, jra, numeric_prefix in meetings:
        for race_no in range(1, 13):
            rows.append(
                {
                    "catalog_id": f"{date}-{label}-{race_no:02d}",
                    "date": date,
                    "course": course,
                    "race_no": race_no,
                    "numeric_race_id": f"{numeric_prefix}{race_no:02d}",
                }
            )
    idx.load_mapping(rows)
    return idx


class P1NamespaceCompatibilityTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["CATALOG_INDEX_DISABLE_PI"] = "1"

    def _resolve_all(self, date: str, meetings):
        from app.data.catalog_index import reset_catalog_index_for_tests
        from app.data.race_resolver import RaceResolver, reset_resolver_for_tests

        idx = _index_from_meetings(date, meetings)
        reset_catalog_index_for_tests(idx)
        reset_resolver_for_tests()
        resolver = RaceResolver(catalog=idx)
        idents = []
        for course, label, jra, numeric_prefix in meetings:
            for race_no in range(1, 13):
                cid = f"{date}-{label}-{race_no:02d}"
                ident = resolver.resolve(cid)
                self.assertIsNotNone(ident, cid)
                assert ident is not None
                self.assertEqual(ident.venue_ja, course, cid)
                self.assertEqual(ident.race_no, race_no, cid)
                self.assertEqual(ident.feature_lookup_key, cid, cid)
                self.assertEqual(ident.core_race_id, f"{date}-{jra}-{race_no:02d}", cid)
                self.assertEqual(ident.numeric_race_id, f"{numeric_prefix}{race_no:02d}", cid)
                idents.append(ident)
        return idents

    def test_one_venue_day(self) -> None:
        with isolated_env():
            idents = self._resolve_all(
                "2026-09-06",
                [("札幌", "01", "01", "2026010109")],
            )
            self.assertEqual(len(idents), 12)
            self.assertEqual(len({i.catalog_race_id for i in idents}), 12)
            self.assertEqual(len({i.core_race_id for i in idents}), 12)
            self.assertEqual(len({i.feature_lookup_key for i in idents}), 12)
            # 1場で label==JRA のとき文字列は一致してよい。空間は別。
            ten = next(i for i in idents if i.race_no == 10)
            self.assertEqual(ten.catalog_race_id, ten.core_race_id)
            self.assertEqual(ten.feature_lookup_key, ten.catalog_race_id)
            self.assertEqual(ten.catalog_ref.meeting_label, "01")
            self.assertEqual(ten.core_ref.jra_venue_code, "01")

    def test_two_venue_day(self) -> None:
        with isolated_env():
            idents = self._resolve_all(
                "2026-09-13",
                [
                    ("新潟", "01", "04", "2026040210"),
                    ("札幌", "02", "01", "2026010110"),
                ],
            )
            self.assertEqual(len(idents), 24)
            sapporo_10 = next(i for i in idents if i.venue_ja == "札幌" and i.race_no == 10)
            self.assertEqual(sapporo_10.catalog_race_id, "2026-09-13-02-10")
            self.assertEqual(sapporo_10.core_race_id, "2026-09-13-01-10")
            self.assertEqual(sapporo_10.feature_lookup_key, "2026-09-13-02-10")
            self.assertNotEqual(sapporo_10.feature_lookup_key, sapporo_10.core_race_id)

    def test_three_venue_day(self) -> None:
        with isolated_env():
            idents = self._resolve_all(
                "2026-08-16",
                [
                    ("新潟", "01", "04", "2026040208"),
                    ("中京", "02", "07", "2026070208"),
                    ("札幌", "03", "01", "2026010108"),
                ],
            )
            self.assertEqual(len(idents), 36)
            self.assertEqual(len({i.feature_lookup_key for i in idents}), 36)

    def test_meeting_order_change(self) -> None:
        with isolated_env():
            # 同じ3場だが開催順が逆。label は変わる。JRA Core は変わらない。
            idents = self._resolve_all(
                "2026-09-20",
                [
                    ("札幌", "01", "01", "2026010111"),
                    ("中京", "02", "07", "2026070211"),
                    ("新潟", "03", "04", "2026040211"),
                ],
            )
            niigata_10 = next(i for i in idents if i.venue_ja == "新潟" and i.race_no == 10)
            self.assertEqual(niigata_10.catalog_race_id, "2026-09-20-03-10")
            self.assertEqual(niigata_10.core_race_id, "2026-09-20-04-10")
            self.assertEqual(niigata_10.feature_lookup_key, "2026-09-20-03-10")
            self.assertNotEqual(niigata_10.venue_ja, "函館")

    def test_same_shaped_catalog_core_collision(self) -> None:
        with isolated_env():
            from app.data.catalog_index import reset_catalog_index_for_tests
            from app.data.race_resolver import RaceResolver, reset_resolver_for_tests

            idx = _index_from_meetings(
                "2026-08-16",
                [
                    ("新潟", "01", "04", "2026040208"),
                    ("中京", "02", "07", "2026070208"),
                    ("札幌", "03", "01", "2026010108"),
                ],
            )
            reset_catalog_index_for_tests(idx)
            reset_resolver_for_tests()
            resolver = RaceResolver(catalog=idx)
            catalog_niigata = resolver.resolve("2026-08-16-01-10")
            catalog_sapporo = resolver.resolve("2026-08-16-03-10")
            assert catalog_niigata is not None and catalog_sapporo is not None
            self.assertEqual(catalog_niigata.venue_ja, "新潟")
            self.assertEqual(catalog_sapporo.venue_ja, "札幌")
            self.assertEqual(catalog_niigata.core_race_id, "2026-08-16-04-10")
            self.assertEqual(catalog_sapporo.core_race_id, "2026-08-16-01-10")
            self.assertEqual(catalog_sapporo.feature_lookup_key, "2026-08-16-03-10")
            self.assertEqual(catalog_niigata.feature_lookup_key, "2026-08-16-01-10")
            self.assertEqual(catalog_niigata.catalog_race_id, catalog_sapporo.core_race_id)

    def test_multiple_dates(self) -> None:
        with isolated_env():
            from app.data.catalog_index import CatalogIndex, reset_catalog_index_for_tests
            from app.data.race_resolver import RaceResolver, reset_resolver_for_tests

            idx = CatalogIndex()
            idx.load_mapping(
                [
                    {
                        "catalog_id": "2026-08-16-03-10",
                        "date": "2026-08-16",
                        "course": "札幌",
                        "race_no": 10,
                        "numeric_race_id": "202601010810",
                    },
                    {
                        "catalog_id": "2026-08-23-01-10",
                        "date": "2026-08-23",
                        "course": "札幌",
                        "race_no": 10,
                        "numeric_race_id": "202601020810",
                    },
                ]
            )
            reset_catalog_index_for_tests(idx)
            reset_resolver_for_tests()
            resolver = RaceResolver(catalog=idx)
            a = resolver.resolve("2026-08-16-03-10")
            b = resolver.resolve("2026-08-23-01-10")
            assert a is not None and b is not None
            self.assertEqual(a.feature_lookup_key, "2026-08-16-03-10")
            self.assertEqual(b.feature_lookup_key, "2026-08-23-01-10")
            self.assertEqual(a.core_race_id, "2026-08-16-01-10")
            self.assertEqual(b.core_race_id, "2026-08-23-01-10")
            self.assertNotEqual(a.feature_lookup_key, b.feature_lookup_key)

    def test_aliases_share_feature_lookup(self) -> None:
        with isolated_env():
            from app.data.catalog_index import reset_catalog_index_for_tests
            from app.data.race_resolver import RaceResolver, reset_resolver_for_tests

            reset_catalog_index_for_tests()
            reset_resolver_for_tests()
            resolver = RaceResolver()
            for raw, ns in (
                ("2026-08-16-03-10", "catalog"),
                ("2026-08-16-札幌-10", "venue_qualified"),
                ("20260816_sapporo_10", "slug"),
                ("202601010810", "numeric"),
            ):
                ident = resolver.resolve(raw)
                self.assertIsNotNone(ident, raw)
                assert ident is not None
                self.assertEqual(ident.id_namespace, ns, raw)
                self.assertEqual(ident.feature_lookup_key, "2026-08-16-03-10", raw)
                self.assertEqual(ident.core_race_id, "2026-08-16-01-10", raw)
                self.assertEqual(ident.numeric_race_id, "202601010810", raw)
                self.assertEqual(ident.venue_ja, "札幌", raw)
                self.assertEqual(ident.race_no, 10, raw)


if __name__ == "__main__":
    unittest.main()
