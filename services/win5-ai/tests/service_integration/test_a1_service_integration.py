# -*- coding: utf-8 -*-
"""Phase A1 — Service Integration (HTTP Application over Single AI library)."""
from __future__ import annotations

import copy
import os
import unittest

from app.consumer.core_payload import fingerprint_payload
from app.service_integration.config import SingleServiceConfig
from app.service_integration.handlers import (
    handle_health,
    handle_metrics,
    handle_openapi,
    handle_single_response,
)
from app.service_integration.validation import RequestValidationError, validate_single_response_request


def _core(race_id: str = "r1", world_id: str = "rank7_world") -> dict:
    return {
        "schema": "core-semantic-payload/v1",
        "race_id": race_id,
        "world_id": world_id,
        "prediction": {"ranks": ["A", "B", "C"], "scores": [0.4, 0.3, 0.2], "top1": "A"},
        "decision_trace": {},
        "transition": None,
        "near_miss": None,
        "affinity": None,
        "exclusion_reasons": {},
        "explanation_confidence": None,
        "expected_strategy_ref": {"registry": "v75-expected-strategy", "key": world_id},
    }


class ValidationA1Test(unittest.TestCase):
    def test_requires_core_payload(self):
        with self.assertRaises(RequestValidationError):
            validate_single_response_request({})

    def test_ok_minimal(self):
        req = validate_single_response_request({"core_payload": _core()})
        self.assertEqual(req["race_id"], "r1")
        self.assertFalse(req["include_tickets"])


class HandlersA1Test(unittest.TestCase):
    def setUp(self):
        for k in list(os.environ.keys()):
            if (
                k.startswith("W_CONSUMER_")
                or k.startswith("W_CORE_")
                or k.startswith("SINGLE_AI_")
            ):
                os.environ.pop(k, None)
        self.cfg = SingleServiceConfig(
            http_enabled=True,
            require_api_key=False,
            default_locale="ja",
        )

    def test_health(self):
        status, body = handle_health(self.cfg)
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["data"]["platform"], "CorePlatformVersion1")

    def test_openapi_raw(self):
        status, body = handle_openapi(self.cfg)
        self.assertEqual(status, 200)
        self.assertEqual(body["openapi"], "3.0.3")
        self.assertIn("/v1/single/response", body["paths"])

    def test_metrics(self):
        status, body = handle_metrics()
        self.assertEqual(status, 200)
        self.assertIn("requests_total", body["data"])

    def test_response_force_shadow(self):
        core = _core()
        before = copy.deepcopy(core)
        status, body = handle_single_response(
            {"core_payload": core, "force": True},
            cfg=self.cfg,
            authorized=True,
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertEqual(body["data"]["schema"], "consumer-api/single/v1")
        self.assertIsNone(body["data"]["natural_explanation"])
        self.assertIsNone(body["data"]["decision_reason"])
        self.assertEqual(fingerprint_payload(core), fingerprint_payload(before))

    def test_consumer_disabled_without_force(self):
        status, body = handle_single_response(
            {"core_payload": _core()},
            cfg=self.cfg,
            authorized=True,
        )
        self.assertEqual(status, 503)
        self.assertEqual(body["error"]["code"], "CONSUMER_DISABLED")

    def test_http_disabled(self):
        cfg = SingleServiceConfig(http_enabled=False, require_api_key=False)
        status, body = handle_single_response(
            {"core_payload": _core(), "force": True},
            cfg=cfg,
            authorized=True,
        )
        self.assertEqual(status, 503)
        self.assertEqual(body["error"]["code"], "SERVICE_DISABLED")

    def test_unauthorized_when_required(self):
        cfg = SingleServiceConfig(http_enabled=True, require_api_key=True)
        status, body = handle_single_response(
            {"core_payload": _core(), "force": True},
            cfg=cfg,
            authorized=False,
        )
        self.assertEqual(status, 401)

    def test_validation_error(self):
        status, body = handle_single_response({}, cfg=self.cfg, authorized=True)
        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["code"], "BAD_REQUEST")


if __name__ == "__main__":
    unittest.main()
