# -*- coding: utf-8 -*-
"""Single AI Consumer API (V109 C1–C4 / ADR-011).

Delegates final assembly to Decision Service Composer (C4).
Shadow only — Production wiring forbidden.
"""
from __future__ import annotations

from typing import Any, Mapping

from app.consumer.core_client import CoreClient
from app.consumer.decision_service.service import (
    DecisionService,
    DecisionServiceDisabledError,
    consumer_dict_from_single_response,
)
from app.consumer.ticket.market import MarketResolver

CONSUMER_SCHEMA = "consumer-api/single/v1"


class ConsumerDisabledError(RuntimeError):
    """W_CONSUMER_SINGLE_ENABLED is OFF."""


_SERVICE = DecisionService()


def build_single_response(
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
    presentation: Mapping[str, Any] | None = None,
    ticket: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble ConsumerSingleResponse via Decision Service Composer.

    When presentation/ticket provided, they are embedded without recalculation.
    """
    try:
        if (
            not include_tickets
            and not include_presentation
            and presentation is None
            and ticket is None
        ):
            # Legacy-compatible skeleton
            raw = _SERVICE.legacy_response(client, race_id, force=force)
        else:
            raw = _SERVICE.shadow_assemble(
                client,
                race_id,
                force=force,
                include_tickets=include_tickets,
                include_presentation=include_presentation,
                locale=locale,
                force_presentation=force_presentation,
                force_ticket=force_ticket,
                market=market,
                presentation=presentation,
                ticket=ticket,
            )
    except DecisionServiceDisabledError as e:
        raise ConsumerDisabledError(str(e)) from e

    return consumer_dict_from_single_response(raw)


def assert_core_untouched(
    original: Mapping[str, Any],
    after: Mapping[str, Any],
) -> None:
    """Test helper: deep equality of Core snapshots."""
    import json

    a = json.dumps(original, sort_keys=True, default=str)
    b = json.dumps(after, sort_keys=True, default=str)
    if a != b:
        raise AssertionError("Core payload was mutated")
