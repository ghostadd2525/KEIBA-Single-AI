"""
KaobaAdapter (Python)

契約: expect-kaoba/1.0（変更禁止）
現行: domains.kaoba_reply（rule）
移行: LlmKaobaSource.generate を実装し KAOBA_PROVIDER=llm で切替
"""
from __future__ import annotations

import os
from typing import Any

from .. import domains
from .analysis_adapter import get_analysis
from .prediction_adapter import get_bundle


class RuleKaobaSource:
    """現行ルールエンジン。"""

    def generate(self, body: dict[str, Any]) -> dict[str, Any]:
        payload = dict(body if isinstance(body, dict) else {})
        race_id = str(payload.get("race_id") or "")
        if not race_id:
            ctx = payload.get("context") if isinstance(payload.get("context"), dict) else {}
            race_id = str(ctx.get("bundle_ref") or "")
            if race_id:
                payload["race_id"] = race_id
        if race_id and "_bundle" not in payload:
            try:
                bundle = get_bundle(race_id)
                if isinstance(bundle, dict) and bundle:
                    payload["_bundle"] = bundle
            except Exception:
                pass
        return domains.kaoba_reply(payload)


class LlmKaobaSource:
    """
    LLM 用プレースホルダ。
    実装時: body + optional bundle/analysis context → KaobaChatResponse。
    未実装時は rule へフォールバック。
    """

    def __init__(self, fallback: RuleKaobaSource | None = None) -> None:
        self._fallback = fallback or RuleKaobaSource()

    def generate(self, body: dict[str, Any]) -> dict[str, Any]:
        # TODO: call LLM with refs from get_bundle / get_analysis
        race_id = str((body or {}).get("race_id") or "")
        if race_id:
            _ = get_bundle(race_id)
            _ = get_analysis(race_id)
        out = self._fallback.generate(body)
        out = dict(out)
        out["provider"] = "rule-fallback"
        return out


def _provider() -> str:
    return (os.environ.get("KAOBA_PROVIDER") or "rule").lower()


class KaobaAdapter:
    def __init__(self) -> None:
        rule = RuleKaobaSource()
        mode = _provider()
        self._source = LlmKaobaSource(rule) if mode in ("llm", "python", "auto") else rule

    def generate(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._source.generate(body)


_adapter = KaobaAdapter()


def generate_reply(body: dict[str, Any]) -> dict[str, Any]:
    """公開入口 — main.py はこれを呼ぶ（domains.kaoba_reply 直呼びをやめる）。"""
    return _adapter.generate(body)
