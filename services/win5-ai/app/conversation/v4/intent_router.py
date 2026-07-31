# -*- coding: utf-8 -*-
"""
Intent Router — Conversation Platform の中心。

Agent: casual | expert | review | chat
Mode: explain | review | chat | default
intent=chat のときのみ Chat Agent へルーティング。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from .modes import (
    MODE_CHAT,
    MODE_EXPLAIN,
    MODE_REVIEW,
    ConversationMode,
    normalize_mode,
)

AgentKind = Literal["casual", "expert", "review", "chat"]


@dataclass
class RoutedIntent:
    name: str
    agent: AgentKind
    confidence: float
    race_id: str | None = None
    mode: ConversationMode = "default"
    slots: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


# (intent, agent, keywords, confidence)
_RULES: list[tuple[str, AgentKind, tuple[str, ...], float]] = [
    # Personal Chat（マイページ日常会話 · KAOBA 非依存）
    (
        "chat",
        "chat",
        ("雑談", "おしゃべり", "日常会話", "personal chat", "マイページで話", "暇つぶし"),
        0.93,
    ),
    ("greeting", "casual", ("こんにちは", "こんばんは", "おはよう", "hello", "hi", "やあ"), 0.92),
    (
        "app_guide",
        "casual",
        ("使い方", "ヘルプ", "help", "何ができる", "どう使う", "ガイド", "案内"),
        0.9,
    ),
    (
        "refuse_predict",
        "casual",
        ("新しい予想", "本命を作って", "予測して作", "今から予想", "自分で予想", "生成して"),
        0.9,
    ),
    (
        "review_prediction",
        "review",
        ("相談", "レビュー", "review", "どう思う", "見てほしい", "意見を", "相談したい"),
        0.91,
    ),
    (
        "explain_pick",
        "expert",
        ("◎の理由", "本命の理由", "理由を聞く", "理由", "なぜ", "根拠", "why", "どうして", "選定", "説明して"),
        0.9,
    ),
    (
        "explain_confidence",
        "expert",
        ("信頼度", "confidence", "確信度", "どのくらい確か"),
        0.88,
    ),
    (
        "race_qa",
        "expert",
        ("レース", "出走", "枠順", "馬場", "距離", "発走", "何頭"),
        0.8,
    ),
    (
        "coverage_inquiry",
        "expert",
        ("カバレッジ", "coverage", "対応率", "データ状況"),
        0.88,
    ),
    (
        "diagnostics_inquiry",
        "expert",
        ("不足", "missing", "診断", "フォールバック", "mock"),
        0.88,
    ),
    (
        "list_races",
        "expert",
        ("レース一覧", "今日のレース", "開催一覧"),
        0.85,
    ),
    (
        "refuse_predict",
        "casual",
        ("予想して", "本命は", "印を", "予測して", "買い目を出して"),
        0.86,
    ),
]

_RACE_ID_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}|\d{8}_[a-z]+_\d{1,2})",
    re.I,
)


def classify_explain_sub_intent(message: str) -> str:
    """Explain / Review 共通の質問観点（UI13: 雑談 / 不明を分離）。"""
    text = (message or "").strip()
    if not text:
        return "unknown"
    # レース相談の天候・オッズ・見送り・初心者は雑談より先
    if re.search(r"雨なら|雨だと|雨の|重馬場|不良馬場|馬場.*悪|天候", text):
        return "weather"
    if re.search(r"オッズ", text):
        return "odds"
    if re.search(r"少額|予算", text):
        return "budget"
    if re.search(r"見送|パスする|買わない|休むべき", text):
        return "skip"
    if re.search(r"初心者|初めて|入門|わかりやすく", text):
        return "beginner"
    if re.search(r"この買い|買い方どう|戦略どう|どう思う|評価して", text):
        return "betting"
    # 雑談を先に（Explain 役割は維持しつつ短く返す）
    if re.search(
        r"こんにちは|こんばんは|おはよう|やあ|はじめまして|hello|hi\b|ハロー",
        text,
        re.I,
    ):
        return "casual"
    if re.search(r"疲れた|つかれた|お疲れ|おつかれ|眠い|ねむい|元気|調子|気分", text):
        return "casual"
    if re.search(r"暑い|寒い|天気|晴れ|雪", text) and not re.search(r"雨", text):
        return "casual"
    if re.search(r"ありがとう|どうも|サンキュ|すき|好き|かわいい|可愛い", text):
        return "casual"
    if re.search(r"暇|つまらない|どうしてる|何してる|しゃべ|雑談|おしゃべり", text):
        return "casual"
    if re.search(r"差|対抗|2番|二番|比較|違い|どれくらい|どのくらい離れ", text):
        return "gap_vs_rival"
    if re.search(r"不安|リスク|危険|弱点|心配|崩れ|取れない|厳しい", text):
        return "risks"
    if re.search(r"買い方|買い目|どう買う|券種|点数|流し|ワイド|馬連|三連", text):
        return "betting"
    if re.search(r"穴馬|穴候補|大穴|波乱馬|穴は|一発", text):
        return "upset"
    if re.search(r"なぜ|理由|根拠|どうして|本命|◎|選定", text):
        return "why_honmei"
    return "unknown"


def is_consult_greeting(message: str) -> bool:
    """相談AI内で返す挨拶（ルーム誘導しない）。"""
    text = (message or "").strip()
    if not text:
        return False
    # 競馬・戦略語が混ざる場合は Greeting にしない
    if re.search(
        r"買い|資金|少額|予算|見送|雨|馬場|オッズ|初心|戦略|立ち回|点数|◎|本命|穴馬|不安",
        text,
    ):
        return False
    if re.search(
        r"こんにちは|こんばんは|おはよう|おはようございます|やあ|はじめまして|hello|hi\b|ハロー",
        text,
        re.I,
    ):
        return True
    if re.search(r"お疲れ|おつかれ|ありがとう|どうも|サンキュ", text):
        return True
    return False


def classify_consult_route(message: str) -> str:
    """
    相談AIルーティング（実装で強制）。

    優先順位:
      1) greeting — 挨拶（ルーム誘導しない）
      2) explain_redirect — ◎理由 / 差 / 不安 / 穴馬
      3) strategy:<sub> — 買い方・資金・天候・オッズなど
      4) room_chat_redirect — 雑談・意味不明・競馬無関係
    """
    text = (message or "").strip()
    if not text:
        return "room_chat_redirect"

    # 意味を持たない短い英数字・記号のみ
    if re.fullmatch(r"[a-zA-Z0-9]{1,12}", text):
        return "room_chat_redirect"
    if re.fullmatch(r"[.．。…・\-_=+*]{1,12}", text):
        return "room_chat_redirect"

    # ① Greeting（ルーム誘導しない）
    if is_consult_greeting(text):
        return "greeting"

    # ② Explain質問
    if re.search(
        r"なぜ|◎|本命.*理由|2番との差|対抗との差|不安材料|穴馬|穴候補|穴は\？|穴は\?",
        text,
    ):
        return "explain_redirect"

    sub = classify_explain_sub_intent(text)
    if sub in ("why_honmei", "gap_vs_rival", "upset"):
        return "explain_redirect"
    if sub == "risks" and re.search(r"不安材料|弱点|心配な点", text):
        return "explain_redirect"

    # ③ Strategy相談
    if sub in ("weather", "odds", "budget", "skip", "beginner", "betting"):
        return f"strategy:{sub}"
    if sub == "risks":
        return "strategy:risks"
    if re.search(
        r"買い|資金|少額|予算|見送|雨|馬場|オッズ|初心|戦略|立ち回|点数|券種|ワイド|馬連|三連|どう思う",
        text,
    ):
        return "strategy:betting"

    # ④ 雑談・意味不明・競馬無関係（暑い・食べ物など）
    return "room_chat_redirect"


class IntentRouter:
    """Intent Router — Agent 責務分離の唯一の分岐点。"""

    def route(
        self,
        message: str,
        *,
        explicit_race_id: str | None = None,
        mode: ConversationMode | str | None = None,
    ) -> RoutedIntent:
        text = (message or "").strip()
        lower = text.lower()
        race_id = (explicit_race_id or "").strip() or None
        if not race_id:
            m = _RACE_ID_RE.search(text)
            if m:
                race_id = m.group(1)

        resolved_mode = normalize_mode(mode) if mode is not None else "default"

        # Mode 明示が最優先
        if resolved_mode == MODE_CHAT:
            return RoutedIntent(
                name="chat",
                agent="chat",
                confidence=0.95,
                race_id=None,  # Personal Chat はレース文脈を持たない
                mode=MODE_CHAT,
                slots={"from_mode": True, "kaoba_independent": True},
                reason="mode:chat",
            )
        if resolved_mode == MODE_REVIEW:
            return RoutedIntent(
                name="review_prediction",
                agent="review",
                confidence=0.95,
                race_id=race_id,
                mode=MODE_REVIEW,
                slots={"from_mode": True},
                reason="mode:review",
            )
        if resolved_mode == MODE_EXPLAIN:
            sub = classify_explain_sub_intent(text)
            return RoutedIntent(
                name="explain_pick",
                agent="expert",
                confidence=0.95,
                race_id=race_id,
                mode=MODE_EXPLAIN,
                slots={"from_mode": True, "sub_intent": sub},
                reason=f"mode:explain:{sub}",
            )

        if not text:
            return RoutedIntent(
                name="unknown",
                agent="casual",
                confidence=0.0,
                race_id=race_id,
                mode=resolved_mode,
                reason="empty_message",
            )

        for name, agent, keywords, conf in _RULES:
            if any(k in text or k.lower() in lower for k in keywords):
                # Chat Agent へは intent=chat のときのみ
                if name == "chat":
                    return RoutedIntent(
                        name="chat",
                        agent="chat",
                        confidence=conf,
                        race_id=None,
                        mode=MODE_CHAT,
                        slots={"matched": True, "kaoba_independent": True},
                        reason="keyword:chat",
                    )
                mode_out: ConversationMode = (
                    MODE_REVIEW
                    if agent == "review"
                    else MODE_EXPLAIN
                    if name == "explain_pick"
                    else resolved_mode
                )
                slots: dict[str, Any] = {"matched": True}
                if name == "explain_pick" or mode_out == MODE_EXPLAIN:
                    slots["sub_intent"] = classify_explain_sub_intent(text)
                return RoutedIntent(
                    name=name,
                    agent=agent,
                    confidence=conf,
                    race_id=race_id,
                    mode=mode_out,
                    slots=slots,
                    reason=f"keyword:{name}",
                )

        if race_id:
            return RoutedIntent(
                name="race_qa",
                agent="expert",
                confidence=0.7,
                race_id=race_id,
                mode=resolved_mode,
                reason="race_id_present",
            )

        return RoutedIntent(
            name="unknown",
            agent="casual",
            confidence=0.35,
            race_id=None,
            mode=resolved_mode,
            reason="no_match",
        )
