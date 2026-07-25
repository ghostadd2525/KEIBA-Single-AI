# -*- coding: utf-8 -*-
"""V5 Phase 1/2 — Knowledge Runtime tests。"""
from __future__ import annotations

import os
import unittest


class KnowledgeRuntimeTest(unittest.TestCase):
    def test_runtime_searches_via_rag(self):
        from app.conversation.v5.knowledge import KnowledgeRuntime

        rt = KnowledgeRuntime()
        out = rt.search("本命")
        self.assertTrue(out["ok"])
        self.assertEqual(out["phase"], 2)
        self.assertTrue(out["via_rag_runtime"])
        self.assertTrue(out["rag"])
        self.assertTrue(out["embedding_local"])
        self.assertFalse(out["vector_db"])
        self.assertFalse(out["external_api"])
        self.assertGreaterEqual(out["hit_count"], 1)

    def test_keyword_fallback(self):
        from app.conversation.v5.knowledge import KnowledgeRuntime

        out = KnowledgeRuntime().search("KAOBA", force_keyword=True)
        self.assertTrue(out["via_retriever_runtime"])
        self.assertFalse(out["via_rag_runtime"])
        self.assertGreaterEqual(out["hit_count"], 1)

    def test_retriever_runtime_meta(self):
        from app.conversation.v5.knowledge import RetrieverRuntime

        r = RetrieverRuntime()
        meta = r.meta()
        self.assertEqual(meta["runtime"], "v5_retriever_runtime")
        self.assertFalse(meta["embedding"])
        out = r.retrieve("KAOBA")
        self.assertEqual(out["retriever"], "retriever_runtime")
        self.assertGreaterEqual(out["hit_count"], 1)

    def test_embedding_and_vector_store(self):
        from app.conversation.v5.knowledge import (
            EmbeddingRuntime,
            VectorStoreRuntime,
        )

        emb = EmbeddingRuntime(dimensions=32)
        v = emb.embed_one("本命 ◎")
        self.assertEqual(len(v), 32)
        store = VectorStoreRuntime()
        store.upsert(
            doc_id="d1",
            vector=v,
            document={"doc_id": "d1", "title": "本命", "body": "x", "category": "glossary", "tags": []},
            category="glossary",
        )
        hits = store.similarity_search(emb.embed_one("本命"), limit=3)
        self.assertGreaterEqual(len(hits), 1)


class ProviderRuntimeWiringTest(unittest.TestCase):
    def setUp(self):
        os.environ["F_V5_KNOWLEDGE_RUNTIME"] = "true"

    def tearDown(self):
        os.environ.pop("F_V5_KNOWLEDGE_RUNTIME", None)
        os.environ.pop("F_V4_KNOWLEDGE_LAYER", None)

    def test_provider_uses_runtime_when_flag_on(self):
        from app.conversation.v4.knowledge import KnowledgeProvider

        provider = KnowledgeProvider()
        self.assertTrue(provider.runtime_enabled)
        out = provider.search("ペース")
        self.assertTrue(out["knowledge_runtime"])
        self.assertTrue(out.get("via_rag_runtime") or out.get("via_retriever_runtime"))
        self.assertGreaterEqual(out["hit_count"], 1)

    def test_tool_path_provider_runtime(self):
        os.environ["F_V4_KNOWLEDGE_LAYER"] = "true"
        from app.conversation.v4.tools import ToolManager

        result = ToolManager().search_knowledge("オッズ")
        self.assertTrue(result.ok)
        self.assertTrue(result.data.get("knowledge_runtime"))
        self.assertGreaterEqual(result.data.get("hit_count") or 0, 1)

    def test_flag_default_off(self):
        os.environ.pop("F_V5_KNOWLEDGE_RUNTIME", None)
        from importlib import reload
        import app.conversation.v4.flags as flags

        reload(flags)
        self.assertFalse(flags.knowledge_runtime_enabled())
        from app.conversation.v4.knowledge import KnowledgeProvider

        provider = KnowledgeProvider()
        self.assertFalse(provider.runtime_enabled)
        out = provider.search("本命")
        self.assertFalse(out.get("knowledge_runtime"))


if __name__ == "__main__":
    unittest.main()
