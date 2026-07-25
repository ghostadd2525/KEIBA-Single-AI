# -*- coding: utf-8 -*-
"""
Security Guard — Personal Chat 情報漏洩防止。

Orchestrator → Security Guard → Intent Router（chat mode）
および Chat Agent 内の Ollama 呼び出し直前でも必ず実行。
無効化不可（SECURITY_GUARD_ALWAYS_ON）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .policy import (
    BLOCK_FIXED_MESSAGE,
    DEFAULT_SECURITY_POLICY,
    SECURITY_GUARD_ALWAYS_ON,
    SecurityPolicy,
)
from .rules import BlockRule, match_block_rules


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    blocked: bool
    rule_id: str | None = None
    category: str | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "blocked": self.blocked,
            "rule_id": self.rule_id,
            "category": self.category,
            "always_on": SECURITY_GUARD_ALWAYS_ON,
        }


class SecurityGuard:
    """Personal Chat Security Guard（無効化できない）。"""

    def __init__(self, policy: SecurityPolicy | None = None) -> None:
        self.policy = policy or DEFAULT_SECURITY_POLICY

    @property
    def always_on(self) -> bool:
        return True

    def check(self, message: str) -> GuardResult:
        """Ollama 呼び出し前に必ず実行する Block 判定。"""
        # 無効化不可 — policy / env で OFF にできない
        if not self.policy.is_enabled() or not SECURITY_GUARD_ALWAYS_ON:
            # 防御的: ここには来ない想定だが、来ても検査を継続する
            pass

        rule = match_block_rules(message)
        if rule is None:
            return GuardResult(allowed=True, blocked=False)

        return GuardResult(
            allowed=False,
            blocked=True,
            rule_id=rule.rule_id,
            category=rule.category,
            message=self.policy.block_message or BLOCK_FIXED_MESSAGE,
        )

    def block_response(self, *, guard: GuardResult | None = None) -> dict[str, Any]:
        """Block 時の固定応答（Ollama 非呼び出し）。"""
        g = guard or GuardResult(
            allowed=False,
            blocked=True,
            message=BLOCK_FIXED_MESSAGE,
        )
        return {
            "agent": "chat",
            "mode": "chat",
            "intent": {
                "name": "chat_blocked",
                "confidence": 1.0,
                "race_id": None,
                "slots": {"security": "blocked"},
            },
            "reply": g.message or BLOCK_FIXED_MESSAGE,
            "citations": [],
            "actions": [],
            "tools_used": [],
            "prediction_meta": None,
            "llm": {"used": False, "role": "security_guard", "ollama_called": False},
            "fallback": None,
            "blocked": True,
            "security": g.to_dict(),
            "kaoba_independent": True,
            "involves_prediction": False,
            "involves_review": False,
            "involves_explain": False,
        }
