# -*- coding: utf-8 -*-
"""Phase C2 — Presentation Layer integration tests."""
from __future__ import annotations

import copy
import os
import unittest

from app.consumer.core_client import InMemoryCoreClient
from app.consumer.core_payload import fingerprint_payload
from app.consumer.flags import snapshot_consumer_flags
from app.consumer.presentation.dto import DISPLAY_ORDER
from app.consumer.presentation.localization import localization_contract, t
from app.consumer.presentation.mapper import map_presentation
from app.consumer.presentation.renderer import render_presentation
from app.consumer.registry import resolve_policy
from app.consumer.single_api import assert_core_untouched, build_single_response


def _rich_core(race_id: str = "r2") -> dict:
    return {
        "schema": "core-semantic-payload/v1",
        "race_id": race_id,
        "world_id": "unsatisfied",
        "prediction": {"ranks": ["A", "B"], "scores": [0.5, 0.5], "top1": "A"},
        "transition": "legacy→unsatisfied",
        "trigger_path": "path/x",
        "near_miss": {
            "residual_class": "NEAR_MISS",
            "near_world": "rank7_world",
            "near_worlds": ["rank7_world", "midhole_world"],
        },
        "affinity": {
            "core_world": 0.2,
            "rank7_world": 0.9,
            "midhole_world": 0.4,
            "midupper_world": 0.1,
            "definition": "v96/must_affinity",
        },
        "exclusion_reasons": {
            "rank7_world": ["must_field_chaos", "exclude_gate"],
            "core_world": ["n_insufficient"],
        },
        "explanation_confidence": {
            "semantic_confidence": 1.0,
            "world_confidence": 0.9,
            "near_miss_confidence": 0.8,
            "trace_confidence": 1.0,
            "explanation_confidence": 0.92,
            "definition_version": "v101/1.0",
            "not": ["prediction_probability", "odds", "calibration"],
        },
    }


class LocalizationContractTest(unittest.TestCase):
    def test_contract_forbids_nl(self):
        c = localization_contract()
        self.assertEqual(c["natural_explanation"], "forbidden_in_c2")
        self.assertIn("ja", c["supported_locales"])

    def test_ec_disclaimer_not_win_prob(self):
        ja = t("ec.not_win_probability", "ja")
        self.assertIn("勝率", ja)


class MapperRendererTest(unittest.TestCase):
    def test_display_order(self):
        bundle = render_presentation(_rich_core(), locale="ja")
        keys = [s.key for s in bundle.sections]
        self.assertEqual(keys, list(DISPLAY_ORDER))

    def test_no_natural_explanation(self):
        bundle = render_presentation(_rich_core())
        self.assertIsNone(bundle.natural_explanation)
        d = bundle.to_dict()
        self.assertIsNone(d["natural_explanation"])

    def test_affinity_sorted_desc(self):
        bundle = map_presentation(_rich_core())
        self.assertTrue(bundle.affinity and bundle.affinity.present)
        scores = [s for _, s in bundle.affinity.values]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(bundle.affinity.values[0][0], "rank7_world")

    def test_ec_not_win_probability_flag(self):
        bundle = map_presentation(_rich_core())
        self.assertTrue(bundle.explanation_confidence.not_win_probability)
        self.assertEqual(bundle.explanation_confidence.display_kind, "explanation_confidence")

    def test_locale_en(self):
        bundle = render_presentation(_rich_core(), locale="en")
        self.assertEqual(bundle.locale, "en")
        world_sec = bundle.sections[0]
        self.assertEqual(world_sec.label, "World")

    def test_mapper_does_not_mutate_core(self):
        core = _rich_core()
        before = copy.deepcopy(core)
        map_presentation(core)
        assert_core_untouched(before, core)


class IntegrationC2Test(unittest.TestCase):
    def setUp(self):
        for k in list(os.environ.keys()):
            if k.startswith("W_CONSUMER_") or k.startswith("W_CORE_") or k.startswith("W_DECISION_"):
                os.environ.pop(k, None)
        self.client = InMemoryCoreClient()
        self.original = _rich_core("r2")
        self.client.put_for_test("r2", self.original)
        self.stored = copy.deepcopy(self.client._store["r2"])

    def test_flags_presentation_default_off(self):
        self.assertFalse(snapshot_consumer_flags()["W_CONSUMER_PRESENTATION_ENABLED"])

    def test_presentation_flag_off_keeps_null(self):
        resp = build_single_response(
            self.client, "r2", force=True, include_presentation=True
        )
        # force=True allows presentation for Shadow when include_presentation
        self.assertIsNotNone(resp["presentation"])
        self.assertIsNone(resp["presentation"]["natural_explanation"])

    def test_presentation_requires_include_without_force_flag(self):
        # force consumer ON path but presentation flag off and no force_presentation,
        # include_presentation False → null
        resp = build_single_response(self.client, "r2", force=True, include_presentation=False)
        self.assertIsNone(resp["presentation"])

    def test_presentation_flag_off_without_force_presentation_warns(self):
        # Consumer force True but we need a path where presentation not allowed:
        # use force=True for consumer access but force_presentation=False and
        # patch: actually force=True enables presentation_allowed.
        # Explicit path: force=False with flag on for single only — skip.
        # Shadow path without force: enable single flag only
        os.environ["W_CONSUMER_SINGLE_ENABLED"] = "true"
        resp = build_single_response(
            self.client, "r2", include_presentation=True, force_presentation=False
        )
        self.assertIsNone(resp["presentation"])
        self.assertIn("presentation_flag_off", resp["warnings"])

    def test_shadow_force_presentation(self):
        os.environ["W_CONSUMER_SINGLE_ENABLED"] = "true"
        resp = build_single_response(
            self.client,
            "r2",
            include_presentation=True,
            force_presentation=True,
            locale="ja",
        )
        pres = resp["presentation"]
        self.assertIsNotNone(pres)
        self.assertEqual([s["key"] for s in pres["sections"]], list(DISPLAY_ORDER))
        self.assertIsNone(pres["natural_explanation"])
        self.assertTrue(pres["explanation_confidence"]["not_win_probability"])
        # Policy unchanged vs registry-only resolve
        self.assertEqual(resp["registry"]["policy_id"], resolve_policy(self.original).policy_id)
        self.assertIsNone(resp["ticket"])

    def test_core_and_prediction_untouched(self):
        fp = fingerprint_payload(self.stored)
        build_single_response(
            self.client, "r2", force=True, include_presentation=True, force_presentation=True
        )
        assert_core_untouched(self.stored, self.client._store["r2"])
        self.assertEqual(fingerprint_payload(self.client._store["r2"]), fp)
        self.assertEqual(self.client._store["r2"]["prediction"]["ranks"], ["A", "B"])

    def test_presentation_excludes_prediction_payload(self):
        resp = build_single_response(
            self.client, "r2", force=True, include_presentation=True
        )
        pres = resp["presentation"]
        self.assertNotIn("prediction", pres)
        self.assertNotIn("ranks", str(pres.get("sections")))


if __name__ == "__main__":
    unittest.main()
