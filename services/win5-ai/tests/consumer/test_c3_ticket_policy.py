# -*- coding: utf-8 -*-
"""Phase C3 — Ticket Policy Resolver integration tests."""
from __future__ import annotations

import copy
import os
import unittest

from app.consumer.core_client import InMemoryCoreClient
from app.consumer.core_payload import fingerprint_payload
from app.consumer.flags import snapshot_consumer_flags
from app.consumer.registry import resolve_policy
from app.consumer.single_api import assert_core_untouched, build_single_response
from app.consumer.ticket.market import DictMarketResolver
from app.consumer.ticket.resolver import resolve_ticket
from app.consumer.ticket.templates import get_template, template_registry_meta


def _core(world_id: str, ranks: list[str] | None = None) -> dict:
    r = ranks or ["A", "B", "C", "D", "E", "F", "G"]
    return {
        "schema": "core-semantic-payload/v1",
        "race_id": "r3",
        "world_id": world_id,
        "prediction": {"ranks": list(r), "scores": [0.3] * len(r), "top1": r[0]},
        "near_miss": None,
        "affinity": {"core_world": 0.5, "definition": "v96/must_affinity"},
        "explanation_confidence": {"explanation_confidence": 0.9},
        "exclusion_reasons": {},
        "transition": None,
    }


class TemplateRegistryTest(unittest.TestCase):
    def test_meta_no_reasoning(self):
        meta = template_registry_meta()
        self.assertIn("no Reasoning Engine", " ".join(meta["rules"]))

    def test_near_miss_not_rank7_diversify(self):
        nm = get_template("policy_near_miss_rank7_conservative")
        r7 = get_template("policy_rank7_ready")
        self.assertEqual(nm.top_n, 1)
        self.assertGreaterEqual(r7.top_n, 5)
        self.assertNotEqual(nm.template_id, r7.template_id)


class ResolverTest(unittest.TestCase):
    def test_rank7_fills_template(self):
        pred = {"ranks": ["A", "B", "C", "D", "E", "F", "G"], "top1": "A"}
        plan = resolve_ticket("policy_rank7_ready", race_id="r3", prediction=pred)
        self.assertEqual(plan.action, "BUY")
        self.assertEqual(len(plan.legs), 5)
        self.assertEqual(len(plan.pool), 7)
        self.assertIsNone(plan.reason)
        self.assertEqual(plan.legs[0].horse_id, "A")

    def test_blocked_skip(self):
        plan = resolve_ticket(
            "policy_blocked",
            race_id="r3",
            prediction={"ranks": ["A", "B"], "top1": "A"},
        )
        self.assertEqual(plan.action, "SKIP")
        self.assertEqual(plan.legs, ())

    def test_market_resolver_odds(self):
        market = DictMarketResolver(budget=200.0, odds_by_horse={"A": 3.5})
        plan = resolve_ticket(
            "policy_legacy_fallback",
            race_id="r3",
            prediction={"ranks": ["A"], "top1": "A"},
            market=market,
        )
        self.assertEqual(plan.legs[0].odds, 3.5)
        self.assertEqual(plan.budget, 200.0)

    def test_does_not_mutate_prediction(self):
        pred = {"ranks": ["A", "B"], "top1": "A"}
        before = copy.deepcopy(pred)
        resolve_ticket("policy_rank7_ready", race_id="r3", prediction=pred)
        self.assertEqual(pred, before)


class IntegrationC3Test(unittest.TestCase):
    def setUp(self):
        for k in list(os.environ.keys()):
            if k.startswith("W_CONSUMER_") or k.startswith("W_CORE_") or k.startswith("W_DECISION_"):
                os.environ.pop(k, None)
        self.client = InMemoryCoreClient()
        self.original = _core("rank7_world")
        self.client.put_for_test("r3", self.original)
        self.stored = copy.deepcopy(self.client._store["r3"])

    def test_ticket_flag_default_off(self):
        self.assertFalse(snapshot_consumer_flags()["W_CONSUMER_TICKET_ENABLED"])

    def test_ticket_flag_off_warns(self):
        os.environ["W_CONSUMER_SINGLE_ENABLED"] = "true"
        resp = build_single_response(
            self.client, "r3", include_tickets=True, force_ticket=False
        )
        self.assertIsNone(resp["ticket"])
        self.assertIn("ticket_flag_off", resp["warnings"])

    def test_shadow_ticket(self):
        resp = build_single_response(
            self.client,
            "r3",
            force=True,
            include_tickets=True,
            force_ticket=True,
            market=DictMarketResolver(odds_by_horse={"A": 2.0, "B": 5.0}),
        )
        t = resp["ticket"]
        self.assertIsNotNone(t)
        self.assertEqual(t["policy_id"], resp["registry"]["policy_id"])
        self.assertEqual(t["action"], "BUY")
        self.assertEqual(len(t["legs"]), 5)
        self.assertIsNone(t["reason"])
        # Registry policy unchanged
        self.assertEqual(resp["registry"]["policy_id"], resolve_policy(self.original).policy_id)

    def test_near_miss_conservative_not_diversify(self):
        core = _core("unsatisfied")
        core["near_miss"] = {
            "residual_class": "NEAR_MISS",
            "near_world": "rank7_world",
        }
        self.client.put_for_test("r3", core)
        resp = build_single_response(
            self.client, "r3", force=True, include_tickets=True, force_ticket=True
        )
        self.assertEqual(resp["registry"]["policy_id"], "policy_near_miss_rank7_conservative")
        self.assertEqual(len(resp["ticket"]["legs"]), 1)
        self.assertEqual(resp["ticket"]["template_id"], "tpl_near_miss_conservative_top1")

    def test_core_semantic_untouched(self):
        fp = fingerprint_payload(self.stored)
        build_single_response(
            self.client,
            "r3",
            force=True,
            include_tickets=True,
            include_presentation=True,
            force_ticket=True,
        )
        assert_core_untouched(self.stored, self.client._store["r3"])
        self.assertEqual(fingerprint_payload(self.client._store["r3"]), fp)
        # Affinity / EC / world unchanged
        self.assertEqual(self.client._store["r3"]["world_id"], "rank7_world")
        self.assertEqual(self.client._store["r3"]["affinity"]["core_world"], 0.5)

    def test_policy_id_stable_across_ticket(self):
        pid_before = resolve_policy(self.client.get("r3")).policy_id
        resp = build_single_response(
            self.client, "r3", force=True, include_tickets=True, force_ticket=True
        )
        self.assertEqual(pid_before, resp["registry"]["policy_id"])
        self.assertEqual(pid_before, resp["ticket"]["policy_id"])


if __name__ == "__main__":
    unittest.main()
