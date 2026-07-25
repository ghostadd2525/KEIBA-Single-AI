# -*- coding: utf-8 -*-
"""V4 Phase 7 — Prediction API Integration（Read Only）。"""
from __future__ import annotations

import os
import unittest
from typing import Any


class _FakePredictionSource:
    def __init__(self, bundle: dict[str, Any] | None, meta: dict[str, Any] | None = None):
        self.bundle = bundle
        self.meta = meta or {"engine_source": "v2_production"}
        self.calls: list[str] = []

    def get_with_meta(self, race_id: str):
        self.calls.append(race_id)
        if self.bundle is None:
            return None, {"error": "not_found"}
        return dict(self.bundle), dict(self.meta)


class _BoomSource:
    def get_with_meta(self, race_id: str):
        raise RuntimeError("prediction down")


def _sample_bundle(race_id: str = "2026-07-25-01-06") -> dict[str, Any]:
    return {
        "race_id": race_id,
        "schema_version": "1",
        "engine_source": "v2_production",
        "summary": {"honmei": "3", "confidence": 0.72, "axis": "3"},
        "runners": [
            {"umaban": 3, "name": "テスト馬", "mark": "◎", "rank": 1, "score": 0.9},
            {"umaban": 7, "name": "相手馬", "mark": "○", "rank": 2, "score": 0.7},
        ],
        "explain": {"reason": {"summary": "展開と能力指数から軸に選定"}},
    }


class PredictionConnectorAdapterTest(unittest.TestCase):
    def test_connector_fetch_ok(self):
        from app.conversation.v4.prediction import PredictionConnector

        src = _FakePredictionSource(_sample_bundle())
        fetch = PredictionConnector(source=src).fetch("2026-07-25-01-06")
        self.assertTrue(fetch.ok)
        self.assertTrue(fetch.available)
        self.assertEqual(src.calls, ["2026-07-25-01-06"])

    def test_adapter_projects_without_mutating_bundle(self):
        from app.conversation.v4.prediction import (
            ConversationPredictionAdapter,
            PredictionConnector,
        )

        original = _sample_bundle()
        original_copy = {
            "race_id": original["race_id"],
            "summary": dict(original["summary"]),
            "runners": [dict(r) for r in original["runners"]],
        }
        src = _FakePredictionSource(original)
        fetch = PredictionConnector(source=src).fetch("2026-07-25-01-06")
        official, meta = ConversationPredictionAdapter().adapt(fetch)
        self.assertIsNotNone(official)
        assert official is not None
        self.assertTrue(official["official"])
        self.assertEqual(official["summary"]["honmei"], "3")
        self.assertEqual(official["top_runners"][0]["mark"], "◎")
        self.assertFalse(meta["mutated"])
        self.assertTrue(meta["connected"])
        self.assertEqual(meta["source"], "prediction_api")
        # bundle 非破壊
        self.assertEqual(original["summary"], original_copy["summary"])
        self.assertEqual(original["runners"], original_copy["runners"])

    def test_connector_error_fail_open_meta(self):
        from app.conversation.v4.prediction import (
            ConversationPredictionAdapter,
            PredictionConnector,
        )

        fetch = PredictionConnector(source=_BoomSource()).fetch("r1")
        official, meta = ConversationPredictionAdapter().adapt(fetch)
        self.assertIsNone(official)
        self.assertTrue(meta["fail_open"])
        self.assertFalse(meta["mutated"])
        self.assertFalse(meta["connected"])


