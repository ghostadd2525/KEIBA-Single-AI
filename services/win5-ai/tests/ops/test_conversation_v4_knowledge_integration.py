# -*- coding: utf-8 -*-
"""V4 Phase 10 — Knowledge Integration（Retriever / Adapter Interface）。"""
from __future__ import annotations

import os
import unittest


class InterfaceOnlyTest(unittest.TestCase):
    def test_embedding_adapter_unconnected(self):
        from app.conversation.v4.knowledge import UnconnectedEmbeddingAdapter

        ad = UnconnectedEmbeddingAdapter()
        self.assertFalse(ad.connected)
        self.assertTrue(ad.meta()["interface_only"])
        with self.assertRaises(NotImplementedError):
            ad.embed(["hello"])

    def test_vector_store_adapter_unconnected(self):
        from app.conversation.v4.knowledge import UnconnectedVectorStoreAdapter

        ad = UnconnectedVectorStoreAdapter()
        self.assertFalse(ad.connected)
        self.assertTrue(ad.meta()["interface_only"])
        with self.assertRaises(NotImplementedError):
            ad.similarity_search([0.1, 0.2], limit=3)


class RetrieverProviderIntegrationTest(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("F_V4_KNOWLEDGE_INTEGRATION", None)

    def test_provider_uses_retriever_interface_only(self):
        from app.conversation.v4.knowledge import KnowledgeProvider, StubRetriever

        retriever = StubRetriever()
        provider = KnowledgeProvider(retriever=retriever)
        out = provider.search("本命")
        self.assertTrue(out["via_retriever"])
        self.assertTrue(out["retriever_interface"])
        self.assertEqual(out["provider"], "knowledge_provider")
        self.assertFalse(out["vector_db"])
        self.assertFalse(out["embedding"])
        self.assertGreaterEqual(out["hit_count"], 1)
        # Provider は Retriever 以外を持たない検索経路
        self.assertTrue(hasattr(provider, "retriever"))

    def test_integration_flag_wires_adapters_but_not_connected(self):
        os.environ["F_V4_KNOWLEDGE_INTEGRATION"] = "true"
        from app.conversation.v4.knowledge import (
            KnowledgeProvider,
            UnconnectedEmbeddingAdapter,
            UnconnectedVectorStoreAdapter,
            build_default_retriever,
        )

        retriever = build_default_retriever(integration=True)
        self.assertTrue(retriever.integration_wired)
        self.assertIsInstance(retriever.embedding, UnconnectedEmbeddingAdapter)
        self.assertIsInstance(retriever.vector_store, UnconnectedVectorStoreAdapter)
        # runtime では呼ばない
        meta = retriever.meta()
        self.assertFalse(meta["uses_embedding_runtime"])
        self.assertFalse(meta["uses_vector_store_runtime"])
        self.assertFalse(meta["vector_db"])

        provider = KnowledgeProvider(retriever=retriever)
        out = provider.search("ペース")
        self.assertTrue(out["via_retriever"])
        self.assertGreaterEqual(out["hit_count"], 1)

    def test_integration_flag_default_off(self):
        os.environ.pop("F_V4_KNOWLEDGE_INTEGRATION", None)
        from importlib import reload
        import app.conversation.v4.flags as flags

        reload(flags)
        self.assertFalse(flags.knowledge_integration_enabled())

    def test_source_stub_preserved(self):
        from app.conversation.v4.knowledge import StubKnowledgeSource, StubRetriever

        src = StubKnowledgeSource()
        r = StubRetriever(source=src)
        self.assertIs(r.source, src)
        self.assertFalse(src.connected_to_vector_db)


class KnowledgeLayerCompatTest(unittest.TestCase):
    def setUp(self):
        os.environ["F_V4_KNOWLEDGE_LAYER"] = "true"

    def tearDown(self):
        os.environ.pop("F_V4_KNOWLEDGE_LAYER", None)
        os.environ.pop("F_V4_KNOWLEDGE_INTEGRATION", None)

    def test_tool_manager_unchanged_path(self):
        from app.conversation.v4.tools import ToolManager

        result = ToolManager().search_knowledge("KAOBA")
        self.assertTrue(result.ok)
        self.assertTrue(result.data.get("via_retriever"))
        self.assertEqual(result.data.get("via"), "knowledge_tool")


if __name__ == "__main__":
    unittest.main()
