# -*- coding: utf-8 -*-
"""Composer — assemble SingleResponse from pre-built parts (V109 C4).

MUST NOT recalculate Ticket, mutate Core, generate Reason / NL, or invent Semantic.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from app.consumer.core_payload import CORE_SCHEMA, fingerprint_payload
from app.consumer.decision_service.dto import (
    SINGLE_RESPONSE_SCHEMA,
    SingleResponseDTO,
    version_info_dict,
)

# Fields Decision Service must never invent as new semantic meaning
_FORBIDDEN_NEW_MEANING_KEYS = frozenset(
    {
        "natural_explanation",
        "decision_reason",
        "reason",
        "why",
        "inferred_world",
        "rewritten_ranks",
        "adjusted_scores",
        "new_affinity",
        "derived_ec",
    }
)


class CompositionValidationError(ValueError):
    """Payload validation failed — Composer refuses to invent fixes."""


def _deep(obj: Any) -> Any:
    return copy.deepcopy(obj)


def validate_parts(
    *,
    core_payload: Mapping[str, Any],
    presentation: Mapping[str, Any] | None,
    ticket: Mapping[str, Any] | None,
    policy_metadata: Mapping[str, Any],
) -> list[str]:
    """Validate inputs. Does not repair or invent meaning."""
    warnings: list[str] = []
    if not core_payload.get("race_id"):
        raise CompositionValidationError("core_missing_race_id")
    if core_payload.get("world_id") is None:
        warnings.append("core_missing_world_id")

    if presentation is not None:
        if presentation.get("natural_explanation") is not None:
            raise CompositionValidationError("presentation_has_natural_explanation")
        for k in _FORBIDDEN_NEW_MEANING_KEYS:
            if k == "natural_explanation":
                continue
            if presentation.get(k) is not None:
                raise CompositionValidationError(f"presentation_forbidden_key:{k}")

    if ticket is not None:
        if ticket.get("reason") is not None:
            raise CompositionValidationError("ticket_has_reason")
        pid = policy_metadata.get("policy_id")
        if pid is not None and ticket.get("policy_id") is not None and ticket.get("policy_id") != pid:
            raise CompositionValidationError("ticket_policy_id_mismatch")

    return warnings


def compose(
    *,
    core_payload: Mapping[str, Any],
    core_ref: Mapping[str, Any] | None = None,
    policy_metadata: Mapping[str, Any],
    presentation: Mapping[str, Any] | None = None,
    ticket: Mapping[str, Any] | None = None,
    flags_snapshot: Mapping[str, Any] | None = None,
    warnings: list[str] | tuple[str, ...] | None = None,
    mode: str = "SHADOW",
    include_presentation: bool = True,
    include_ticket: bool = True,
) -> SingleResponseDTO:
    """Compose SingleResponseDTO from parts.

    Deep-copies all inputs. Never mutates callers' objects.
    Never recalculates Ticket / Presentation.
    """
    core_copy = _deep(dict(core_payload))
    pres_copy = _deep(dict(presentation)) if presentation is not None else None
    ticket_copy = _deep(dict(ticket)) if ticket is not None else None
    policy_copy = _deep(dict(policy_metadata))
    flags_copy = _deep(dict(flags_snapshot or {}))

    extra = validate_parts(
        core_payload=core_copy,
        presentation=pres_copy,
        ticket=ticket_copy,
        policy_metadata=policy_copy,
    )

    # Flag application: omit sections without recalculating them
    if not include_presentation:
        pres_copy = None
    if not include_ticket:
        ticket_copy = None

    fp = fingerprint_payload(core_copy)
    ref = _deep(dict(core_ref)) if core_ref else {
        "schema": str(core_copy.get("schema") or CORE_SCHEMA),
        "race_id": str(core_copy.get("race_id") or ""),
        "payload_fingerprint": fp,
    }
    # Ensure fingerprint matches embedded core
    if ref.get("payload_fingerprint") and ref["payload_fingerprint"] != fp:
        raise CompositionValidationError("core_fingerprint_mismatch")
    ref["payload_fingerprint"] = fp

    registry = {
        "policy_id": policy_copy.get("policy_id"),
        "strategy_id": policy_copy.get("strategy_id"),
        "registry_versions": list(policy_copy.get("registry_versions") or []),
        "world_id": policy_copy.get("world_id"),
        "residual_class": policy_copy.get("residual_class"),
        "near_world": policy_copy.get("near_world"),
    }

    warn_list = list(warnings or [])
    warn_list.extend(extra)

    selectors = {
        "world_id": registry.get("world_id"),
        "residual_class": registry.get("residual_class"),
        "near_world": registry.get("near_world"),
    }

    return SingleResponseDTO(
        schema=SINGLE_RESPONSE_SCHEMA,
        version=version_info_dict(),
        core_ref=ref,
        core_payload=core_copy,
        registry=registry,
        policy_metadata=policy_copy,
        presentation=pres_copy,
        ticket=ticket_copy,
        flags_snapshot=flags_copy,
        warnings=tuple(warn_list),
        selectors=selectors,
        mode=mode,
        natural_explanation=None,
        decision_reason=None,
    )


def assert_no_new_meaning(response: Mapping[str, Any]) -> None:
    """Fail if Composer invented forbidden semantic keys at top level."""
    for k in _FORBIDDEN_NEW_MEANING_KEYS:
        if k in ("natural_explanation", "decision_reason"):
            if response.get(k) is not None:
                raise AssertionError(f"forbidden_non_null:{k}")
            continue
        if k in response and response[k] is not None:
            raise AssertionError(f"forbidden_key_present:{k}")
