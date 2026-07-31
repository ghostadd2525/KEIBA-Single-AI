# -*- coding: utf-8 -*-
"""
Review Agent — レース相談の会話文のみ生成。

公開 API: review(context: ReviewContext) のみ。
Flow: ReviewContext → Prompt Builder → Ollama
レポート見出し（予想の強み / リスク / 展開…）は出さない。
回答は 結論 → 理由 → 補足 の会話形式。
Prediction / 印 / 順位 / 買い目ロジックは変更しない。
"""
from __future__ import annotations

import re
from typing import Any

from ..config import load_conversation_config, resolve_model
from ..context.review_context import ReviewContext
from ..flags import conversation_ollama_enabled, review_agent_enabled
from ..intent_router import classify_consult_route, classify_explain_sub_intent
from ..ollama_client import OllamaClient
from ..prompts.builder import PromptBuilder

_REWRITE_RE = re.compile(
    r"(本命を|印を|順位を|買い目を).{0,8}(変更|変え|差し替|修正)|"
    r"(別の本命|代わりに|おすすめは\d+番|私なら|買い目提案)",
    re.I,
)

_EXPLAIN_REDIRECT = (
    "その内容は「予想の説明」で確認できるよ。\n"
    "馬の理由や差・不安・穴の話はそちらが向いているよ。\n"
    "ここでは買い方や立ち回りの相談を続けよう。"
)

_ROOM_CHAT_REDIRECT = (
    "その話ならルームチャットで話そう😊\n"
    "ここではレースや買い方の相談を中心に案内しているよ。"
)

_GREETING_TAIL = "レースや買い方について気になることがあれば、一緒に考えるよ。"


def _greeting_reply(message: str) -> str:
    text = (message or "").strip()
    if re.search(r"ありがとう|どうも|サンキュ", text):
        soft = "どういたしまして😊"
    elif re.search(r"お疲れ|おつかれ", text):
        soft = "お疲れさま😊"
    elif "おはよう" in text:
        soft = "おはよう😊"
    elif "こんばんは" in text:
        soft = "こんばんは😊"
    elif re.search(r"hello|hi\b|ハロー", text, re.I):
        soft = "Hello😊"
    else:
        soft = "こんにちは😊"
    return f"{soft}\n{_GREETING_TAIL}"


def _horse_label(pred: dict[str, Any] | None) -> str:
    if not isinstance(pred, dict):
        return "中心の馬"
    tops = pred.get("top_runners") if isinstance(pred.get("top_runners"), list) else []
    if tops and isinstance(tops[0], dict):
        r = tops[0]
        num = r.get("umaban") or r.get("horse_number") or ""
        name = str(r.get("name") or r.get("horse_name") or "").strip()
        if name:
            return f"{num}番{name}".strip() if num != "" and num is not None else name
        if num != "" and num is not None:
            return f"{num}番"
    return "中心の馬"


def _strategy_reply(route: str, pred: dict[str, Any] | None) -> str:
    axis = _horse_label(pred)
    sub = route.split(":", 1)[1] if ":" in route else "betting"
    if sub == "skip":
        return (
            "迷うなら、無理に大きく買わず見送り寄りでいいよ。\n"
            "自信が薄いときは総額を抑えるか、主軸だけ少額にするのが無難。\n"
            "今日の調子に合わせて、無理しない立ち回りを優先しよう。"
        )
    if sub == "beginner":
        return (
            "初心者なら、主軸（馬連・ワイド）を少点数で買うのがおすすめだよ。\n"
            "保険や一発は後回しにして、総額も普段どおりに抑えよう。\n"
            f"軸の {axis} を中心に、相手は広げすぎないのが安心。"
        )
    if sub == "weather":
        return (
            "雨なら、前が残るか崩れやすいかが変わりやすいよ。\n"
            "軸は変えず、相手を1頭増減して様子を見るのが無難。\n"
            "馬場発表を見てから最終判断しよう。"
        )
    if sub == "odds":
        return (
            "オッズが動いても、軸をすぐ変えないのがおすすめだよ。\n"
            "人気が急に集まった相手は点数を少し抑えめに。\n"
            "総額の上限は守ったまま調整しよう。"
        )
    if sub == "budget":
        return (
            "少額なら、主軸（馬連・ワイド）に寄せるのがおすすめだよ。\n"
            "保険や一発は後回しにして、総額を普段どおりに抑えよう。\n"
            f"軸の {axis} 中心はそのままで大丈夫。"
        )
    if sub == "risks":
        return (
            "展開が想定と違うと、着順は動きやすいよ。\n"
            "だから大きく勝負するより、普段どおりの金額が安心。\n"
            "迷うなら点数を減らすか、見送り寄りでもいいよ。"
        )
    return (
        f"この買い方なら、軸の {axis} を中心に進めて大丈夫だと思うよ。\n"
        "大きく崩すより、点数と総額を守るほうが安心。\n"
        "迷うところがあれば、見送りや少額の話も続けて聞いてね。"
    )


def _template_chat(message: str, pred: dict[str, Any] | None) -> str:
    """classify_consult_route に従う（①Greeting ②Explain ③Strategy ④Room）。"""
    route = classify_consult_route(message)
    if route == "greeting":
        return _greeting_reply(message)
    if route == "explain_redirect":
        return _EXPLAIN_REDIRECT
    if route == "room_chat_redirect":
        return _ROOM_CHAT_REDIRECT
    if route.startswith("strategy:"):
        return _strategy_reply(route, pred)
    return _ROOM_CHAT_REDIRECT


