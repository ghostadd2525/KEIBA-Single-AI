# -*- coding: utf-8 -*-
"""Read-only Core Race Semantic Payload (Platform v1).

MUST NOT mutate Core. Consumer copies fields for fingerprinting only.
Schema: core-semantic-payload/v1 (ADR-011 / V103).
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

CORE_SCHEMA = "core-semantic-payload/v1"


@dataclass(frozen=True)
class CorePayloadRef:
    schema: str
    race_id: str
    payload_fingerprint: str


def _canonical(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return {str(k): _canonical(obj[k]) for k in sorted(obj.keys(), key=str)}
    if isinstance(obj, (list, tuple)):
        return [_canonical(x) for x in obj]
    return obj


def fingerprint_payload(payload: Mapping[str, Any]) -> str:
    """Stable hash over a deep copy view — never writes back to source."""
    blob = json.dumps(_canonical(dict(payload)), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def freeze_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deep copy. Caller must treat as immutable; source is untouched."""
    return copy.deepcopy(dict(payload))


def validate_minimal_core(payload: Mapping[str, Any]) -> list[str]:
    """Return list of contract warnings (non-fatal for skeleton)."""
    warnings: list[str] = []
    if not payload.get("race_id"):
        warnings.append("missing_race_id")
    if payload.get("world_id") is None:
        warnings.append("missing_world_id")
    pred = payload.get("prediction")
    if pred is not None and not isinstance(pred, Mapping):
        warnings.append("prediction_not_object")
    return warnings


def core_ref_from_payload(payload: Mapping[str, Any]) -> CorePayloadRef:
    race_id = str(payload.get("race_id") or "")
    return CorePayloadRef(
        schema=str(payload.get("schema") or CORE_SCHEMA),
        race_id=race_id,
        payload_fingerprint=fingerprint_payload(payload),
    )
