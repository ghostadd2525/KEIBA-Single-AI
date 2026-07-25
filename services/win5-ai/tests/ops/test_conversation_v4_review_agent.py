# -*- coding: utf-8 -*-
"""V4 Phase 3/4 — Review Agent + Review Context tests."""
from __future__ import annotations

import inspect
import os
import unittest


class ModeAndRouterReviewTest(unittest.TestCase):
    def test_mode_review_routes_review_agent(self):
        from app.conversation.v4.intent_router import IntentRouter

        r = IntentRouter().route("なにか聞いて", mode="review")
        self.assertEqual(r.agent, "review")
        self.assertEqual(r.name, "review_prediction")
        self.assertEqual(r.mode, "review")

    def test_mode_explain_routes_expert(self):
        from app.conversation.v4.intent_router import IntentRouter

        r = IntentRouter().route("教えて", mode="explain")
        self.assertEqual(r.agent, "expert")
        self.assertEqual(r.name, "explain_pick")
        self.assertEqual(r.mode, "explain")

    def test_consult_keyword(self):
        from app.conversation.v4.intent_router import IntentRouter

        r = IntentRouter().route("この予想について相談したい")
        self.assertEqual(r.agent, "review")


class ReviewContextTest(unittest.TestCase):
    def setUp(self):
        os.environ["F_V4_CONVERSATION_ENABLED"] = "true"
        os.environ["F_V4_REVIEW_AGENT"] = "true"
        os.environ.pop("F_V4_CONVERSATION_OLLAMA", None)

    def tearDown(self):
        for k in (
            "F_V4_CONVERSATION_ENABLED",
            "F_V4_REVIEW_AGENT",
            "F_V4_CONVERSATION_OLLAMA",
        ):
            os.environ.pop(k, None)

    def test_builder_fills_required_keys(self):
        from app.conversation.v4.context import ReviewContextBuilder
        from app.conversation.v4.intent_router import RoutedIntent
        from app.conversation.v4.prediction import PredictionConnector

        class _Src:
            def get_with_meta(self, race_id: str):
                return (
                    {
                        "race_id": race_id,
                        "summary": {"honmei": "3"},
                        "runners": [{"umaban": 3, "name": "馬", "mark": "◎", "rank": 1}],
                    },
                    {"engine_source": "v2_production"},
                )

        routed = RoutedIntent(
            name="review_prediction",
            agent="review",
            confidence=0.9,
            race_id="2026-07-25-01-06",
            mode="review",
        )
        ctx = ReviewContextBuilder(
            connector=PredictionConnector(source=_Src())
        ).build(
            {
                "message": "相談",
                "prediction": {
                    "race_id": "2026-07-25-01-06",
                    "prediction_available": True,
                    "summary": {"honmei": "99"},
                },
            },
            routed,
        )
        for key in (
            "mode",
            "prediction",
            "prediction_meta",
            "buy_strategy",
            "race",
            "horse",
            "user",
            "request",
        ):
            self.assertIn(key, ctx.to_dict())
        self.assertFalse(ctx.prediction_meta.get("mutated"))
        self.assertTrue(ctx.prediction_meta.get("connected"))
        self.assertEqual(ctx.prediction["summary"]["honmei"], "3")
        self.assertTrue(ctx.buy_strategy.get("stub"))
        self.assertTrue(ctx.race.get("stub"))
        self.assertTrue(ctx.horse.get("stub"))
        self.assertTrue(ctx.user.get("stub"))

    def test_review_agent_only_accepts_context(self):
        from app.conversation.v4.agents.review import ReviewAgent
        from app.conversation.v4.context import ReviewContext

        agent = ReviewAgent()
        self.assertTrue(hasattr(agent, "review"))
        self.assertFalse(hasattr(agent, "handle"))
        sig = inspect.signature(agent.review)
        params = list(sig.parameters.keys())
        self.assertEqual(params, ["context"])
        with self.assertRaises(TypeError):
            agent.review({"prediction": {}})  # type: ignore[arg-type]
        out = agent.review(ReviewContext(mode="review", request={"message": "相談"}))
        self.assertEqual(out.get("agent"), "review")
        self.assertIn("context_keys", out)

    def test_prompt_builder_review_requires_context(self):
        from app.conversation.v4.context import ReviewContext
        from app.conversation.v4.prompts import PromptBuilder

        b = PromptBuilder()
        with self.assertRaises(TypeError):
            b.build_review(message="x", race_id="r", prediction=None)  # type: ignore[call-arg]
        prompt = b.build_review(
            ReviewContext(
                mode="review",
                prediction={"prediction_available": True, "summary": {"honmei": "1"}},
                prediction_meta={"mutated": False, "used": True},
                request={"message": "相談して"},
            )
        )
        self.assertEqual(prompt["kind"], "review")
        self.assertIn("CONTEXT_JSON", prompt["user"])
        self.assertIn("buy_strategy", prompt["user"])

    def test_orchestrator_review_via_context(self):
        from app.conversation.v4.context import ReviewContextBuilder
        from app.conversation.v4.orchestrator import ConversationOrchestrator
        from app.conversation.v4.prediction import PredictionConnector

        class _Src:
            def get_with_meta(self, race_id: str):
                return (
                    {
                        "race_id": race_id,
                        "prediction_available": True,
                        "engine_source": "v2_production",
                        "summary": {"honmei": "3", "confidence": 0.7},
                        "runners": [
                            {"umaban": 3, "name": "テスト馬", "mark": "◎", "rank": 1}
                        ],
                    },
                    {"engine_source": "v2_production"},
                )

        orch = ConversationOrchestrator(
            review_context_builder=ReviewContextBuilder(
                connector=PredictionConnector(source=_Src())
            )
        )
        out = orch.chat(
            {
                "message": "この予想どう思う？",
                "mode": "review",
                "race_id": "2026-07-25-01-06",
            }
        )
        self.assertEqual(out.get("agent"), "review")
        self.assertFalse(out["prediction_meta"]["mutated"])
        # Review Agent 自体は Prediction API に接続しない（connected=false 固定・変更禁止）
        self.assertFalse(out["prediction_meta"]["connected"])
        self.assertEqual(out["prediction_meta"].get("source"), "prediction_api")
        self.assertTrue(out["prediction_meta"]["used"])
        self.assertEqual(
            set(out.get("context_keys") or []),
            {
                "mode",
                "prediction",
                "prediction_meta",
                "buy_strategy",
                "race",
                "horse",
                "user",
                "request",
                "history",
            },
        )


