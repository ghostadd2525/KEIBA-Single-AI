# -*- coding: utf-8 -*-
"""RaceResolver identity recovery — 2026-08-23 36R."""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

os.environ["CATALOG_INDEX_DISABLE_PI"] = "1"

from app.data.catalog_index import CatalogIndex, _fetch_pi_races, reset_catalog_index_for_tests
from app.data.race_resolver import resolve_identity

_FIXTURE = Path(__file__).resolve().parents[1] / "app" / "data" / "catalog_fixtures" / "2026-08-23.json"


class TestCatalogIndex20260823(unittest.TestCase):
    def setUp(self) -> None:
        idx = CatalogIndex()
        idx.load_builtin_fixtures()
        reset_catalog_index_for_tests(idx)

    def test_fixture_36r_core_ids(self) -> None:
        rows = json.loads(_FIXTURE.read_text(encoding="utf-8-sig"))["races"]
        self.assertEqual(len(rows), 36)
        for row in rows:
            ident = resolve_identity(row["catalog_id"])
            self.assertIsNotNone(ident, row["catalog_id"])
            assert ident is not None
            self.assertEqual(ident.core_race_id, row["core_race_id"], row["catalog_id"])

    def test_sapporo_10r(self) -> None:
        ident = resolve_identity("2026-08-23-03-10")
        self.assertIsNotNone(ident)
        assert ident is not None
        self.assertEqual(ident.venue_ja, "札幌")
        self.assertEqual(ident.core_race_id, "2026-08-23-01-10")

    def test_fetch_pi_flattens_venues(self) -> None:
        payload = {
            "ok": True,
            "data": {
                "date": "2026-08-23",
                "venues": [
                    {
                        "venue": "札幌",
                        "races": [
                            {"race_id": "2026-08-23-03-10", "date": "2026-08-23", "course": "札幌", "race_no": 10, "numeric_race_id": "202601020210"}
                        ],
                    }
                ],
            },
        }
        import urllib.request
        from unittest import mock

        class _Resp:
            def read(self):
                return json.dumps(payload).encode()

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        with mock.patch.dict(os.environ, {"PI_BASE_URL": "http://pi.test", "CATALOG_INDEX_DISABLE_PI": "0"}):
            with mock.patch("urllib.request.urlopen", return_value=_Resp()):
                rows = _fetch_pi_races("2026-08-23")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["race_id"], "2026-08-23-03-10")


if __name__ == "__main__":
    unittest.main()
