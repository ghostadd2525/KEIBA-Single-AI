# -*- coding: utf-8 -*-
"""I1 Request validation for site-facing Single calls."""
from __future__ import annotations

from typing import Any, Mapping

from app.site_integration.race_id import RaceIdError, normalize_race_id, parse_race_id_meta


class SiteValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_site_single_request(
    body: Mapping[str, Any] | None,
    *,
    path_race_id: str | None = None,
    default_timeout_ms: int = 12000,
    max_timeout_ms: int = 30000,
) -> dict[str, Any]:
    """Validate site → Single request. Requires race_id + core_payload (I1)."""
    if body is None or not isinstance(body, dict):
        # GET path may pass empty body with path_race_id only
        body = {}

    try:
        race_id = normalize_race_id(body.get("race_id") or path_race_id)
    except RaceIdError as e:
        raise SiteValidationError(e.code, e.message) from e

    core = body.get("core_payload")
    if core is None:
        raise SiteValidationError(
            "CORE_PAYLOAD_REQUIRED",
            "core_payload required until Core PROMOTE Gate; "
            "Site Integration does not invent Core (read-only Single path)",
        )
    if not isinstance(core, dict):
        raise SiteValidationError("BAD_REQUEST", "core_payload must be object")

    # Align race_id on payload copy without mutating caller's Core semantics store
    core_out = dict(core)
    if not core_out.get("race_id"):
        core_out["race_id"] = race_id
    elif str(core_out.get("race_id")).strip() != race_id:
        raise SiteValidationError(
            "RACE_ID_MISMATCH",
            "body.race_id / path race_id must match core_payload.race_id",
        )

    options = body.get("options") or {}
    if options is not None and not isinstance(options, dict):
        raise SiteValidationError("BAD_REQUEST", "options must be object")

    timeout_ms = body.get("timeout_ms", default_timeout_ms)
    try:
        timeout_ms = int(timeout_ms)
    except (TypeError, ValueError) as e:
        raise SiteValidationError("BAD_REQUEST", "timeout_ms must be int") from e
    if timeout_ms < 100 or timeout_ms > max_timeout_ms:
        raise SiteValidationError(
            "BAD_REQUEST",
            f"timeout_ms must be between 100 and {max_timeout_ms}",
        )

    locale = options.get("locale")
    if locale is not None and not isinstance(locale, str):
        raise SiteValidationError("BAD_REQUEST", "options.locale must be string")

    return {
        "race_id": race_id,
        "race_meta": parse_race_id_meta(race_id),
        "core_payload": core_out,
        "include_tickets": bool(options.get("include_tickets", False)),
        "include_presentation": bool(options.get("include_presentation", False)),
        "locale": str(locale).strip() if locale else None,
        "force": bool(body.get("force", False)),
        "timeout_ms": timeout_ms,
    }
