# -*- coding: utf-8 -*-
"""Single Response DTO — Decision Service Composer output (V109 C4).

Embeds Core / Presentation / Ticket without mutating them.
No Reasoning / Natural Explanation / Decision Reason.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SINGLE_RESPONSE_SCHEMA = "single-response/v1"
PLATFORM_CONTRACT = "PLATFORM-V1-CONTRACT"
COMPOSER_VERSION = "decision-service-composer/v1"


@dataclass(frozen=True)
class VersionInfo:
    single_response_schema: str = SINGLE_RESPONSE_SCHEMA
    consumer_api_schema: str = "consumer-api/single/v1"
    core_schema: str = "core-semantic-payload/v1"
    platform_contract: str = PLATFORM_CONTRACT
    composer: str = COMPOSER_VERSION
    parents: tuple[str, ...] = (
        "ADR-009",
        "ADR-010",
        "ADR-011",
        "C1",
        "C2",
        "C3",
    )


@dataclass(frozen=True)
class SingleResponseDTO:
    """Final Single AI response — composed, not reasoned."""

    schema: str
    version: dict[str, Any]
    core_ref: dict[str, Any]
    # Exact deep copy of Core Payload for audit (read-only echo)
    core_payload: dict[str, Any]
    registry: dict[str, Any]
    policy_metadata: dict[str, Any]
    presentation: dict[str, Any] | None
    ticket: dict[str, Any] | None
    flags_snapshot: dict[str, Any]
    warnings: tuple[str, ...] = field(default_factory=tuple)
    selectors: dict[str, Any] = field(default_factory=dict)
    mode: str = "SHADOW"  # SHADOW | LEGACY — Production wiring forbidden in C4
    # Forbidden outputs — always null
    natural_explanation: None = None
    decision_reason: None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["natural_explanation"] = None
        d["decision_reason"] = None
        return d


def version_info_dict() -> dict[str, Any]:
    v = VersionInfo()
    return {
        "single_response_schema": v.single_response_schema,
        "consumer_api_schema": v.consumer_api_schema,
        "core_schema": v.core_schema,
        "platform_contract": v.platform_contract,
        "composer": v.composer,
        "parents": list(v.parents),
    }
