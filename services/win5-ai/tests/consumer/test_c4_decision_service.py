# -*- coding: utf-8 -*-
"""Phase C4 — Decision Service Composer integration tests."""
from __future__ import annotations

import copy
import json
import os
import unittest

from app.consumer.core_client import InMemoryCoreClient
from app.consumer.core_payload import fingerprint_payload
from app.consumer.decision_service.composer import (
    CompositionValidationError,
    assert_no_new_meaning,
    compose,
)
from app.consumer.decision_service.service import DecisionService
from app.consumer.presentation.renderer import render_presentation
from app.consumer.registry import resolve_policy
from app.consumer.single_api import assert_core_untouched, build_single_response
from app.consumer.ticket.resolver import resolve_ticket


def _core(race_id: str = "r4", world_id: str = "rank7_world") -> dict:
    return {
        "schema": "core-semantic-payload/v1",
        "race_id": race_id,
        "world_id": world_id,
        "prediction": {
            "ranks": ["A", "B", "C", "D", "E", "F", "G"],
            "scores": [0.3, 0.2, 0.1, 0.1, 0.1, 0.1, 0.1],
            "top1": "A",
        },
        "near_miss": None,
        "affinity": {"rank7_world": 0.9, "definition": "v96/must_affinity"},
        "explanation_confidence": {
            "explanation_confidence": 0.95,
            "definition_version": "v101/1.0",
        },
        "exclusion_reasons": {"midhole_world": ["x"]},
        "transition": "t1",
    }


class ComposerUnitTest(unittest.TestCase):
    def test_preserves_core_exact(self):
        core = _core()
        before = copy.deepcopy(core)
        res = resolve_policy(core)
        dto = compose(
            core_payload=core,
            policy_metadata={
                "policy_id": res.policy_id,
                "strategy_id": res.strategy_id,
                "registry_versions": list(res.registry_versions),
                "world_id": res.world_id,
            },
            presentation=None,
            ticket=None,
        )
        self.assertEqual(dto.core_payload, before)
        assert_core_untouched(before, core)

    def test_preserves_presentation_and_ticket(self):
        core = _core()
        pres = render_presentation(core).to_dict()
        tkt = resolve_ticket(
            "policy_rank7_ready", race_id="r4", prediction=core["prediction"]
        ).to_dict()
        pres_before = copy.deepcopy(pres)
        tkt_before = copy.deepcopy(tkt)
        dto = compose(
            core_payload=core,
            policy_metadata={"policy_id": "policy_rank7_ready", "strategy_id": "rank7_world"},
            presentation=pres,
            ticket=tkt,
        )
        self.assertEqual(dto.presentation, pres_before)
        self.assertEqual(dto.ticket, tkt_before)
        # Callers' objects unchanged
        self.assertEqual(pres, pres_before)
        self.assertEqual(tkt, tkt_before)

    def test_rejects_reason(self):
        core = _core()
        with self.assertRaises(CompositionValidationError):
            compose(
                core_payload=core,
                policy_metadata={"policy_id": "policy_rank7_ready"},
                ticket={"policy_id": "policy_rank7_ready", "reason": "because"},
            )

    def test_no_new_meaning(self):
        core = _core()
        dto = compose(
            core_payload=core,
            policy_metadata={"policy_id": "policy_rank7_ready"},
        )
        d = dto.to_dict()
        assert_no_new_meaning(d)
        self.assertIsNone(d["natural_explanation"])
        self.assertIsNone(d["decision_reason"])
        self.assertIn("composer", d["version"])


class DecisionServiceIntegrationTest(unittest.TestCase):
    def setUp(self):
        for k in list(os.environ.keys()):
            if k.startswith("W_CONSUMER_") or k.startswith("W_CORE_") or k.startswith("W_DECISION_"):
                os.environ.pop(k, None)
        self.client = InMemoryCoreClient()
        self.original = _core()
        self.client.put_for_test("r4", self.original)
        self.stored = copy.deepcopy(self.client._store["r4"])
        self.svc = DecisionService()

    def test_legacy_flag_off_compatible(self):
        legacy = self.svc.legacy_response(self.client, "r4", force=True)
        via_api = build_single_response(self.client, "r4", force=True)
        self.assertIsNone(legacy["presentation"])
        self.assertIsNone(legacy["ticket"])
        self.assertIsNone(via_api["presentation"])
        self.assertIsNone(via_api["ticket"])
        self.assertEqual(legacy["registry"]["policy_id"], via_api["registry"]["policy_id"])
        self.assertEqual(
            legacy["core_ref"]["payload_fingerprint"],
            via_api["core_ref"]["payload_fingerprint"],
        )
        self.assertEqual(legacy["mode"], "LEGACY")

    def test_core_payload_exact_in_response(self):
        resp = build_single_response(self.client, "r4", force=True)
        self.assertEqual(resp["core_payload"], self.stored)
        assert_core_untouched(self.stored, self.client._store["r4"])

    def test_compose_from_prebuilt_no_recalc(self):
        core = self.client.get("r4")
        pres = render_presentation(core).to_dict()
        # Deliberately odd ticket (still valid policy) — composer must not recalculate
        custom_ticket = {
            "schema": "ticket-plan/v1",
            "policy_id": "policy_rank7_ready",
            "template_id": "custom_shadow",
            "action": "BUY",
            "legs": [{"type": "win", "horse_id": "A", "stake": 1.0, "odds": None}],
            "pool": ["A"],
            "budget": 1.0,
            "reason": None,
            "warnings": [],
        }
        custom_before = copy.deepcopy(custom_ticket)
        resp = self.svc.shadow_assemble(
            self.client,
            "r4",
            force=True,
            include_tickets=True,
            include_presentation=True,
            presentation=pres,
            ticket=custom_ticket,
        )
        self.assertEqual(resp["ticket"]["template_id"], "custom_shadow")
        self.assertEqual(resp["ticket"]["legs"], custom_before["legs"])
        self.assertEqual(custom_ticket, custom_before)

    def test_shadow_full_stack(self):
        resp = build_single_response(
            self.client,
            "r4",
            force=True,
            include_tickets=True,
            include_presentation=True,
        )
        self.assertEqual(resp["single_response_schema"], "single-response/v1")
        self.assertIsNotNone(resp["presentation"])
        self.assertIsNotNone(resp["ticket"])
        self.assertIsNone(resp["natural_explanation"])
        self.assertIsNone(resp["decision_reason"])
        self.assertEqual(
            resp["ticket"]["policy_id"], resp["registry"]["policy_id"]
        )
        # Semantic fields unchanged in store
        store = self.client._store["r4"]
        self.assertEqual(store["world_id"], "rank7_world")
        self.assertEqual(store["prediction"]["ranks"][0], "A")
        self.assertEqual(store["affinity"]["rank7_world"], 0.9)

    def test_fingerprint_stable(self):
        fp0 = fingerprint_payload(self.stored)
        resp = build_single_response(
            self.client, "r4", force=True, include_tickets=True, include_presentation=True
        )
        self.assertEqual(resp["core_ref"]["payload_fingerprint"], fp0)
        self.assertEqual(fingerprint_payload(resp["core_payload"]), fp0)


if __name__ == "__main__":
    unittest.main()
