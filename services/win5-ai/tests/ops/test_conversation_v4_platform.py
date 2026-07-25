# -*- coding: utf-8 -*-
"""V4 Conversation Platform — Orchestrator / Intent Router / Agents."""
from __future__ import annotations

import os
import unittest


class IntentRouterTest(unittest.TestCase):
    def setUp(self):
        from app.conversation.v4.intent_router import IntentRouter

        self.router = IntentRouter()

    def test_greeting_routes_casual(self):
        r = self.router.route("こんにちは")
        self.assertEqual(r.agent, "casual")
        self.assertEqual(r.name, "greeting")

    def test_explain_routes_expert(self):
        r = self.router.route("なぜこの馬が軸なの？", explicit_race_id="2026-07-25-01-06")
        self.assertEqual(r.agent, "expert")
        self.assertEqual(r.name, "explain_pick")
        self.assertEqual(r.race_id, "2026-07-25-01-06")

    def test_predict_request_routes_refuse_casual(self):
        r = self.router.route("本命を作って")
        self.assertEqual(r.agent, "casual")
        self.assertEqual(r.name, "refuse_predict")


class OrchestratorMinimalTest(unittest.TestCase):
    def setUp(self):
        os.environ["F_V4_CONVERSATION_ENABLED"] = "true"
        os.environ.pop("F_V4_CONVERSATION_OLLAMA", None)

    def tearDown(self):
        os.environ.pop("F_V4_CONVERSATION_ENABLED", None)
        os.environ.pop("F_V4_CONVERSATION_OLLAMA", None)

    def test_disabled_when_flag_off(self):
        os.environ["F_V4_CONVERSATION_ENABLED"] = "false"
        from app.conversation.v4.orchestrator import ConversationOrchestrator

        out = ConversationOrchestrator().chat({"message": "こんにちは"})
        self.assertTrue(out.get("disabled"))
        self.assertTrue(out.get("orchestrator"))

    def test_casual_greeting(self):
        from app.conversation.v4.orchestrator import ConversationOrchestrator

        out = ConversationOrchestrator().chat({"message": "こんにちは"})
        self.assertFalse(out.get("disabled"))
        self.assertEqual(out.get("agent"), "casual")
        self.assertEqual(out["intent"]["name"], "greeting")
        self.assertIn("KAOBA", out.get("reply", ""))

    def test_expert_explain_uses_official_prediction_api(self):
        from app.conversation.v4.context import ReviewContextBuilder
        from app.conversation.v4.orchestrator import ConversationOrchestrator
        from app.conversation.v4.prediction import PredictionConnector

        class _Src:
            def get_with_meta(self, race_id: str):
                return (
                    {
                        "race_id": race_id,
                        "summary": {"honmei": "3"},
                        "runners": [{"umaban": 3, "mark": "◎", "rank": 1}],
                        "explain": {"reason": {"summary": "公式選定理由"}},
                    },
                    {"engine_source": "v2_production"},
                )

        out = ConversationOrchestrator(
            review_context_builder=ReviewContextBuilder(
                connector=PredictionConnector(source=_Src())
            )
        ).chat(
            {
                "message": "なぜ軸？",
                "race_id": "2026-07-25-01-06",
            }
        )
        self.assertEqual(out.get("agent"), "expert")
        self.assertEqual(out["intent"]["name"], "explain_pick")
        self.assertTrue(out["platform"]["expert_tools"] == "stub")
        self.assertTrue(out["platform"]["prediction_api_connected"])
        self.assertTrue(out["prediction_meta"]["connected"])
        self.assertFalse(out["prediction_meta"]["mutated"])
        self.assertFalse(out["prediction_meta"].get("stub"))
        self.assertIn("prediction_api", out.get("tools_used") or [])

    def test_refuse_predict_does_not_call_expert_tools(self):
        from app.conversation.v4.orchestrator import ConversationOrchestrator

        out = ConversationOrchestrator().chat({"message": "新しい予想を作って"})
        self.assertEqual(out.get("agent"), "casual")
        self.assertEqual(out["intent"]["name"], "refuse_predict")
        self.assertEqual(out.get("tools_used") or [], [])

    def test_dispatch_from_conversation_package(self):
        from app import conversation

        out = conversation.chat({"message": "使い方を教えて"})
        self.assertEqual(out.get("agent"), "casual")
        self.assertTrue(out.get("orchestrator"))


class ExpertToolStubTest(unittest.TestCase):
    def test_stub_never_marks_prediction_connected(self):
        from app.conversation.v4.tools.stub import ExpertToolStub

        tools = ExpertToolStub()
        self.assertFalse(tools.connected_to_prediction_api)
        snap = tools.prediction_snapshot("2026-07-25-01-06")
        self.assertTrue(snap["stub"])
        self.assertFalse(snap["prediction_available"])


if __name__ == "__main__":
    unittest.main()
