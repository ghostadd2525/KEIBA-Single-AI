# -*- coding: utf-8 -*-
"""V6 Phase 2 — Memory Platform（Consent-only · auto-save forbidden）."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


class MemoryConsentOnlyTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        root = Path(self._tmpdir.name)
        from app.conversation.v6.memory.store import reset_memory_store_for_tests
        from app.conversation.v6.memory.manager import reset_memory_manager_for_tests
        from app.conversation.v6.memory.gateway import reset_memory_gateway_for_tests
        from app.conversation.v6.memory.tool import MemoryTool

        self.store = reset_memory_store_for_tests(root)
        self.manager = reset_memory_manager_for_tests(self.store)
        reset_memory_gateway_for_tests(MemoryTool(self.manager))
        os.environ["F_V6_MEMORY"] = "ON"
        os.environ.pop("F_V4_CONVERSATION_ENABLED", None)

    def tearDown(self) -> None:
        os.environ.pop("F_V6_MEMORY", None)
        os.environ.pop("F_V4_CONVERSATION_ENABLED", None)
        self._tmpdir.cleanup()

    def test_flag_default_off_in_snapshot(self) -> None:
        os.environ.pop("F_V6_MEMORY", None)
        from app.conversation.v4.flags import flag_snapshot, memory_enabled

        self.assertFalse(memory_enabled())
        self.assertFalse(flag_snapshot()["F_V6_MEMORY"])

    def test_without_consent_does_not_save(self) -> None:
        """停止条件: 「覚えて」無しでは保存されない（自動保存禁止）。"""
        out = self.manager.remember("u1", "ニックネームは太郎です")
        self.assertFalse(out["saved"])
        self.assertEqual(out["reason"], "consent_required")
        self.assertEqual(self.store.list("u1"), [])

    def test_with_consent_saves(self) -> None:
        out = self.manager.remember("u1", "ニックネームは太郎って覚えて")
        self.assertTrue(out["ok"])
        self.assertTrue(out["saved"])
        records = self.store.list("u1")
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0].consent)
        self.assertEqual(records[0].category, "nickname")
        self.assertIn("太郎", records[0].value)

    def test_forbidden_topic_rejected_even_with_consent(self) -> None:
        out = self.manager.remember("u1", "この予測の自信度を覚えて")
        self.assertFalse(out["saved"])
        self.assertTrue(str(out["reason"]).startswith("forbidden_topic"))
        self.assertEqual(self.store.list("u1"), [])

    def test_list_forget_and_clear(self) -> None:
        self.manager.remember("u1", "好きな競馬場は東京を覚えて")
        self.manager.remember("u1", "好きな騎手は武豊を覚えて")
        listed = self.manager.list_memories("u1")
        self.assertEqual(listed["count"], 2)
        self.assertIn("東京", listed["message"])

        forgotten = self.manager.forget("u1", "東京を忘れて")
        self.assertEqual(forgotten["removed_count"], 1)
        self.assertEqual(len(self.store.list("u1")), 1)

        cleared = self.manager.forget_all("u1")
        self.assertEqual(cleared["removed_count"], 1)
        self.assertEqual(self.store.list("u1"), [])

    def test_gateway_handles_remember_without_history(self) -> None:
        from app.conversation import chat

        res = chat(
            {
                "user_id": "gw-user",
                "message": "説明スタイルは短くを覚えて",
                "mode": "chat",
            }
        )
        self.assertEqual(res.get("agent"), "memory")
        self.assertTrue(res["meta"]["memory_saved"])
        self.assertFalse(res["meta"]["history_touched"])
        self.assertFalse(res["meta"]["auto_save"])
        self.assertEqual(len(self.store.list("gw-user")), 1)

    def test_gateway_ignores_casual_preference_without_consent(self) -> None:
        from app.conversation import chat

        # Memory 操作ではない → gateway は None → V4 OFF なら legacy
        res = chat(
            {
                "user_id": "gw-user2",
                "message": "好きな馬はディープインパクトです",
                "mode": "chat",
            }
        )
        self.assertNotEqual(res.get("agent"), "memory")
        self.assertEqual(self.store.list("gw-user2"), [])

    def test_memory_separated_from_history_store(self) -> None:
        """History と Memory は別ストレージ。"""
        from app.conversation.v4.history.manager import HistoryManager

        self.manager.remember("u-sep", "呼び方はさん付けを覚えて")
        hist = HistoryManager()
        hist.append_user("sess-sep", "呼び方はさん付けを覚えて")
        # History はメモリ FIFO · Memory はファイル
        self.assertEqual(len(hist.snapshot("sess-sep")["messages"]), 1)
        self.assertEqual(len(self.store.list("u-sep")), 1)
        self.assertTrue(self.store.meta()["history_separated"])
        self.assertTrue(self.store.meta()["persistent"])

    def test_tool_not_in_tool_manager(self) -> None:
        from app.conversation.v4.tools import ToolManager
        from app.conversation.v6.memory.tool import MemoryTool

        tm = ToolManager()
        self.assertNotIn("memory", getattr(tm, "tools", {}) or {})
        self.assertFalse(MemoryTool.registered_in_tool_manager)


if __name__ == "__main__":
    unittest.main()
