# -*- coding: utf-8 -*-
"""Phase I1 — Existing Site Integration tests."""
from __future__ import annotations

import os
import unittest

from app.site_integration.config import SiteIntegrationConfig
from app.site_integration.handlers import (
    handle_health,
    handle_openapi,
    handle_site_single,
    handle_version,
)
from app.site_integration.race_id import normalize_race_id, parse_race_id_meta
from app.site_integration.validation import SiteValidationError, validate_site_single_request


def _core(race_id: str = "20260719_hanshin_11") -> dict:
    return {
        "schema": "core-semantic-payload/v1",
        "race_id": race_id,
        "world_id": "rank7_world",
        "prediction": {"ranks": ["A", "B", "C"], "scores": [0.4, 0.3, 0.2], "top1": "A"},
        "decision_trace": {},
        "transition": None,
        "near_miss": None,
        "affinity": None,
        "exclusion_reasons": {},
        "explanation_confidence": None,
        "expected_strategy_ref": {"registry": "v75-expected-strategy", "key": "rank7_world"},
    }


class RaceIdI1Test(unittest.TestCase):
    def test_slug_meta(self):
        meta = parse_race_id_meta("20260719_hanshin_11")
        self.assertEqual(meta["form"], "ymd_venue_no")
        self.assertEqual(meta["venue"], "hanshin")
        self.assertEqual(meta["race_no"], 11)

    def test_reject_path(self):
        with self.assertRaises(Exception):
            normalize_race_id("../x")


class ValidationI1Test(unittest.TestCase):
    def test_requires_core(self):
        with self.assertRaises(SiteValidationError) as ctx:
            validate_site_single_request({"race_id": "r1"})
        self.assertEqual(ctx.exception.code, "CORE_PAYLOAD_REQUIRED")

    def test_ok(self):
        req = validate_site_single_request(
            {"race_id": "20260719_hanshin_11", "core_payload": _core()}
        )
        self.assertEqual(req["race_id"], "20260719_hanshin_11")


class HandlersI1Test(unittest.TestCase):
    def setUp(self):
        for k in list(os.environ.keys()):
            if (
                k.startswith("W_CONSUMER_")
                or k.startswith("SITE_SINGLE_")
                or k.startswith("W_CORE_")
            ):
                os.environ.pop(k, None)
        self.cfg = SiteIntegrationConfig(
            http_enabled=True,
            require_api_key=False,
            default_timeout_ms=5000,
            max_timeout_ms=10000,
        )

    def test_health_version_openapi(self):
        self.assertEqual(handle_health(self.cfg)[0], 200)
        self.assertEqual(handle_version(self.cfg)[0], 200)
        status, doc = handle_openapi(self.cfg)
        self.assertEqual(status, 200)
        self.assertEqual(doc["openapi"], "3.0.3")

    def test_site_single_force(self):
        status, body = handle_site_single(
            {
                "race_id": "20260719_hanshin_11",
                "core_payload": _core(),
                "force": True,
            },
            cfg=self.cfg,
            authorized=True,
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["data"]["schema"], "site-integration/single/v1")
        self.assertEqual(body["data"]["single"]["schema"], "consumer-api/single/v1")
        self.assertIsNone(body["data"]["single"]["natural_explanation"])

    def test_path_race_id(self):
        status, body = handle_site_single(
            {"core_payload": _core(), "force": True},
            path_race_id="20260719_hanshin_11",
            cfg=self.cfg,
            authorized=True,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["race_id"], "20260719_hanshin_11")

    def test_consumer_disabled(self):
        status, body = handle_site_single(
            {"race_id": "20260719_hanshin_11", "core_payload": _core()},
            cfg=self.cfg,
            authorized=True,
        )
        self.assertEqual(status, 503)
        self.assertEqual(body["error"]["code"], "CONSUMER_DISABLED")

    def test_unauthorized(self):
        cfg = SiteIntegrationConfig(http_enabled=True, require_api_key=True)
        status, body = handle_site_single(
            {"race_id": "r1", "core_payload": _core("r1"), "force": True},
            cfg=cfg,
            authorized=False,
        )
        self.assertEqual(status, 401)


if __name__ == "__main__":
    unittest.main()
