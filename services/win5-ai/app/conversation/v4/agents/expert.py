# -*- coding: utf-8 -*-
"""
Expert Agent — 説明・QA・カバレッジ等。

Explain Mode: ReviewContext（Official Prediction）のみを根拠にする。
その他 Expert Intent: Tool Stub（本 Phase では Prediction 非接続のまま）。
"""
from __future__ import annotations

import re
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
        pred = context.prediction if isinstance(context.prediction, dict) else {}
        message = str(context.message or "")
        req = context.request if isinstance(context.request, dict) else {}
        slots = req.get("slots") if isinstance(req.get("slots"), dict) else {}
        sub = str(slots.get("sub_intent") or "")
        if not sub:
            from ..intent_router import classify_explain_sub_intent

            sub = classify_explain_sub_intent(message)

        template = self._compose_explain_by_intent(pred, message, sub)

        if not conversation_ollama_enabled():
            return template, False
        client = self._ollama or OllamaClient(
            base_url=cfg["ollama"]["base_url"],
            timeout_ms=int(cfg["ollama"]["timeout_ms"]),
        )
        # LLM には意図と jargon 禁止を明示
        guided = (
            f"{prompt['system']}\n\n"
            f"質問意図: {sub}\n"
            "ルール: 必ず3行（または3段落）で ①結論 ②理由 ③補足 だけを返す。"
            "質問に最初に直接答える。初心者向けのやさしい日本語。"
            "「本命馬」「Prediction」「対象馬」は禁止。馬名があるときは必ず実馬名を毎回入れる。"
            "「この馬」「このレース」は名前・レース情報が取れないときだけの最終手段。"
            "質問以外の話題へ広げない。不安材料に安心材料を混ぜない。"
            "戦略画面への誘導は買い方・点数・資金のときだけ。"
            "リアクションや思考メモの余分な行は入れない。"
            "「ステージ」「総合バランス」「拮抗」「抜けている」などの内部用語は使わない。\n\n"
            f"{prompt['user']}"
        )
        result = client.chat(
            model=resolve_model(None),
            message=guided,
        )
        if result.ok and result.reply:
            return str(result.reply).strip(), True
        return template, False

    def _compose_explain_by_intent(
        self, pred: dict[str, Any], message: str, sub: str
    ) -> str:
        """結論→理由→補足。実馬名を毎回明示。内部語は使わない。"""
        if sub == "unknown":
            return (
                "ごめんね、ちょっと質問の内容が分からなかったよ😅\n"
                "レースについてなら何でも聞いてね。"
            )
        if sub == "casual":
            text = (message or "").strip()
            soft = "うん、聞いてるよ。"
            if "おはよう" in text:
                soft = "おはよう！"
            elif "こんばんは" in text:
                soft = "こんばんは！"
            elif re.search(r"こんにちは|はじめまして|hello|hi\b|やあ|ハロー", text, re.I):
                soft = "こんにちは！"
            elif re.search(r"疲れた|つかれた|お疲れ|おつかれ|眠い|ねむい", text):
                soft = "お疲れさま。少し休んでね。"
            elif "暑い" in text:
                soft = "だよね、暑いね。"
            elif "寒い" in text:
                soft = "だよね、寒いね。"
            elif re.search(r"ありがとう|サンキュ|どうも", text):
                soft = "どういたしまして。"
            return (
                f"{soft}\n"
                "雑談したいときは通常のKAOBAチャットでも話せるよ😊\n"
                "レースについて気になることがあれば、何でも聞いてね。"
            )

        tops = pred.get("top_runners") if isinstance(pred.get("top_runners"), list) else []
        race_info = pred.get("race_info") if isinstance(pred.get("race_info"), dict) else {}
        venue = str(race_info.get("venue") or "")
        field = race_info.get("field_size")
        distance = race_info.get("distance")
        surface = race_info.get("surface")
        race_no = race_info.get("race_no")
        if race_no is None:
            race_no = race_info.get("race_number")
        race_id = str(pred.get("race_id") or race_info.get("race_id") or "")
        if venue and race_no is not None:
            place = f"{venue}{race_no}R"
        elif venue:
            place = venue
        elif race_id:
            place = race_id
        else:
            place = "このレース"

        def _label(r: dict[str, Any]) -> str:
            num = r.get("umaban") or r.get("horse_number") or ""
            name = str(r.get("name") or r.get("horse_name") or "").strip()
            if name:
                return f"{num}番{name}".strip() if num != "" and num is not None else name
            if num != "" and num is not None:
                return f"{num}番"
            return ""

        honmei = tops[0] if tops else {}
        axis = _label(honmei) or "中心の馬"

        if sub == "betting":
            return (
                f"この買い方なら、{axis}を中心に進めて大丈夫だと思うよ。\n"
                "大きく崩すより、点数と総額を守るほうが安心。\n"
                "穴馬・少額・雨・オッズの話も、気になるところから聞いてね。"
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

        def _bare(r: dict[str, Any] | None) -> str:
            if not r:
                return ""
            return str(r.get("name") or r.get("horse_name") or "").strip()

        honmei = _label(tops[0]) if tops and isinstance(tops[0], dict) else ""
        honmei = honmei or "この馬"
        honmei_bare = _bare(tops[0] if tops and isinstance(tops[0], dict) else None) or honmei
        rival = _label(tops[1]) if len(tops) > 1 and isinstance(tops[1], dict) else ""
        rival = rival or "2番手"
        ana_labels = [
            _label(t)
            for t in tops[2:4]
            if isinstance(t, dict)
        ]
        ana_labels = [x for x in ana_labels if x]
        ana_bares = [
            _bare(t)
            for t in tops[2:4]
            if isinstance(t, dict) and _bare(t)
        ]

        try:
            dist_n = float(distance) if distance is not None else None
        except (TypeError, ValueError):
            dist_n = None
        try:
            field_n = int(field) if field is not None else None
        except (TypeError, ValueError):
            field_n = None

        def merge_reason(lines: list[str], fallback: str) -> str:
            xs = [str(x).strip() for x in (lines or []) if str(x).strip()]
            if not xs:
                return fallback
            if len(xs) == 1:
                return xs[0]
            head = xs[0]
            if head.endswith("だよ"):
                head = head[:-2]
            elif head.endswith("よ"):
                head = head[:-1]
            return f"{head}し、{xs[1]}"

        def compose_explain(conclusion: str, reason: str, supplement: str) -> str:
            return "\n".join([p for p in (conclusion, reason, supplement) if p])

        why_bits: list[str] = []
        gap_bits: list[str] = []
        risk_bits: list[str] = []
        if dist_n is not None:
            if dist_n <= 1400:
                why_bits.append("短い距離なので、出して好位に付けた馬が最後まで残りやすいよ")
                risk_bits.append("出遅れると、追い上げる間もなく終わってしまいやすいよ")
                gap_bits.append("短い距離では、序盤に前へ行けた側が残りやすいよ")
            elif dist_n <= 1800:
                why_bits.append("道中の運びと、最後の直線での伸びの両方が効きやすい距離だよ")
                risk_bits.append("ペースを誤ると、最後の直線で勢いが落ちやすいよ")
                gap_bits.append(f"{int(dist_n)}mでは、直線でどれだけ脚を使えるかの差が出やすいよ")
            else:
                why_bits.append("長い距離なので、後半まで脚を使える馬が残りやすいよ")
                risk_bits.append("後半につかれてしまうと、直線で差されやすくなるよ")
                gap_bits.append("長い距離では、後半に脚が残るかどうかで差が出やすいよ")
        if venue or surface:
            course = f"{venue}の{surface}" if venue and surface else (venue or str(surface))
            why_bits.append(f"{course}らしい流れになりやすく、そこで運べる馬が残るイメージだよ")
            gap_bits.append(f"{course}では、どの位置から直線に入れるかの差が出やすいよ")
            risk_bits.append(f"{course}で想定と違う流れになると、直線まで脚が持たなくなりやすいよ")
        if field_n is not None:
            if field_n <= 10:
                why_bits.append(f"出走{field_n}頭と少なめで、実力差が出やすい並びだよ")
                gap_bits.append("少頭数なので、2頭の差が着順に出やすいよ")
            elif field_n >= 15:
                gap_bits.append(f"出走{field_n}頭と多く、馬群の中で差が埋もれやすいよ")
                risk_bits.append(f"出走{field_n}頭だと馬群に包まれ、進路が取れないと崩れやすいよ")
        if not gap_bits:
            gap_bits.append("位置取りと、直線での伸び方の差が出やすいよ")
        if not risk_bits:
            risk_bits.append("想定と違うペースになると、位置を取れず苦しくなりやすいよ")
            risk_bits.append("前が止まらない展開だと、狙った形を作れないよ")

        if sub == "gap_vs_rival":
            top = gap_bits[0] if gap_bits else "位置取りと、直線での伸び方の差が出やすいよ"
            return compose_explain(
                f"{honmei}と{rival}を比べると、{top}",
                merge_reason(gap_bits[:2], top),
                f"だから今回は{honmei_bare}を一歩前に見ているよ。",
            )

        if sub == "risks":
            top = risk_bits[0] if risk_bits else "想定と違うペースになると苦しくなりやすいよ"

            def _strip_yo(s: str) -> str:
                t = str(s or "").strip().rstrip("。．")
                if t.endswith("だよ"):
                    return t[:-2]
                if t.endswith("よ"):
                    return t[:-1]
                return t

            return compose_explain(
                f"{honmei}で一番心配なのは、{_strip_yo(top)}ことだよ。",
                merge_reason(
                    risk_bits[:2],
                    "想定と違う流れになると、力を出しにくくなりやすいよ。",
                ),
                f"もしその流れになると、{honmei_bare}も力を出しにくくなるよ。",
            )

        if sub == "upset":
            if len(ana_labels) >= 2:
                conclusion = f"穴候補として見たいのは{ana_labels[0]}と{ana_labels[1]}だよ。"
            elif ana_labels:
                conclusion = f"穴候補として見たいのは{ana_labels[0]}だよ。"
            else:
                conclusion = "穴を探すなら、上位以外で今回の距離・流れが合う馬だよ。"
            upset_bits: list[str] = []
            if field_n is not None and field_n >= 15:
                upset_bits.append(f"出走{field_n}頭と多く、伏兵が紛れやすいよ")
            if dist_n is not None:
                upset_bits.append(
                    "短い距離では、序盤の位置取り次第で人気薄が残ることがあるよ"
                    if dist_n <= 1400
                    else f"{int(dist_n)}mが合う人気薄は、直線で伸びてくることがあるよ"
                )
            if not upset_bits:
                upset_bits.extend(gap_bits[:2])
            tip_name = (ana_bares[0] if ana_bares else "") or (ana_labels[0] if ana_labels else "")
            tip_wrap = (
                f"だから{tip_name}は相手の端に残しておきたいよ。"
                if tip_name
                else f"{place}では、条件が合う人気薄を端に置いておく感じだよ。"
            )
            return compose_explain(
                conclusion,
                merge_reason(upset_bits[:2], "今回の流れに合いそうな人気薄を拾ったよ。"),
                tip_wrap,
            )

        # why_honmei / default explain
        reason = (
            f"近走内容・距離・展開の相性をまとめて見ると、{honmei_bare}が一番安定して走れそうだったよ。"
            if why_bits
            else "近走内容・距離・展開の相性をまとめて見ると、一番安定して走れそうだったよ。"
        )
        return compose_explain(
            f"{honmei}を◎にした一番の理由は、今回の条件なら一番力を発揮しやすいと判断したからだよ。",
            reason,
            f"だから今回は{honmei_bare}を中心に考えているよ。",
        )

    def _explain_reply(
        self,
        prompt: dict[str, str],
        cfg: dict[str, Any],
        tool_data: dict[str, Any],
        routed: RoutedIntent,
    ) -> tuple[str, bool]:
        template = (
            "ごめんね、ちょっと質問の内容が分からなかったよ😅\n"
            "レースについてなら何でも聞いてね。"
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
