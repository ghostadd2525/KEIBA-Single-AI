# -*- coding: utf-8 -*-
"""
Expert Agent — 説明・QA・カバレッジ等。

Explain Mode: ReviewContext（Official Prediction）のみを根拠にする。
その他 Expert Intent: Tool Stub（本 Phase では Prediction 非接続のまま）。
"""
from __future__ import annotations

from typing import Any

from ..config import load_conversation_config, resolve_model
from ..context.review_context import ReviewContext
from ..flags import conversation_ollama_enabled
from ..intent_router import RoutedIntent
from ..ollama_client import OllamaClient
from ..prompts.builder import PromptBuilder
from ..tools.stub import ExpertToolStub


class ExpertAgent:
    name = "expert"

    def __init__(
        self,
        tools: ExpertToolStub | None = None,
        *,
        prompts: PromptBuilder | None = None,
        ollama: OllamaClient | None = None,
    ) -> None:
        self.tools = tools or ExpertToolStub()
        self.prompts = prompts or PromptBuilder()
        self._ollama = ollama

    def explain(self, context: ReviewContext) -> dict[str, Any]:
        """
        Explain Mode — ReviewContext のみ受け取る。
        Official Prediction を改変しない。
        """
        if not isinstance(context, ReviewContext):
            raise TypeError("explain() accepts ReviewContext only")

        cfg = load_conversation_config()
        message = context.message
        race_id = context.race_id
        pred = context.prediction if isinstance(context.prediction, dict) else None
        history = list(context.history or [])

        prompt = self.prompts.build_explain(
            message=message,
            race_id=race_id,
            prediction=pred,
            history=history,
        )
        reply, used_llm = self._explain_reply_from_context(prompt, cfg, context)

        max_reply = int(cfg["limits"]["max_reply_chars"])
        if len(reply) > max_reply:
            reply = reply[:max_reply]

        actions: list[dict[str, Any]] = []
        if race_id:
            actions.append({"type": "open_race", "race_id": race_id})
        else:
            actions.append({"type": "list_races"})

        meta = dict(context.prediction_meta or {})
        meta["mutated"] = False
        meta.pop("stub", None)

        return {
            "agent": self.name,
            "mode": "explain",
            "intent": {
                "name": str((context.request or {}).get("intent") or "explain_pick"),
                "confidence": (context.request or {}).get("intent_confidence"),
                "race_id": race_id,
                "slots": (context.request or {}).get("slots") or {},
            },
            "reply": reply,
            "citations": [
                {
                    "type": "official_prediction",
                    "race_id": race_id,
                    "source": "prediction_api",
                }
            ]
            if pred
            else [],
            "actions": actions,
            "tools_used": ["prediction_api"] if pred else [],
            "prompt_kind": prompt.get("kind"),
            "prediction_meta": meta,
            "llm": {
                "used": used_llm,
                "role": "explain",
            },
            "history_used": len(history),
            "context_keys": sorted(context.to_dict().keys()),
        }

    def handle(
        self,
        message: str,
        routed: RoutedIntent,
        *,
        prediction: dict[str, Any] | None = None,
        history: list[dict[str, str]] | None = None,
        review_context: ReviewContext | None = None,
    ) -> dict[str, Any]:
        # Explain は ReviewContext 経由を優先
        if review_context is not None and (
            routed.name == "explain_pick" or routed.mode == "explain"
        ):
            return self.explain(review_context)

        cfg = load_conversation_config()
        intent = routed.name
        tool_data = self.tools.execute(intent, race_id=routed.race_id)

        used_llm = False
        prompt_kind = None
        if intent == "explain_pick" or routed.mode == "explain":
            # 互換: context 無しの場合は stub（Orchestrator は通常 explain() を使う）
            pred = prediction if isinstance(prediction, dict) else None
            if not pred:
                snap = (tool_data.get("prediction") or {}) if isinstance(tool_data, dict) else {}
                if isinstance(snap, dict) and snap:
                    pred = {
                        "race_id": routed.race_id,
                        "prediction_available": False,
                        "engine_source": None,
                        "explain_summary": (tool_data.get("explain") or {}).get("summary"),
                        **{k: v for k, v in snap.items() if k not in ("tool", "stub", "message")},
                    }
            prompt = self.prompts.build_explain(
                message=message,
                race_id=routed.race_id,
                prediction=pred,
                history=history,
            )
            prompt_kind = prompt.get("kind")
            reply, used_llm = self._explain_reply(prompt, cfg, tool_data, routed)
        else:
            reply = self._compose(intent, routed, tool_data, message)

        max_reply = int(cfg["limits"]["max_reply_chars"])
        if len(reply) > max_reply:
            reply = reply[:max_reply]

        actions: list[dict[str, Any]] = []
        if routed.race_id:
            actions.append({"type": "open_race", "race_id": routed.race_id})
        else:
            actions.append({"type": "list_races"})

        mode_out = routed.mode
        if mode_out == "default" and intent == "explain_pick":
            mode_out = "explain"

        return {
            "agent": self.name,
            "mode": mode_out,
            "intent": {
                "name": intent,
                "confidence": routed.confidence,
                "race_id": routed.race_id,
                "slots": routed.slots,
            },
            "reply": reply,
            "citations": [
                {"type": "stub_tool", "name": s} for s in (tool_data.get("sources") or [])
            ],
            "actions": actions,
            "tools_used": list(tool_data.get("sources") or []),
            "tool_payload": tool_data,
            "prompt_kind": prompt_kind,
            "prediction_meta": {
                "used": bool(prediction),
                "mutated": False,
                "prediction_available": False,
                "connected": False,
                "stub": True,
            },
            "llm": {
                "used": used_llm,
                "role": "explain" if prompt_kind == "explain" else "none_in_minimal_platform",
            },
            "history_used": len(history or []),
        }

    def _explain_reply_from_context(
        self,
        prompt: dict[str, str],
        cfg: dict[str, Any],
        context: ReviewContext,
    ) -> tuple[str, bool]:
        rid = context.race_id or "（レース未指定）"
        pred = context.prediction if isinstance(context.prediction, dict) else {}
        summary = pred.get("explain_summary") or (
            (pred.get("summary") or {}).get("honmei")
            if isinstance(pred.get("summary"), dict)
            else None
        )
        template = (
            f"◎の理由（Explain Mode / レース: {rid}）\n"
            f"{summary or 'Official Prediction の選定理由を説明します。'}\n"
            "※ 順位・印・買い目は変更しません。Prediction AI が唯一の正解です。"
        )
        if not conversation_ollama_enabled():
            return template, False
        client = self._ollama or OllamaClient(
            base_url=cfg["ollama"]["base_url"],
            timeout_ms=int(cfg["ollama"]["timeout_ms"]),
        )
        result = client.chat(
            model=resolve_model(None),
            message=f"{prompt['system']}\n\n{prompt['user']}",
        )
        if result.ok and result.reply:
            return str(result.reply).strip(), True
        return template, False

    def _explain_reply(
        self,
        prompt: dict[str, str],
        cfg: dict[str, Any],
        tool_data: dict[str, Any],
        routed: RoutedIntent,
    ) -> tuple[str, bool]:
        rid = routed.race_id or "（レース未指定）"
        template = (
            f"◎の理由（Explain Mode / レース: {rid}）\n"
            f"{(tool_data.get('explain') or {}).get('summary') or 'Prediction の選定理由を説明します。'}\n"
            "※ 順位・印・買い目は変更しません。Prediction AI が唯一の正解です。"
        )
        if not conversation_ollama_enabled():
            return template, False
        client = self._ollama or OllamaClient(
            base_url=cfg["ollama"]["base_url"],
            timeout_ms=int(cfg["ollama"]["timeout_ms"]),
        )
        result = client.chat(
            model=resolve_model(None),
            message=f"{prompt['system']}\n\n{prompt['user']}",
        )
        if result.ok and result.reply:
            return str(result.reply).strip(), True
        return template, False

    def _compose(
        self,
        intent: str,
        routed: RoutedIntent,
        tool_data: dict[str, Any],
        message: str,
    ) -> str:
        rid = routed.race_id or "（レース未指定）"
        if intent == "explain_confidence":
            return (
                f"信頼度の質問だね（レース: {rid}）。\n"
                "現状 stub のため数値は返せないよ。"
                "Prediction API 接続後に、既存予測の confidence を説明する予定。"
            )
        if intent == "race_qa":
            return (
                f"レースについての質問を Expert が受けたよ（レース: {rid}）。\n"
                f"質問: {message[:80]}\n"
                "データ Tool は stub のため、事実データはまだ繋げていないよ。"
            )
        if intent == "coverage_inquiry":
            cov = tool_data.get("coverage") or {}
            return f"カバレッジ問い合わせ。{cov.get('message') or 'stub'}"
        if intent == "diagnostics_inquiry":
            diag = tool_data.get("diagnostics") or {}
            return f"診断問い合わせ。{diag.get('summary') or 'stub'}"
        if intent == "list_races":
            races = tool_data.get("races") or {}
            return f"レース一覧。{races.get('message') or 'stub'}"
        return (
            "Expert Agent が処理したよ。ただし Tool は stub で、"
            "Prediction API には接続していません。"
        )
