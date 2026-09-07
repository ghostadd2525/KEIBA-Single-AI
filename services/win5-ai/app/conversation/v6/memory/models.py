# -*- coding: utf-8 -*-
"""Memory data models — Long-term only（History と型を共有しない）."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


ALLOWED_CATEGORIES = frozenset(
    {
        "nickname",
        "address_form",
        "favorite_venue",
        "favorite_jockey",
        "favorite_horse",
        "explain_style",
        "answer_length",
        "conversation_settings",
        "user_explicit",
    }
)


@dataclass
class MemoryRecord:
    """永続化された 1 件の長期 Memory。"""

    memory_id: str
    user_id: str
    category: str
    key: str
    value: str
    source_text: str
    consent: bool
    created_at: str
    updated_at: str
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        user_id: str,
        category: str,
        key: str,
        value: str,
        source_text: str,
        consent: bool,
        meta: dict[str, Any] | None = None,
    ) -> "MemoryRecord":
        now = _utc_now()
        return cls(
            memory_id=str(uuid4()),
            user_id=str(user_id),
            category=category,
            key=key,
            value=value,
            source_text=source_text,
            consent=bool(consent),
            created_at=now,
            updated_at=now,
            meta=dict(meta or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "MemoryRecord":
        return cls(
            memory_id=str(raw.get("memory_id") or uuid4()),
            user_id=str(raw.get("user_id") or ""),
            category=str(raw.get("category") or "user_explicit"),
            key=str(raw.get("key") or ""),
            value=str(raw.get("value") or ""),
            source_text=str(raw.get("source_text") or ""),
            consent=bool(raw.get("consent")),
            created_at=str(raw.get("created_at") or _utc_now()),
            updated_at=str(raw.get("updated_at") or _utc_now()),
            meta=dict(raw.get("meta") or {}),
        )


@dataclass
class MemoryCandidate:
    """Consent 前の候補。Store には入れない。"""

    user_id: str
    category: str
    key: str
    value: str
    source_text: str
    consent_detected: bool
    rejected_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