class ReviewAgentTest(unittest.TestCase):
    def setUp(self):
        os.environ["F_V4_CONVERSATION_ENABLED"] = "true"
        os.environ["F_V4_REVIEW_AGENT"] = "true"
        os.environ.pop("F_V4_CONVERSATION_OLLAMA", None)

    def tearDown(self):
        for k in (
            "F_V4_CONVERSATION_ENABLED",
            "F_V4_REVIEW_AGENT",
            "F_V4_CONVERSATION_OLLAMA",
        ):
            os.environ.pop(k, None)

    def test_review_flag_off_message(self):
        os.environ["F_V4_REVIEW_AGENT"] = "false"
        from app.conversation.v4.agents.review import ReviewAgent
        from app.conversation.v4.context import ReviewContext

        out = ReviewAgent().review(
            ReviewContext(mode="review", request={"message": "相談", "intent_confidence": 0.9})
        )
        self.assertEqual(out.get("fallback"), "flag_off")
        self.assertIn("オフ", out.get("reply", ""))

    def test_review_does_not_mutate_prediction(self):
        from app.conversation.v4.context import ReviewContextBuilder
        from app.conversation.v4.orchestrator import ConversationOrchestrator
        from app.conversation.v4.prediction import PredictionConnector

        class _Src:
            def get_with_meta(self, race_id: str):
                return (
                    {
                        "race_id": race_id,
                        "prediction_available": True,
                        "engine_source": "v2_production",
                        "summary": {"honmei": "3", "confidence": 0.7},
                        "runners": [
                            {"umaban": 3, "name": "テスト馬", "mark": "◎", "rank": 1}
                        ],
                    },
                    {"engine_source": "v2_production"},
                )

        out = ConversationOrchestrator(
            review_context_builder=ReviewContextBuilder(
                connector=PredictionConnector(source=_Src())
            )
        ).chat(
            {
                "message": "この予想どう思う？",
                "mode": "review",
                "race_id": "2026-07-25-01-06",
            }
        )
        self.assertEqual(out.get("agent"), "review")
        self.assertEqual(out.get("mode"), "review")
        self.assertFalse(out["prediction_meta"]["mutated"])
        self.assertNotIn("updated_prediction", out)
        self.assertNotIn("new_marks", out)

    def test_prompt_builder_separates_explain_and_review(self):
        from app.conversation.v4.context import ReviewContext
        from app.conversation.v4.prompts import PromptBuilder

        b = PromptBuilder()
        e = b.build_explain(message="◎の理由", race_id="r1", prediction=None)
        r = b.build_review(ReviewContext(mode="review", request={"message": "相談"}))
        self.assertEqual(e["kind"], "explain")
        self.assertEqual(r["kind"], "review")
        self.assertIn("選定理由", e["user"])
        self.assertIn("レビュー", r["user"])
        self.assertNotEqual(e["system"], r["system"])

    def test_ui_mode_contract(self):
        from app.conversation.v4.modes import UI_MODE_TRIGGERS, resolve_mode_from_body

        self.assertEqual(
            UI_MODE_TRIGGERS["explain"]["label_ja"], "KAOBAに◎の理由を聞く"
        )
        self.assertEqual(UI_MODE_TRIGGERS["review"]["label_ja"], "KAOBAに相談")
        self.assertEqual(
            resolve_mode_from_body({"context": {"type": "consult"}}), "review"
        )
        self.assertEqual(resolve_mode_from_body({"mode": "explain"}), "explain")


class FlagDefaultOffTest(unittest.TestCase):
    def test_review_flag_default_off(self):
        os.environ.pop("F_V4_REVIEW_AGENT", None)
        from importlib import reload
        import app.conversation.v4.flags as flags

        reload(flags)
        self.assertFalse(flags.review_agent_enabled())


if __name__ == "__main__":
    unittest.main()
