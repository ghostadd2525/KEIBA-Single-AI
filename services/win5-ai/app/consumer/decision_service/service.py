# -*- coding: utf-8 -*-
"""Decision Service — Composer orchestration (V109 C4).

Assembles SingleResponse from Core + Presentation + Ticket + Policy + Flags.
Not a Reasoner. Does not change Core judgment. Shadow only — no Production wiring.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from app.consumer.core_client import CoreClient, get_core_payload
from app.consumer.decision_service.composer import (
    CompositionValidationError,
    assert_no_new_meaning,
    compose,
)
from app.consumer.decision_service.dto import SingleResponseDTO
from app.consumer.flags import (
    consumer_presentation_enabled,
    consumer_single_enabled,
    consumer_ticket_enabled,
    snapshot_all_flags,
)
from app.consumer.presentation.renderer import render_presentation
from app.consumer.registry import RegistryResolution, resolve_policy
from app.consumer.ticket.market import MarketResolver, NullMarketResolver
from app.consumer.ticket.resolver import resolve_ticket


class DecisionServiceDisabledError(RuntimeError):
    """Consumer / Decision Service path disabled (Flag OFF)."""


def _policy_metadata(resolution: RegistryResolution) -> dict[str, Any]:
    return {
        "policy_id": resolution.policy_id,
        "strategy_id": resolution.strategy_id,
        "registry_versions": list(resolution.registry_versions),
        "world_id": resolution.world_id,
        "residual_class": resolution.residual_class,
        "near_world": resolution.near_world,
        "notes": list(resolution.notes),
    }


class DecisionService:
    """Composer facade. Ticket/Presentation obtained as inputs — not re-reasoned here."""

    def compose_from_parts(
        self,
        *,
        core_payload: Mapping[str, Any],
        policy_metadata: Mapping[str, Any],
        presentation: Mapping[str, Any] | None = None,
        ticket: Mapping[str, Any] | None = None,
        core_ref: Mapping[str, Any] | None = None,
        flags_snapshot: Mapping[str, Any] | None = None,
        warnings: list[str] | None = None,
        mode: str = "SHADOW",
        include_presentation: bool = True,
        include_ticket: bool = True,
    ) -> SingleResponseDTO:
        """Pure composition — does not call Ticket Resolver or Presentation Mapper."""
        return compose(
            core_payload=core_payload,
            core_ref=core_ref,
            policy_metadata=policy_metadata,
            presentation=presentation,
            ticket=ticket,
            flags_snapshot=flags_snapshot or snapshot_all_flags(),
            warnings=warnings,
            mode=mode,
            include_presentation=include_presentation,
            include_ticket=include_ticket,
        )

    def legacy_response(
        self,
        client: CoreClient,
        race_id: str,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        """Flag-OFF compatible skeleton: registry only, no presentation/ticket."""
        if not force and not consumer_single_enabled():
            raise DecisionServiceDisabledError("W_CONSUMER_SINGLE_ENABLED=false")

        payload, ref, core_warnings = get_core_payload(client, race_id)
        resolution = resolve_policy(payload)
        dto = self.compose_from_parts(
            core_payload=payload,
            core_ref={
                "schema": ref.schema,
                "race_id": ref.race_id,
                "payload_fingerprint": ref.payload_fingerprint,
            },
            policy_metadata=_policy_metadata(resolution),
            presentation=None,
            ticket=None,
            flags_snapshot=snapshot_all_flags(),
            warnings=list(core_warnings) + list(resolution.notes),
            mode="LEGACY",
            include_presentation=False,
            include_ticket=False,
        )
        out = dto.to_dict()
        assert_no_new_meaning(out)
        return out

    def shadow_assemble(
        self,
        client: CoreClient,
        race_id: str,
        *,
        force: bool = False,
        include_tickets: bool = False,
        include_presentation: bool = False,
        locale: str | None = None,
        force_presentation: bool = False,
        force_ticket: bool = False,
        market: MarketResolver | None = None,
        # Optional pre-built parts — if provided, Composer will not rebuild them
        presentation: Mapping[str, Any] | None = None,
        ticket: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Shadow orchestration: obtain parts then Compose.

        When presentation/ticket args are supplied, they are embedded as-is
        (no recalculation). Otherwise C2/C3 may be invoked once as input providers.
        """
        if not force and not consumer_single_enabled():
            raise DecisionServiceDisabledError("W_CONSUMER_SINGLE_ENABLED=false")

        payload, ref, core_warnings = get_core_payload(client, race_id)
        core_snapshot = copy.deepcopy(payload)
        resolution = resolve_policy(payload)
        policy_meta = _policy_metadata(resolution)
        warnings = list(core_warnings)
        warnings.extend(resolution.notes)

        presentation_allowed = (
            force_presentation or force or consumer_presentation_enabled()
        )
        ticket_allowed = force_ticket or force or consumer_ticket_enabled()

        pres: dict[str, Any] | None = None
        if include_presentation:
            if presentation is not None:
                # Use provided DTO — do not recalculate
                pres = copy.deepcopy(dict(presentation))
            elif presentation_allowed:
                bundle = render_presentation(payload, locale=locale)
                pres = bundle.to_dict()
                warnings.extend(bundle.warnings)
            else:
                warnings.append("presentation_flag_off")

        tkt: dict[str, Any] | None = None
        if include_tickets:
            if ticket is not None:
                tkt = copy.deepcopy(dict(ticket))
            elif ticket_allowed:
                plan = resolve_ticket(
                    resolution.policy_id,
                    race_id=race_id,
                    prediction=payload.get("prediction")
                    if isinstance(payload.get("prediction"), Mapping)
                    else None,
                    market=market or NullMarketResolver(),
                )
                tkt = plan.to_dict()
                warnings.extend(plan.warnings)
            else:
                warnings.append("ticket_flag_off")

        dto = self.compose_from_parts(
            core_payload=payload,
            core_ref={
                "schema": ref.schema,
                "race_id": ref.race_id,
                "payload_fingerprint": ref.payload_fingerprint,
            },
            policy_metadata=policy_meta,
            presentation=pres,
            ticket=tkt,
            flags_snapshot=snapshot_all_flags(),
            warnings=warnings,
            mode="SHADOW",
            include_presentation=include_presentation and pres is not None,
            include_ticket=include_tickets and tkt is not None,
        )

        # Immutability of source core store snapshot vs response echo
        out = dto.to_dict()
        assert_no_new_meaning(out)
        if out["core_payload"] != core_snapshot:
            # compose deep-copied; equality to pre-compose snapshot required
            raise CompositionValidationError("core_payload_echo_mismatch")
        return out


def consumer_dict_from_single_response(resp: Mapping[str, Any]) -> dict[str, Any]:
    """Map SingleResponse → consumer-api/single/v1 shape (backward compatible fields)."""
    return {
        "schema": "consumer-api/single/v1",
        "core_ref": resp.get("core_ref"),
        "registry": resp.get("registry"),
        "ticket": resp.get("ticket"),
        "presentation": resp.get("presentation"),
        "flags_snapshot": resp.get("flags_snapshot"),
        "warnings": list(resp.get("warnings") or []),
        "selectors": resp.get("selectors") or {},
        # C4 extras (non-breaking additions for Shadow)
        "single_response_schema": resp.get("schema"),
        "version": resp.get("version"),
        "core_payload": resp.get("core_payload"),
        "policy_metadata": resp.get("policy_metadata"),
        "mode": resp.get("mode"),
        "natural_explanation": None,
        "decision_reason": None,
    }