class ReviewContextBuilderPredictionTest(unittest.TestCase):
    def test_builder_uses_official_not_request_payload(self):
        from app.conversation.v4.context import ReviewContextBuilder
        from app.conversation.v4.intent_router import RoutedIntent
        from app.conversation.v4.prediction import PredictionConnector

        src = _FakePredictionSource(_sample_bundle())
        builder = ReviewContextBuilder(connector=PredictionConnector(source=src))
        routed = RoutedIntent(
            name="review_prediction",
            agent="review",
            confidence=0.9,
            race_id="2026-07-25-01-06",
            mode="review",
        )
        ctx = builder.build(
            {
                "message": "相談",
                "prediction": {
                    "race_id": "2026-07-25-01-06",
                    "summary": {"honmei": "99"},  # 無視されるべき
                },
            },
            routed,
        )
        self.assertIsNotNone(ctx.prediction)
        assert ctx.prediction is not None
        self.assertEqual(ctx.prediction["summary"]["honmei"], "3")
        self.assertNotEqual(ctx.prediction["summary"]["honmei"], "99")
        self.assertTrue(ctx.prediction_meta["connected"])
        self.assertFalse(ctx.prediction_meta["mutated"])
        self.assertTrue(ctx.prediction.get("official"))


class OrchestratorPredictionIntegrationTest(unittest.TestCase):
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

    def _orch_with_source(self, source):
        from app.conversation.v4.context import ReviewContextBuilder
        from app.conversation.v4.orchestrator import ConversationOrchestrator
        from app.conversation.v4.prediction import PredictionConnector

        builder = ReviewContextBuilder(connector=PredictionConnector(source=source))
        return ConversationOrchestrator(review_context_builder=builder)

    def test_review_gets_official_prediction(self):
        orch = self._orch_with_source(_FakePredictionSource(_sample_bundle()))
        out = orch.chat(
            {
                "message": "この予想どう思う？",
                "mode": "review",
                "race_id": "2026-07-25-01-06",
            }
        )
        self.assertEqual(out.get("agent"), "review")
        self.assertFalse(out["prediction_meta"]["mutated"])
        # Review Agent は接続口ではないため応答 meta.connected は false 固定（Agent 変更禁止）
        # Official 取得の証跡は source / used / citations
        self.assertEqual(out["prediction_meta"].get("source"), "prediction_api")
        self.assertTrue(out["prediction_meta"]["used"])
        self.assertTrue(out["platform"]["prediction_api_connected"])
        self.assertTrue(out["platform"]["prediction_read_only"])
        self.assertTrue(any(c.get("type") == "prediction_readonly" for c in (out.get("citations") or [])))
        self.assertIn(out.get("fallback"), (None, "template_no_ollama_flag"))

    def test_explain_uses_review_context_official(self):
        orch = self._orch_with_source(_FakePredictionSource(_sample_bundle()))
        out = orch.chat(
            {
                "message": "なぜ軸？",
                "mode": "explain",
                "race_id": "2026-07-25-01-06",
            }
        )
        self.assertEqual(out.get("agent"), "expert")
        self.assertEqual(out.get("mode"), "explain")
        self.assertTrue(out["prediction_meta"]["connected"])
        self.assertFalse(out["prediction_meta"]["mutated"])
        self.assertIn("prediction_api", out.get("tools_used") or [])
        self.assertNotIn("stub", str(out.get("prediction_meta")))

    def test_fail_open_when_prediction_down(self):
        from app.conversation.v4.prediction import FAIL_OPEN_MESSAGE

        orch = self._orch_with_source(_BoomSource())
        out = orch.chat(
            {
                "message": "この予想どう思う？",
                "mode": "review",
                "race_id": "2026-07-25-01-06",
            }
        )
        self.assertEqual(out.get("fallback"), "prediction_api_fail_open")
        self.assertEqual(out.get("reply"), FAIL_OPEN_MESSAGE)
        self.assertFalse(out.get("disabled"))
        self.assertTrue(out["platform"]["prediction_api_connected"])
        self.assertFalse(out["prediction_meta"]["mutated"])

        # Casual は引き続き動く
        casual = orch.chat({"message": "こんにちは"})
        self.assertEqual(casual.get("agent"), "casual")
        self.assertFalse(casual.get("disabled"))

    def test_review_agent_signature_unchanged(self):
        import inspect

        from app.conversation.v4.agents.review import ReviewAgent

        sig = inspect.signature(ReviewAgent().review)
        self.assertEqual(list(sig.parameters.keys()), ["context"])


if __name__ == "__main__":
    unittest.main()
