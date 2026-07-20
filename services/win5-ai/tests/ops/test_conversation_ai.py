# -*- coding: utf-8 -*-
"""Conversation AI unit tests."""
from __future__ import annotations

import unittest

from tests.ops.helpers import http_json, isolated_env, running_server


class IntentClassifierTest(unittest.TestCase):
    def test_coverage_intent(self):
        from app.conversation.intent import IntentClassifier

        intent, conf, _ = IntentClassifier().classify("カバレッジを教えて", has_race=False)
        self.assertEqual(intent, "coverage_inquiry")
        self.assertGreater(conf, 0.8)

    def test_diagnostics_intent(self):
        from app.conversation.intent import IntentClassifier

        intent, _, _ = IntentClassifier().classify("不足データは？", has_race=False)
        self.assertEqual(intent, "diagnostics_inquiry")

    def test_greeting(self):
        from app.conversation.intent import IntentClassifier

        intent, _, _ = IntentClassifier().classify("こんにちは", has_race=False)
        self.assertEqual(intent, "greeting")


class ContextManagerTest(unittest.TestCase):
    def test_follow_up_uses_active_race(self):
        with isolated_env():
            from app.conversation.context import ContextManager, ConversationContext
            from app.conversation.service import ConversationService
            from app.data.db import migrate

            migrate()
            svc = ConversationService()
            r1 = svc.chat({"message": "20260719_hanshin_11を予想して", "session_id": "s1"})
            self.assertEqual(r1["intent"]["name"], "predict_race")
            sid = r1["session_id"]

            r2 = svc.chat({"message": "このレースの理由は？", "session_id": sid})
            self.assertIn(r2["intent"]["name"], ("explain_pick", "follow_up", "predict_race"))
            self.assertIsNotNone(r2.get("race_id"))


class ConversationToolsTest(unittest.TestCase):
    def test_coverage_tool(self):
        with isolated_env():
            from app.conversation.tools import ConversationTools

            data = ConversationTools().execute("coverage_inquiry")
            self.assertIn("coverage", data)
            self.assertIn("coverage", data["sources"])


class ConversationE2ETest(unittest.TestCase):
    def test_coverage_via_chat(self):
        with running_server() as base:
            status, body = http_json(
                f"{base}/v1/conversation/chat",
                method="POST",
                body={"message": "カバレッジを教えて"},
            )
            self.assertEqual(status, 200)
            data = body.get("data") or {}
            self.assertEqual(data.get("intent", {}).get("name"), "coverage_inquiry")
            self.assertIn("カバレッジ", data.get("reply", ""))

    def test_diagnostics_via_chat(self):
        with running_server() as base:
            status, body = http_json(
                f"{base}/v1/conversation/chat",
                method="POST",
                body={"message": "不足データを診断して"},
            )
            self.assertEqual(status, 200)
            data = body.get("data") or {}
            self.assertEqual(data.get("intent", {}).get("name"), "diagnostics_inquiry")

    def test_multi_turn_session(self):
        with running_server() as base:
            s1, b1 = http_json(
                f"{base}/v1/conversation/chat",
                method="POST",
                body={"message": "20260719_hanshin_11を予想して"},
            )
            self.assertEqual(s1, 200)
            sid = b1["data"]["session_id"]

            s2, b2 = http_json(
                f"{base}/v1/conversation/chat",
                method="POST",
                body={"message": "穴馬は？", "session_id": sid},
            )
            self.assertEqual(s2, 200)
            d2 = b2["data"]
            self.assertGreaterEqual(d2.get("turn", 0), 2)
            self.assertEqual(d2.get("intent", {}).get("name"), "find_upset")


if __name__ == "__main__":
    unittest.main()
