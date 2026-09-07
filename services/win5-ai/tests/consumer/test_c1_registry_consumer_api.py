# -*- coding: utf-8 -*-
"""Phase C1 — Decision Registry + Single Consumer API skeleton."""
from __future__ import annotations

import copy
import os
import unittest

from app.consumer.core_client import InMemoryCoreClient
from app.consumer.core_payload import fingerprint_payload
from app.consumer.flags import snapshot_consumer_flags
from app.consumer.registry import (
    FALLBACK_POLICY,
    PURE_RESIDUAL_POLICY,
    registry_holds_prediction,
    resolve_policy,
)
from app.consumer.single_api import (
    CONSUMER_SCHEMA,
    ConsumerDisabledError,
    assert_core_untouched,
    build_single_response,
)


def _core(
    race_id: str = "r1",
    world_id: str = "rank7_world",
    *,
    near_miss: dict | None = None,
    prediction: dict | None = None,
) -> dict:
    return {
        "schema": "core-semantic-payload/v1",
        "race_id": race_id,
        "world_id": world_id,
        "prediction": prediction
        or {
            "ranks": ["A", "B", "C"],
            "scores": [0.4, 0.3, 0.2],
            "top1": "A",
        },
        "decision_trace": {},
        "transition": None,
        "near_miss": near_miss,
        "affinity": None,
        "exclusion_reasons": {},
        "explanation_confidence": None,
        "expected_strategy_ref": {"registry": "v75-expected-strategy", "key": world_id},
    }


class RegistryTest(unittest.TestCase):
    def test_rank7_policy(self):
        r = resolve_policy(_core(world_id="rank7_world"))
        self.assertEqual(r.policy_id, "policy_rank7_ready")
        self.assertFalse(registry_holds_prediction(r))

    def test_near_miss_conservative(self):
        r = resolve_policy(
            _core(
                world_id="unsatisfied",
                near_miss={
                    "residual_class": "NEAR_MISS",
                    "near_world": "core_world",
                },
            )
        )
        self.assertEqual(r.policy_id, "policy_near_miss_core_conservative")
        self.assertEqual(r.near_world, "core_world")

    def test_pure_residual(self):
        r = resolve_policy(
            _core(
                world_id="unsatisfied",
                near_miss={"residual_class": "PURE_RESIDUAL", "near_world": None},
            )
        )
        self.assertEqual(r.policy_id, PURE_RESIDUAL_POLICY)

    def test_unknown_world_fallback(self):
        r = resolve_policy(_core(world_id="totally_new_world"))
        self.assertEqual(r.policy_id, FALLBACK_POLICY)

    def test_registry_ignores_prediction_content(self):
        a = resolve_policy(_core(prediction={"ranks": ["A"], "scores": [1.0], "top1": "A"}))
        b = resolve_policy(_core(prediction={"ranks": ["Z"], "scores": [0.0], "top1": "Z"}))
        self.assertEqual(a.policy_id, b.policy_id)
        self.assertEqual(a.strategy_id, b.strategy_id)


class ConsumerApiC1Test(unittest.TestCase):
    def setUp(self):
        for k in list(os.environ.keys()):
            if k.startswith("W_CONSUMER_") or k.startswith("W_CORE_") or k.startswith("W_DECISION_"):
                os.environ.pop(k, None)
        self.client = InMemoryCoreClient()
        self.original = _core("r1", "rank7_world")
        self.client.put_for_test("r1", self.original)
        self.stored_before = copy.deepcopy(self.client._store["r1"])

    def test_flags_default_off(self):
        for k, v in snapshot_consumer_flags().items():
            self.assertFalse(v, k)

    def test_disabled_without_force(self):
        with self.assertRaises(ConsumerDisabledError):
            build_single_response(self.client, "r1")

    def test_skeleton_response(self):
        resp = build_single_response(self.client, "r1", force=True)
        self.assertEqual(resp["schema"], CONSUMER_SCHEMA)
        self.assertEqual(resp["registry"]["policy_id"], "policy_rank7_ready")
        self.assertIsNone(resp["ticket"])
        self.assertIsNone(resp["presentation"])
        self.assertEqual(resp["core_ref"]["race_id"], "r1")
        self.assertTrue(resp["core_ref"]["payload_fingerprint"])

    def test_core_not_mutated(self):
        before_fp = fingerprint_payload(self.stored_before)
        build_single_response(self.client, "r1", force=True)
        after = self.client._store["r1"]
        assert_core_untouched(self.stored_before, after)
        self.assertEqual(fingerprint_payload(after), before_fp)
        # Caller-held original also untouched
        assert_core_untouched(self.original, self.original)

    def test_get_returns_independent_copy(self):
        p1 = self.client.get("r1")
        p1["world_id"] = "hacked"
        p2 = self.client.get("r1")
        self.assertEqual(p2["world_id"], "rank7_world")

    def test_options_warn_not_implemented(self):
        resp = build_single_response(
            self.client, "r1", force=True, include_tickets=True, include_presentation=True
        )
        # C3: tickets resolved in Shadow when force + include_tickets
        self.assertIsNotNone(resp["ticket"])
        self.assertIsNone(resp["ticket"]["reason"])
        self.assertIsNotNone(resp["presentation"])
        self.assertIsNone(resp["presentation"]["natural_explanation"])


if __name__ == "__main__":
    unittest.main()
