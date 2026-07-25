# -*- coding: utf-8 -*-
"""V4 Phase 9 — Knowledge Layer（RAG Foundation · Stub）。"""
from __future__ import annotations

import os
import unittest


class KnowledgeSourceProviderTest(unittest.TestCase):
    def test_source_is_shared_only(self):
        from app.conversation.v4.knowledge import StubKnowledgeSource

        src = StubKnowledgeSource()
        meta = src.meta()
        self.assertTrue(meta["stub"])
        self.assertFalse(meta["vector_db"])
        self.assertFalse(meta["embedding"])
        self.assertFalse(meta["external_api"])
        self.assertFalse(meta["user_private"])
        self.assertFalse(meta["prediction_rationale"])
        cats = {d.category for d in src.list_documents()}
        self.assertTrue(cats.issubset({"faq", "help", "service", "glossary", "general_keiba"}))

    def test_provider_keyword_search_stub(self):
        from app.conversation.v4.knowledge import StubKnowledgeProvider

        out = StubKnowledgeProvider().search("本命")
        self.assertTrue(out["stub"])
        self.assertTrue(out.get("via_retriever"))
        self.assertFalse(out["vector_db"])
        self.assertGreaterEqual(out["hit_count"], 1)
        titles = [h["document"]["title"] for h in out["hits"]]
        self.assertTrue(any("本命" in t for t in titles))


class KnowledgeToolViaManagerTest(unittest.TestCase):
    def setUp(self):
        os.environ["F_V4_KNOWLEDGE_LAYER"] = "true"

    def tearDown(self):
        os.environ.pop("F_V4_KNOWLEDGE_LAYER", None)

    def test_manager_search_knowledge(self):
        from app.conversation.v4.tools import ToolManager, select_tool_names

        mgr = ToolManager()
        self.assertTrue(mgr.has_tool("knowledge"))
        self.assertTrue(any(c["name"] == "knowledge" for c in mgr.capabilities()))
        selected = select_tool_names(mode="default", intent="app_guide")
        self.assertIn("knowledge", selected)

        result = mgr.search_knowledge("KAOBA")
        self.assertTrue(result.ok)
        self.assertEqual(result.tool, "knowledge")
        self.assertTrue(result.data.get("enabled"))
        self.assertFalse(result.data.get("user_private"))
        self.assertFalse(result.data.get("prediction_rationale"))
        self.assertGreaterEqual(result.data.get("hit_count") or 0, 1)

    def test_agent_must_not_need_direct_provider(self):
        """Provider は Tool 経由のみ。Manager.call で到達できること。"""
        from app.conversation.v4.tools import ToolManager

        direct = ToolManager().call("knowledge", query="オッズ", category="glossary")
        self.assertTrue(direct.ok)
        self.assertEqual(direct.data.get("via"), "knowledge_tool")


class KnowledgeFlagTest(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("F_V4_KNOWLEDGE_LAYER", None)

    def test_flag_default_off(self):
        os.environ.pop("F_V4_KNOWLEDGE_LAYER", None)
        from importlib import reload
        import app.conversation.v4.flags as flags

        reload(flags)
        self.assertFalse(flags.knowledge_layer_enabled())

    def test_disabled_when_flag_off(self):
        os.environ["F_V4_KNOWLEDGE_LAYER"] = "false"
        from app.conversation.v4.tools import ToolManager

        result = ToolManager().search_knowledge("ヘルプ")
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "knowledge_layer_disabled")


if __name__ == "__main__":
    unittest.main()
