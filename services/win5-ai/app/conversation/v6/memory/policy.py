# -*- coding: utf-8 -*-
"""
Memory Policy — 保存可能 / 禁止の単一判定。

自動保存は行わない。Consent 有無は ConsentManager の責務。
"""
from __future__ import annotations

import re
from typing import Any

from .models import ALLOWED_CATEGORIES, MemoryCandidate

# 禁止トピック（部分一致 · 大小無視）
FORBIDDEN_TOKENS = (
    "prediction",
    "予測",
    "予想結果",
    "ranking",
    "ランキング",
    "confidence",
    "自信度",
    "security",
    "セキュリティ",
    "api_key",
    "api key",
    "apikey",
    "feature flag",
    "feature_flag",
    "f_v4_",
    "f_v5_",
    "f_v6_",
    "system prompt",
    "システムプロンプト",
    "secret",
    "シークレット",
    "password",
    "パスワード",
    "token",
    "トークン",
    "conversation history",
    "会話履歴",
    "履歴を保存",
)

# カテゴリ推定パターン（同意後の内容解析のみ）
_CATEGORY_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "nickname",
        "nickname",
        re.compile(
            r"(?:ニックネーム|名前|呼び名)[はを:\s]*(.+?)(?:って|と)?(?:覚えて|記憶|$)",
            re.I,
        ),
    ),
    (
        "address_form",
        "address_form",
        re.compile(
            r"(?:呼び方|呼んで)[はを:\s]*(.+?)(?:って|と)?(?:覚えて|記憶|$)",
            re.I,
        ),
    ),
    (
        "favorite_venue",
        "favorite_venue",
        re.compile(
            r"(?:好きな競馬場|推し競馬場|競馬場)[はを:\s]*(.+?)(?:って|を)?(?:覚えて|記憶|$)",
            re.I,
        ),
    ),
    (
        "favorite_jockey",
        "favorite_jockey",
        re.compile(
            r"(?:好きな騎手|推し騎手|騎手)[はを:\s]*(.+?)(?:って|を)?(?:覚えて|記憶|$)",
            re.I,
        ),
    ),
    (
        "favorite_horse",
        "favorite_horse",
        re.compile(
            r"(?:好きな馬|推し馬|馬)[はを:\s]*(.+?)(?:って|を)?(?:覚えて|記憶|$)",
            re.I,
        ),
    ),
    (
        "explain_style",
        "explain_style",
        re.compile(
            r"(?:説明スタイル|説明の仕方|説明は)[はを:\s]*(.+?)(?:って|で)?(?:覚えて|記憶|$)",
            re.I,
        ),
    ),
    (
        "answer_length",
        "answer_length",
        re.compile(
            r"(?:回答の長さ|答えは|回答は)[はを:\s]*(.+?)(?:って|で)?(?:覚えて|記憶|$)",
            re.I,
        ),
    ),
    (
        "conversation_settings",
        "conversation_settings",
        re.compile(
            r"(?:会話設定|チャット設定|Conversation設定)[はを:\s]*(.+?)(?:って|を)?(?:覚えて|記憶|$)",
            re.I,
        ),
    ),
]

_STRIP_CONSENT = re.compile(
    r"(?:を)?(?:覚えて(?:おいて|て)?|記憶して(?:おいて|て)?|メモして(?:おいて|て)?|"
    r"remember(?:\s+this)?)\s*$",
    re.I,
)


class MemoryPolicy:
    """保存対象 / 禁止のポリシー。"""

    version = "v6-phase2"

    def is_forbidden_text(self, text: str) -> str | None:
        raw = str(text or "")
        lowered = raw.lower()
        for token in FORBIDDEN_TOKENS:
            if token.lower() in lowered:
                return f"forbidden_topic:{token}"
        return None

    def is_allowed_category(self, category: str) -> bool:
        return str(category or "") in ALLOWED_CATEGORIES

    def extract_candidate(
        self,
        *,
        user_id: str,
        message: str,
        consent_detected: bool,
    ) -> MemoryCandidate:
        """
        候補抽出。consent_detected=False の場合も候補は作れるが
        Manager は保存しない（自動保存禁止の証拠用）。
        """
        text = str(message or "").strip()
        forbidden = self.is_forbidden_text(text)
        if forbidden:
            return MemoryCandidate(
                user_id=user_id,
                category="user_explicit",
                key="rejected",
                value="",
                source_text=text,
                consent_detected=consent_detected,
                rejected_reason=forbidden,
            )

        category = "user_explicit"
        key = "note"
        value = text

        for cat, k, pattern in _CATEGORY_PATTERNS:
            m = pattern.search(text)
            if m:
                category = cat
                key = k
                value = m.group(1).strip(" 　「」『』\"'")
                break
        else:
            # 「覚えて：〜」/ 同意語を除去した残りを user_explicit として保存
            cleaned = _STRIP_CONSENT.sub("", text).strip()
            cleaned = re.sub(r"^(?:覚えて|記憶して|メモして)[:：\s]*", "", cleaned)
            cleaned = cleaned.strip(" 　:：")
            if cleaned:
                value = cleaned
            else:
                return MemoryCandidate(
                    user_id=user_id,
                    category="user_explicit",
                    key="empty",
                    value="",
                    source_text=text,
                    consent_detected=consent_detected,
                    rejected_reason="empty_value",
                )

        if not self.is_allowed_category(category):
            return MemoryCandidate(
                user_id=user_id,
                category=category,
                key=key,
                value=value,
                source_text=text,
                consent_detected=consent_detected,
                rejected_reason="category_not_allowed",
            )

        forbidden_value = self.is_forbidden_text(value)
        if forbidden_value:
            return MemoryCandidate(
                user_id=user_id,
                category=category,
                key=key,
                value=value,
                source_text=text,
                consent_detected=consent_detected,
                rejected_reason=forbidden_value,
            )

        return MemoryCandidate(
            user_id=user_id,
            category=category,
            key=key,
            value=value,
            source_text=text,
            consent_detected=consent_detected,
            rejected_reason=None,
        )

    def meta(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "allowed_categories": sorted(ALLOWED_CATEGORIES),
            "auto_save": False,
            "requires_consent": True,
        }