class ReviewAgent:
    name = "review"

    def __init__(
        self,
        *,
        prompts: PromptBuilder | None = None,
        ollama: OllamaClient | None = None,
    ) -> None:
        self.prompts = prompts or PromptBuilder()
        self._ollama = ollama

    def review(self, context: ReviewContext) -> dict[str, Any]:
        """Review Agent の唯一の公開入口。ReviewContext のみ受け取る。"""
        if not isinstance(context, ReviewContext):
            raise TypeError("ReviewAgent.review requires ReviewContext")

        cfg = load_conversation_config()
        req = context.request or {}
        race_id = context.race_id
        message = context.message or ""

        if not review_agent_enabled():
            return {
                "agent": self.name,
                "mode": context.mode or "review",
                "intent": {
                    "name": "review_disabled",
                    "confidence": req.get("intent_confidence") or 0.0,
                    "race_id": race_id,
                    "slots": req.get("slots") or {},
                },
                "reply": "いま相談の準備中だよ。少し待ってからもう一度ね。",
                "citations": [],
                "actions": [],
                "tools_used": [],
                "prediction_meta": {
                    **(context.prediction_meta or {}),
                    "used": False,
                    "mutated": False,
                    "connected": False,
                    "source": "none",
                },
                "llm": {"used": False, "role": "review"},
                "fallback": "flag_off",
                "context_keys": list(context.to_dict().keys()),
            }

        prompt = self.prompts.build_review(context)
        route = classify_consult_route(message)
        # ルーティングは実装で確定（プロンプト任せにしない）
        reply = _template_chat(message, context.prediction)
        llm_meta = {"used": False, "role": "consult_route"}
        fallback = route
        reply = self._guard_output(reply, message, context.prediction)

        max_reply = int(cfg["limits"]["max_reply_chars"])
        if len(reply) > max_reply:
            reply = reply[:max_reply]

        actions: list[dict[str, Any]] = []
        if race_id:
            actions.append({"type": "open_race", "race_id": race_id})

        meta = dict(context.prediction_meta or {})
        meta["mutated"] = False
        meta["connected"] = False

        pred = context.prediction
        return {
            "agent": self.name,
            "mode": context.mode or "review",
            "intent": {
                "name": req.get("intent") or "review_prediction",
                "confidence": req.get("intent_confidence") or 0.0,
                "race_id": race_id,
                "slots": {
                    **(req.get("slots") or {}),
                    "review_rules": "no_mutate_prediction",
                    "input": "ReviewContext",
                    "sub_intent": classify_explain_sub_intent(message),
                    "consult_route": classify_consult_route(message),
                },
            },
            "reply": reply,
            "citations": [
                {
                    "type": "prediction_readonly",
                    "race_id": race_id,
                    "engine_source": meta.get("engine_source")
                    or ((pred or {}).get("engine_source") if pred else None),
                }
            ]
            if pred
            else [],
            "actions": actions,
            "tools_used": [],
            "prompt_kind": prompt.get("kind"),
            "prediction_meta": meta,
            "llm": llm_meta,
            "fallback": fallback,
            "review_style": "conversational",
            "context_keys": list(context.to_dict().keys()),
            "history_used": len(context.history or []),
        }

    def _generate(
        self,
        prompt: dict[str, str],
        cfg: dict[str, Any],
        message: str,
        pred: dict[str, Any] | None,
    ) -> tuple[str, dict[str, Any], str | None]:
        model = resolve_model(None)
        template = _template_chat(message, pred)
        if not conversation_ollama_enabled():
            return template, {"used": False, "role": "review_template"}, "template_no_ollama_flag"

        client = self._ollama or OllamaClient(
            base_url=cfg["ollama"]["base_url"],
            timeout_ms=int(cfg["ollama"]["timeout_ms"]),
            chat_path=cfg["ollama"]["chat_path"],
            tags_path=cfg["ollama"]["tags_path"],
        )
        combined = f"{prompt['system']}\n\n{prompt['user']}"
        result = client.chat(model=model, message=combined)
        if result.ok and result.reply:
            return (
                result.reply,
                {"used": True, "role": "review", "model": result.model or model, "provider": "ollama"},
                None,
            )
        return (
            template,
            {"used": False, "role": "review_fail_open", "model": model},
            result.error_reason or "ollama_error",
        )

    def _guard_output(
        self, reply: str, message: str, pred: dict[str, Any] | None
    ) -> str:
        text = str(reply or "").strip() or _template_chat(message, pred)
        # 旧レポート見出しが混入したら会話テンプレへ差し替え
        if re.search(r"^##\s*(予想の強み|リスク|展開の注目点|初心者向け)", text, re.M):
            return _template_chat(message, pred)
        if _REWRITE_RE.search(text):
            return _template_chat(message, pred)
        # 内部設計語が混入したら相談AIテンプレへ
        if re.search(
            r"Review\s*Agent|予想は変更しません|印は変更しません|Prediction\s*AI|"
            r"内容は受け取ったよ|どこからでも大丈夫|買い方のどこが気になる",
            text,
            re.I,
        ):
            return _template_chat(message, pred)
        return text
