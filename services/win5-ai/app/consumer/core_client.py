# -*- coding: utf-8 -*-
"""Core API client — read-only (ADR-011 / V109 C1).

Decision Registry and Consumer MUST obtain Core via this client.
This module never writes Core stores and never mutates returned sources.
"""
from __future__ import annotations

from typing import Any, Mapping, Protocol

from app.consumer.core_payload import (
    CORE_SCHEMA,
    CorePayloadRef,
    core_ref_from_payload,
    freeze_payload,
    validate_minimal_core,
)


class CoreNotFoundError(KeyError):
    """race_id not available from Core provider."""


class CoreClient(Protocol):
    def get(self, race_id: str) -> dict[str, Any]:
        """Return a frozen (deep-copied) CoreRaceSemanticPayload."""
        ...


class InMemoryCoreClient:
    """Test/staging provider. Stores are never mutated by get()."""

    def __init__(self, store: Mapping[str, Mapping[str, Any]] | None = None) -> None:
        self._store: dict[str, dict[str, Any]] = {
            str(k): freeze_payload(v) for k, v in (store or {}).items()
        }

    def put_for_test(self, race_id: str, payload: Mapping[str, Any]) -> None:
        """Test helper only — replaces provider entry; does not touch PE/Core engines."""
        body = freeze_payload(payload)
        body.setdefault("schema", CORE_SCHEMA)
        body["race_id"] = str(race_id)
        self._store[str(race_id)] = body

    def get(self, race_id: str) -> dict[str, Any]:
        rid = str(race_id)
        if rid not in self._store:
            raise CoreNotFoundError(rid)
        # Always deep-copy out so callers cannot mutate the store
        return freeze_payload(self._store[rid])


def get_core_payload(client: CoreClient, race_id: str) -> tuple[dict[str, Any], CorePayloadRef, list[str]]:
    """Read-only fetch + ref + validation warnings."""
    payload = client.get(race_id)
    # Defense: ensure race_id consistency without mutating provider's original
    if str(payload.get("race_id") or "") != str(race_id):
        payload = freeze_payload(payload)
        payload["race_id"] = str(race_id)
    ref = core_ref_from_payload(payload)
    warnings = validate_minimal_core(payload)
    return payload, ref, warnings
