# -*- coding: utf-8 -*-
"""A1 Request validation — Application layer only."""
from __future__ import annotations

from typing import Any, Mapping


class RequestValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_single_response_request(body: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate POST /v1/single/response body. Does not mutate Core semantics."""
    if body is None or not isinstance(body, dict):
        raise RequestValidationError("BAD_REQUEST", "JSON object required")

    core = body.get("core_payload")
    if not isinstance(core, dict):
        raise RequestValidationError("BAD_REQUEST", "core_payload object required")
    race_id = core.get("race_id") or body.get("race_id")
    if not race_id or not str(race_id).strip():
        raise RequestValidationError("BAD_REQUEST", "race_id required on core_payload or body")
    if core.get("schema") and not isinstance(core.get("schema"), str):
        raise RequestValidationError("BAD_REQUEST", "core_payload.schema must be string")

    options = body.get("options") or {}
    if options is not None and not isinstance(options, dict):
        raise RequestValidationError("BAD_REQUEST", "options must be object")

    include_tickets = bool(options.get("include_tickets", False))
    include_presentation = bool(options.get("include_presentation", False))
    locale = options.get("locale")
    if locale is not None and not isinstance(locale, str):
        raise RequestValidationError("BAD_REQUEST", "options.locale must be string")

    # force is Application/Shadow harness only — never a Production default
    force = bool(body.get("force", False))

    return {
        "race_id": str(race_id).strip(),
        "core_payload": dict(core),
        "include_tickets": include_tickets,
        "include_presentation": include_presentation,
        "locale": str(locale).strip() if locale else None,
        "force": force,
    }
