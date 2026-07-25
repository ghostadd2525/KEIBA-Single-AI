# -*- coding: utf-8 -*-
"""V4 Phase 8 — Tool Layer（Tool Manager + Capability）。"""
from __future__ import annotations

import os
import unittest
from typing import Any


class _FakePredictionSource:
    def __init__(self, bundle: dict[str, Any] | None):
        self.bundle = bundle
        self.calls: list[str] = []

    def get_with_meta(self, race_id: str):
        self.calls.append(race_id)
        if self.bundle is None:
            return None, {"error": "not_found"}
        return dict(self.bundle), {"engine_source": "v2_production"}


def _sample_bundle(race_id: str = "2026-07-25-01-06") -> dict[str, Any]:
    return {
        "race_id": race_id,
        "summary": {"honmei": "3", "confidence": 0.7},
        "runners": [{"umaban": 3, "name": "テスト馬", "mark": "◎", "rank": 1}],
        "explain": {"reason": {"summary": "公式選定"}},
    }


class CapabilityTest(unittest.TestCase):
    def test_catalog_has_four_tools(self):
        from app.conversation.v4.tools import capability_catalog

        names = {c["name"] for c in capability_catalog()}
        self.assertEqual(
            names,
            {"prediction", "race_info", "statistics", "help", "knowledge"},
        )

    def test_select_prefers_prediction_for_review(self):
        from app.conversation.v4.tools import select_tool_names

        names = select_tool_names(mode="review", intent="review_prediction")
        self.assertEqual(names[0], "prediction")


class ToolManagerTest(unittest.TestCase):
    def test_only_manager_entry_prediction_read_only(self):
        from app.conversation.v4.prediction import PredictionConnector
        from app.conversation.v4.tools import PredictionTool, ToolManager

        src = _FakePredictionSource(_sample_bundle())
        mgr = ToolManager(
            prediction_tool=PredictionTool(
                connector=PredictionConnector(source=src)
            )
        )
        caps = mgr.capabilities()
        self.assertTrue(any(c["name"] == "prediction" for c in caps))
        selected = mgr.select(mode="explain", intent="explain_pick")
        self.assertIn("prediction", selected)

        result = mgr.call("prediction", race_id="2026-07-25-01-06")
        self.assertTrue(result.ok)
        self.assertFalse(result.mutated)
        self.assertTrue(result.read_only)
        official, meta = mgr.get_official_prediction("2026-07-25-01-06")
        self.assertIsNotNone(official)
        assert official is not None
        self.assertEqual(official["summary"]["honmei"], "3")
        self.assertFalse(meta["mutated"])
        self.assertTrue(meta["tool_layer"])
        self.assertEqual(meta["via"], "tool_manager")
        self.assertEqual(src.calls, ["2026-07-25-01-06", "2026-07-25-01-06"])

    def test_stub_tools_not_connected(self):
        from app.conversation.v4.tools import ToolManager

        mgr = ToolManager()
        race = mgr.call("race_info", race_id="r1")
        stats = mgr.call("statistics", race_id="r1")
        help_r = mgr.call("help", query="使い方")
        self.assertTrue(race.stub and race.data.get("connected") is False)
        self.assertTrue(stats.stub and stats.data.get("connected") is False)
        self.assertTrue(help_r.stub)
        self.assertIn("faq", help_r.data)


class ToolLayerFlagTest(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("F_V4_TOOL_LAYER", None)

    def test_flag_default_off(self):
        os.environ.pop("F_V4_TOOL_LAYER", None)
        from importlib import reload
        import app.conversation.v4.flags as flags

        reload(flags)
        self.assertFalse(flags.tool_layer_enabled())


class BuilderViaToolManagerTest(unittest.TestCase):
    def setUp(self):
        os.environ["F_V4_TOOL_LAYER"] = "true"
        os.environ["F_V4_CONVERSATION_ENABLED"] = "true"
        os.environ["F_V4_REVIEW_AGENT"] = "true"
        os.environ.pop("F_V4_CONVERSATION_OLLAMA", None)

    def tearDown(self):
        for k in (
            "F_V4_TOOL_LAYER",
            "F_V4_CONVERSATION_ENABLED",
            "F_V4_REVIEW_AGENT",
            "F_V4_CONVERSATION_OLLAMA",
        ):
            os.environ.pop(k, None)

    def test_builder_uses_tool_manager_not_payload(self):
        from app.conversation.v4.context import ReviewContextBuilder
        from app.conversation.v4.intent_router import RoutedIntent
        from app.conversation.v4.prediction import PredictionConnector
        from app.conversation.v4.tools import PredictionTool, ToolManager

        src = _FakePredictionSource(_sample_bundle())
        mgr = ToolManager(
            prediction_tool=PredictionTool(
                connector=PredictionConnector(source=src)
            )
        )
        ctx = ReviewContextBuilder(
            connector=PredictionConnector(source=src),
            tool_manager=mgr,
        ).build(
            {
                "message": "相談",
                "prediction": {"summary": {"honmei": "99"}},
            },
            RoutedIntent(
                name="review_prediction",
                agent="review",
                confidence=0.9,
                race_id="2026-07-25-01-06",
                mode="review",
            ),
        )
        self.assertIsNotNone(ctx.prediction)
        assert ctx.prediction is not None
        self.assertEqual(ctx.prediction["summary"]["honmei"], "3")
        self.assertTrue(ctx.prediction_meta.get("tool_layer"))
        self.assertEqual(ctx.prediction_meta.get("via"), "tool_manager")
        self.assertFalse(ctx.prediction_meta.get("mutated"))
        self.assertIn("prediction", ctx.request.get("slots", {}).get("tools_used", []))

    def test_review_explain_via_orchestrator_tool_manager(self):
        from app.conversation.v4.context import ReviewContextBuilder
        from app.conversation.v4.orchestrator import ConversationOrchestrator
        from app.conversation.v4.prediction import PredictionConnector
        from app.conversation.v4.tools import PredictionTool, ToolManager

        src = _FakePredictionSource(_sample_bundle())
        mgr = ToolManager(
            prediction_tool=PredictionTool(
                connector=PredictionConnector(source=src)
            )
        )
        builder = ReviewContextBuilder(
            connector=PredictionConnector(source=src),
            tool_manager=mgr,
        )
        orch = ConversationOrchestrator(review_context_builder=builder)

        review = orch.chat(
            {
                "message": "この予想どう思う？",
                "mode": "review",
                "race_id": "2026-07-25-01-06",
            }
        )
        self.assertEqual(review.get("agent"), "review")
        self.assertTrue(review["platform"]["tool_layer"])
        self.assertEqual(review["prediction_meta"].get("via"), "tool_manager")
        self.assertFalse(review["prediction_meta"]["mutated"])
        self.assertTrue(review["prediction_meta"]["used"])

        explain = orch.chat(
            {
                "message": "なぜ軸？",
                "mode": "explain",
                "race_id": "2026-07-25-01-06",
            }
        )
        self.assertEqual(explain.get("agent"), "expert")
        self.assertEqual(explain.get("mode"), "explain")
        self.assertTrue(explain["prediction_meta"].get("tool_layer"))
        self.assertEqual(explain["prediction_meta"].get("via"), "tool_manager")
        self.assertFalse(explain["prediction_meta"]["mutated"])

    def test_review_agent_unchanged_signature(self):
        import inspect

        from app.conversation.v4.agents.review import ReviewAgent

        self.assertEqual(list(inspect.signature(ReviewAgent().review).parameters.keys()), ["context"])


if __name__ == "__main__":
    unittest.main()
