# -*- coding: utf-8 -*-
"""Collector Validator — C-1 race_meta / C-4 entries_core."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .contracts import entries_core as entries_core_contract
from .contracts import odds as odds_contract
from .contracts import race_meta as race_meta_contract
from .contracts import track as track_contract


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: list[dict[str, str]] = field(default_factory=list)


def validate_race_meta(*, http_ok: bool, body: bytes | str) -> ValidationResult:
    """Minimal Validator for STATIC_CORE / race_meta."""
    return _validate_simple(
        http_ok=http_ok,
        body=body,
        required=race_meta_contract.REQUIRED_FIELDS,
        array_fields=race_meta_contract.ARRAY_FIELDS,
    )


def validate_odds(*, http_ok: bool, body: bytes | str) -> ValidationResult:
    """Minimal Validator for DYNAMIC / odds."""
    return _validate_simple(
        http_ok=http_ok,
        body=body,
        required=odds_contract.REQUIRED_FIELDS,
        array_fields=odds_contract.ARRAY_FIELDS,
    )


def validate_track(*, http_ok: bool, body: bytes | str) -> ValidationResult:
    """Minimal Validator for DYNAMIC / track."""
    return _validate_simple(
        http_ok=http_ok,
        body=body,
        required=track_contract.REQUIRED_FIELDS,
        array_fields=track_contract.ARRAY_FIELDS,
    )


def validate_entries_core(*, http_ok: bool, body: bytes | str) -> ValidationResult:
    """
    Minimal Validator for STATIC_CORE / entries_core.

    Checks: HTTP success, required fields, NULL, empty arrays.
    Entry fields: horse_number, frame, horse_name, jockey, weight.
    """
    errors: list[dict[str, str]] = []

    if not http_ok:
        errors.append({"code": "http_error", "field": "*"})
        return ValidationResult(ok=False, errors=errors)

    payload, parse_errors = _parse_object(body)
    if parse_errors:
        return ValidationResult(ok=False, errors=parse_errors)

    assert payload is not None
    _check_required_fields(payload, entries_core_contract.REQUIRED_FIELDS, errors)
    _check_null_fields(payload, entries_core_contract.REQUIRED_FIELDS, errors)
    _check_empty_arrays(payload, entries_core_contract.ARRAY_FIELDS, errors)

    entries = payload.get("entries")
    if isinstance(entries, list) and entries:
        for idx, entry in enumerate(entries):
            prefix = f"entries[{idx}]"
            if not isinstance(entry, dict):
                errors.append({"code": "invalid_shape", "field": prefix})
                continue
            for field_name in entries_core_contract.ENTRY_REQUIRED_FIELDS:
                path = f"{prefix}.{field_name}"
                if field_name not in entry:
                    errors.append({"code": "required_missing", "field": path})
                elif entry[field_name] is None:
                    errors.append({"code": "required_null", "field": path})

    return ValidationResult(ok=len(errors) == 0, errors=errors)


def _validate_simple(
    *,
    http_ok: bool,
    body: bytes | str,
    required: tuple[str, ...],
    array_fields: tuple[str, ...],
) -> ValidationResult:
    errors: list[dict[str, str]] = []
    if not http_ok:
        errors.append({"code": "http_error", "field": "*"})
        return ValidationResult(ok=False, errors=errors)
    payload, parse_errors = _parse_object(body)
    if parse_errors:
        return ValidationResult(ok=False, errors=parse_errors)
    assert payload is not None
    _check_required_fields(payload, required, errors)
    _check_null_fields(payload, required, errors)
    _check_empty_arrays(payload, array_fields, errors)
    return ValidationResult(ok=len(errors) == 0, errors=errors)


def _parse_object(body: bytes | str) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    text = body.decode("utf-8") if isinstance(body, bytes) else body
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None, [{"code": "invalid_json", "field": "*"}]
    if not isinstance(payload, dict):
        return None, [{"code": "invalid_shape", "field": "*"}]
    return payload, []


def _check_required_fields(
    payload: dict[str, Any],
    required: tuple[str, ...],
    errors: list[dict[str, str]],
) -> None:
    for field_name in required:
        if field_name not in payload:
            errors.append({"code": "required_missing", "field": field_name})


def _check_null_fields(
    payload: dict[str, Any],
    required: tuple[str, ...],
    errors: list[dict[str, str]],
) -> None:
    for field_name in required:
        if field_name in payload and payload[field_name] is None:
            errors.append({"code": "required_null", "field": field_name})


def _check_empty_arrays(
    payload: dict[str, Any],
    array_fields: tuple[str, ...],
    errors: list[dict[str, str]],
) -> None:
    for field_name in array_fields:
        if field_name in payload and payload[field_name] == []:
            errors.append({"code": "empty_array", "field": field_name})
