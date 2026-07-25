# -*- coding: utf-8 -*-
"""V6 Phase 1 — formal Knowledge Contents via Source (Platform unchanged)."""
from __future__ import annotations

import os
import unittest


class FormalKnowledgeSourceTest(unittest.TestCase):
    def test_formal_catalog_loaded(self):
        from app.conversation.v4.knowledge.source import StubKnowledgeSource

        src = StubKnowledgeSource()
        meta = src.meta()
        self.assertTrue(meta["formal"])
        self.assertEqual(meta["content_phase"], "v6-phase1")
        self.assertGreaterEqual(meta["document_count"], 20)
        self.assertEqual(
            set(meta["categories"]),
            {"faq", "help", "service", "glossary", "general_keiba"},
        )

    def test_category_tag_keyword_search(self):
        from app.conversation.v4.knowledge.source import StubKnowledgeSource

        src = StubKnowledgeSource()
        by_cat = src.search_by_category("faq")
        self.assertGreaterEqual(len(by_cat), 1)
        self.assertTrue(all(d.category == "faq" for d in by_cat))

        by_tag = src.search_by_tag("kaoba")
        self.assertGreaterEqual(len(by_tag), 1)

        by_kw = src.search_by_keyword("本命")
        self.assertGreaterEqual(len(by_kw), 1)
        self.assertTrue(any("本命" in d.title or "本命" in d.body for d in by_kw))

        combo = src.search("自信度", category="glossary", limit=5)
        self.assertGreaterEqual(len(combo), 1)

    def test_runtime_uses_formal_content(self):
        os.environ["F_V5_KNOWLEDGE_RUNTIME"] = "ON"
        os.environ["F_V4_KNOWLEDGE_LAYER"] = "ON"
        try:
            from app.conversation.v5.knowledge import KnowledgeRuntime
            from app.conversation.v4.knowledge import KnowledgeProvider
            from app.conversation.v4.tools import ToolManager

            rt = KnowledgeRuntime()
            out = rt.search("KAOBA")
            self.assertGreaterEqual(out["hit_count"], 1)
            self.assertTrue((out.get("source_meta") or {}).get("formal"))

            # keyword + category via Provider (Runtime path)
            prov = KnowledgeProvider()
            out2 = prov.search("本命", category="glossary")
            self.assertGreaterEqual(out2["hit_count"], 1)
            self.assertTrue(out2.get("knowledge_runtime") or out2.get("via_retriever"))

            # Tool path (Manager unchanged)
            tool = ToolManager().search_knowledge("日常会話", category="help")
            self.assertTrue(tool.ok)
            self.assertGreaterEqual(tool.data.get("hit_count") or 0, 1)
        finally:
            os.environ.pop("F_V5_KNOWLEDGE_RUNTIME", None)
            os.environ.pop("F_V4_KNOWLEDGE_LAYER", None)


if __name__ == "__main__":
    unittest.main()
