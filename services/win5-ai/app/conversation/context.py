# -*- coding: utf-8 -*-
"""会話セッションコンテキスト — 複数ターンの race / intent / date を保持。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..data.race_resolver import RaceIdentity, RaceResolver


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


@dataclass
class ConversationContext:
    session_id: str
    turn: int = 0
    active_race_id: str | None = None
    active_core_race_id: str | None = None
    active_date: str | None = None
    last_intent: str | None = None
    last_venue: str | None = None
    last_race_no: int | None = None
    history_snippet: list[dict[str, str]] = field(default_factory=list)

    def as_meta(self) -> dict[str, Any]:
        return {
            "turn": self.turn,
            "active_race_id": self.active_race_id,
            "active_core_race_id": self.active_core_race_id,
            "active_date": self.active_date,
            "last_intent": self.last_intent,
            "last_venue": self.last_venue,
            "last_race_no": self.last_race_no,
        }

    def update_from_identity(self, identity: RaceIdentity | None) -> None:
        if not identity:
            return
        self.active_race_id = identity.public_race_id or identity.catalog_race_id
        self.active_core_race_id = identity.core_race_id
        self.active_date = identity.date
        self.last_venue = identity.venue_ja
        self.last_race_no = identity.race_no

    def date_hint(self) -> str | None:
        return self.active_date or _today_iso()


class ContextManager:
    def __init__(self, history_repo, resolver: RaceResolver | None = None) -> None:
        self.history = history_repo
        self.resolver = resolver or RaceResolver()

    def load(self, session_id: str) -> ConversationContext:
        rows = self.history.list_session(session_id, limit=20)
        ctx = ConversationContext(session_id=session_id, turn=len(rows))
        ctx.history_snippet = [
            {"role": r["role"], "content": (r.get("content") or "")[:200]}
            for r in rows[-6:]
        ]

        for row in reversed(rows):
            if row.get("role") != "assistant":
                continue
            meta_raw = row.get("meta_json")
            meta: dict[str, Any] = {}
            if isinstance(meta_raw, str) and meta_raw:
                try:
                    meta = json.loads(meta_raw)
                except json.JSONDecodeError:
                    meta = {}
            elif isinstance(meta_raw, dict):
                meta = meta_raw
            resolved = meta.get("resolved") or {}
            if resolved.get("public_race_id") or resolved.get("catalog_race_id"):
                ctx.active_race_id = resolved.get("public_race_id") or resolved.get(
                    "catalog_race_id"
                )
                ctx.active_core_race_id = resolved.get("core_race_id")
                ctx.active_date = resolved.get("date")
                ctx.last_venue = resolved.get("venue")
                ctx.last_race_no = resolved.get("race_no")
            elif row.get("race_id"):
                ctx.active_race_id = str(row["race_id"])
            if row.get("intent"):
                ctx.last_intent = str(row["intent"])
            if ctx.active_race_id:
                break

        for row in reversed(rows):
            if row.get("role") == "user" and row.get("race_id"):
                ctx.active_race_id = str(row["race_id"])
                break

        return ctx

    def resolve_with_context(
        self,
        text: str,
        ctx: ConversationContext,
        *,
        explicit_race_id: str | None = None,
    ) -> RaceIdentity | None:
        if explicit_race_id:
            return self.resolver.resolve(explicit_race_id, date_hint=ctx.date_hint())

        follow_up_markers = (
            "このレース",
            "さっき",
            "それ",
            "同じレース",
            "もう一度",
            "続き",
            "先ほど",
        )
        if any(m in text for m in follow_up_markers) and ctx.active_race_id:
            ident = self.resolver.resolve(ctx.active_race_id, date_hint=ctx.date_hint())
            if ident:
                return ident

        if ctx.last_venue and ctx.last_race_no and not self._has_race_marker(text):
            if any(k in text for k in ("理由", "穴", "買い", "本命", "予想")):
                probe = f"{ctx.date_hint()}-{ctx.last_venue}-{ctx.last_race_no}"
                ident = self.resolver.resolve(probe, date_hint=ctx.date_hint())
                if ident:
                    return ident

        date_hint = ctx.date_hint()
        if "今日" in text or "本日" in text:
            date_hint = _today_iso()

        return self.resolver.resolve(text, date_hint=date_hint)

    @staticmethod
    def _has_race_marker(text: str) -> bool:
        import re

        if re.search(r"20\d{6}_[a-z0-9]+_\d+", text.lower()):
            return True
        if re.search(r"20\d{2}-\d{2}-\d{2}", text):
            return True
        if re.search(r"(札幌|函館|福島|新潟|東京|中山|中京|京都|阪神|小倉)\s*\d{1,2}\s*R?", text):
            return True
        return False
