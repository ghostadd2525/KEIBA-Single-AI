# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.race_identity import catalog_identity_metadata


class IdentityMetadataTest(unittest.TestCase):
    def test_feature_lookup_stays_catalog_not_core(self):
        meta = catalog_identity_metadata(
            date="2026-08-16",
            catalog_race_id="2026-08-16-03-10",
            numeric_race_id="202601010810",
            course="札幌",
            race_number=10,
        )
        self.assertEqual(meta["feature_lookup_key"], "2026-08-16-03-10")
        self.assertEqual(meta["catalog_race_id"], "2026-08-16-03-10")
        self.assertEqual(meta["core_race_id"], "2026-08-16-01-10")
        self.assertEqual(meta["jra_venue_code"], "01")
        self.assertNotEqual(meta["feature_lookup_key"], meta["core_race_id"])


if __name__ == "__main__":
    unittest.main()
