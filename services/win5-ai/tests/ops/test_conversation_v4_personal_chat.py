# -*- coding: utf-8 -*-
"""V4 Personal Chat Agent tests."""
from __future__ import annotations

import os
import unittest


class PersonalChatRouterTest(unittest.TestCase):
    def test_mode_chat_routes_chat_only(self):
        from app.conversation.v4.intent_router import IntentRouter

        r = IntentRouter().route("なぜ本命？", mode="chat")
        self.assertEqual(r.name, "chat")
        self.assertEqual(r.agent, "chat")
        self.assertEqual(r.mode, "chat")
        self.assertIsNone(r.race_id)

    def test_keyword_chat(self):
        from app.conversation.v4.intent_router import IntentRouter

        r = IntentRouter().route("ちょっと雑談しよう")
        self.assertEqual(r.name, "chat")
        self.assertEqual(r.agent, "chat")

    def test_review_not_hijacked_without_chat(self):
        from app.conversation.v4.intent_router import IntentRouter

        r = IntentRouter().route("この予想どう思う？", mode="review")
        self.assertEqual(r.agent, "review")


class PersonalChatAgentTest(unittest.TestCase):
    def setUp(self):
        os.environ["F_V4_CONVERSATION_ENABLED"] = "true"
        os.environ["F_V4_PERSONAL_CHAT"] = "true"
        os.environ.pop("F_V4_CONVERSATION_OLLAMA", None)

    def tearDown(self):
        for k in (
            "F_V4_CONVERSATION_ENABLED",
            "F_V4_PERSONAL_CHAT",
            "F_V4_CONVERSATION_OLLAMA",
        ):
            os.environ.pop(k, None)

    def test_flag_default_off(self):
        os.environ.pop("F_V4_PERSONAL_CHAT", None)
        from importlib import reload
        import app.conversation.v4.flags as flags

        reload(flags)
        self.assertFalse(flags.personal_chat_enabled())

    def test_chat_agent_independent(self):
        from app.conversation.v4.orchestrator import ConversationOrchestrator

        out = ConversationOrchestrator().chat(
            {"message": "今日元気？", "mode": "chat"}
        )
        self.assertEqual(out.get("agent"), "chat")
        self.assertEqual(out.get("mode"), "chat")
        self.assertEqual(out["intent"]["name"], "chat")
        self.assertTrue(out.get("kaoba_independent"))
        self.assertFalse(out.get("involves_prediction"))
        self.assertFalse(out.get("involves_review"))
        self.assertFalse(out.get("involves_explain"))
        self.assertIsNone(out.get("prediction_meta"))

    def test_flag_off_message(self):
        os.environ["F_V4_PERSONAL_CHAT"] = "false"
        from app.conversation.v4.agents.chat import ChatAgent

        out = ChatAgent().chat("こんにちは")
        self.assertEqual(out.get("fallback"), "flag_off")
        self.assertIn("オフ", out.get("reply", ""))

    def test_chat_prompt_separated(self):
        from app.conversation.v4.prompts import PromptBuilder

        p = PromptBuilder().build_chat(message="ひま")
        self.assertEqual(p["kind"], "chat")
        self.assertIn("KAOBA", p["system"])
        self.assertIn("別", p["system"])
        self.assertIn("予想", p["user"])

    def test_mode_contract(self):
        from app.conversation.v4.modes import UI_MODE_TRIGGERS, resolve_mode_from_body

        self.assertEqual(UI_MODE_TRIGGERS["chat"]["intent"], "chat")
        self.assertTrue(UI_MODE_TRIGGERS["chat"]["kaoba_independent"])
        self.assertEqual(
            resolve_mode_from_body({"mode": "personal_chat"}), "chat"
        )


if __name__ == "__main__":
    unittest.main()
