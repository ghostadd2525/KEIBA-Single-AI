# -*- coding: utf-8 -*-
"""POST /v1/prediction-runs の fail-closed 検査。frontend 切替はしない。

既定: PREDICTION_RUNS_ENABLED=0。route 先頭で停止する。
PRODUCTION_EXPOSURE_READY は CORS * のあいだ False。
"""
from __future__ import annotations

import os
import re
import threading
import time
from typing import Any

from ..data.db import prediction_run_schema_ready

SITE_CORPUS_ACCUMULATION_ACTIVE = False
PRODUCTION_EXPOSURE_READY = False

ERROR_SCHEMA_NOT_READY = "PREDICTION_RUN_SCHEMA_NOT_READY"
ERROR_PREDICTION_RUNS_DISABLED = "PREDICTION_RUNS_DISABLED"
ERROR_UNEXPECTED_BODY_KEYS = "UNEXPECTED_BODY_KEYS"
ERROR_INVALID_RACE_ID_FORMAT = "INVALID_RACE_ID_FORMAT"
ERROR_RACE_NOT_FOUND = "RACE_NOT_FOUND"
ERROR_RACE_DATE_NOT_ALLOWED = "RACE_DATE_NOT_ALLOWED"
ERROR_ALLOWLIST_REQUIRED = "PREDICTION_RUN_ALLOWLIST_REQUIRED"
ERROR_AUTH_REQUIRED = "PREDICTION_RUN_AUTH_REQUIRED"
ERROR_RATE_LIMITED = "PREDICTION_RUN_RATE_LIMITED"
ERROR_BODY_TOO_LARGE = "PREDICTION_RUN_BODY_TOO_LARGE"

ALLOWED_POST_BODY_KEYS = frozenset({"race_id"})
RACE_ID_PUBLIC = re.compile(r"^\d{8}_[a-z0-9]+_\d{1,2}$")
RACE_ID_CORE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}$")

DEFAULT_BODY_LIMIT_BYTES = 4096
DEFAULT_RATE_LIMIT = 10
DEFAULT_RATE_WINDOW_SEC = 60.0

_rate_hits: dict[str, list[float]] = {}
_rate_lock = threading.Lock()


class SchemaNotReadyError(RuntimeError):
    pass


class PredictionRunsDisabledError(RuntimeError):
    code = ERROR_PREDICTION_RUNS_DISABLED


class RaceGuardError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def prediction_runs_enabled() -> bool:
    return (os.environ.get("PREDICTION_RUNS_ENABLED") or "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def require_prediction_runs_enabled() -> None:
    if not prediction_runs_enabled():
        raise PredictionRunsDisabledError("PREDICTION_RUNS_ENABLED is not 1")


def prediction_run_body_limit_bytes() -> int:
    raw = (os.environ.get("PREDICTION_RUN_MAX_BODY_BYTES") or "").strip()
    if not raw:
        return DEFAULT_BODY_LIMIT_BYTES
    try:
        n = int(raw)
    except ValueError:
        return DEFAULT_BODY_LIMIT_BYTES
    return n if n > 0 else DEFAULT_BODY_LIMIT_BYTES


def prediction_run_allowed_dates() -> set[str]:
    raw = (os.environ.get("PREDICTION_RUN_ALLOWED_DATES") or "").strip()
    return {part.strip() for part in raw.split(",") if part.strip()}


def prediction_run_expected_key() -> str:
    return (
        (os.environ.get("PREDICTION_RUN_API_KEY") or "").strip()
        or (os.environ.get("AI_API_KEY") or "").strip()
    )


def verify_prediction_run_auth(headers: Any) -> None:
    expected = prediction_run_expected_key()
    if not expected:
        raise RaceGuardError(
            ERROR_AUTH_REQUIRED,
            "PREDICTION_RUN_API_KEY or AI_API_KEY must be set when POST is enabled",
        )
    getter = getattr(headers, "get", None)
    raw = getter("X-Prediction-Run-Key") if getter else None
    if not raw and getter:
        raw = getter("X-AI-Key")
    if str(raw or "") != expected:
        raise RaceGuardError(ERROR_AUTH_REQUIRED, "prediction run authentication failed")


def _rate_window_and_limit() -> tuple[int, float]:
    limit_raw = (os.environ.get("PREDICTION_RUN_RATE_LIMIT") or "").strip()
    try:
        limit = int(limit_raw) if limit_raw else DEFAULT_RATE_LIMIT
    except ValueError:
        limit = DEFAULT_RATE_LIMIT
    window_raw = (os.environ.get("PREDICTION_RUN_RATE_WINDOW_SEC") or "").strip()
    try:
        window = float(window_raw) if window_raw else DEFAULT_RATE_WINDOW_SEC
    except ValueError:
        window = DEFAULT_RATE_WINDOW_SEC
    return max(1, limit), window


def _sweep_rate_hits(now: float, window: float) -> None:
    stale: list[str] = []
    for key, hits in _rate_hits.items():
        kept = [t for t in hits if now - t < window]
        if kept:
            _rate_hits[key] = kept
        else:
            stale.append(key)
    for key in stale:
        _rate_hits.pop(key, None)


def check_prediction_run_rate_limit(identity: str) -> None:
    limit, window = _rate_window_and_limit()
    with _rate_lock:
        now = time.monotonic()
        _sweep_rate_hits(now, window)
        hits = list(_rate_hits.get(identity, []))
        if len(hits) >= limit:
            raise RaceGuardError(ERROR_RATE_LIMITED, "prediction run rate limit exceeded")
        hits.append(now)
        _rate_hits[identity] = hits


def reset_prediction_run_rate_limit() -> None:
    with _rate_lock:
        _rate_hits.clear()


def parse_prediction_run_content_length(raw: Any) -> int | None:
    """欠落・不正・負数は None。上限迂回のための unbounded read を禁止する。"""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        n = int(text)
    except (TypeError, ValueError):
        return None
    if n < 0:
        return None
    return n


def public_post_exposure() -> dict[str, Any]:
    """設計: 有効化時も allowlist / 認証 / rate limit / body 上限が必須。CORS * のあいだ READY=NO。"""
    api_key_set = bool(prediction_run_expected_key())
    return {
        "PREDICTION_RUNS_ENABLED": prediction_runs_enabled(),
        "ai_api_key_enforced": api_key_set,
        "allowlist_required": True,
        "auth_required": True,
        "origin_restriction": False,
        "cors_allow_origin": "*",
        "rate_limit": True,
        "body_limit_bytes": prediction_run_body_limit_bytes(),
        "PRODUCTION_EXPOSURE_READY": False,
        "SITE_CORPUS_ACCUMULATION_ACTIVE": SITE_CORPUS_ACCUMULATION_ACTIVE,
        "note": "default PREDICTION_RUNS_ENABLED=0; route stops before infer",
    }


def require_prediction_run_schema() -> None:
    if not prediction_run_schema_ready():
        raise SchemaNotReadyError("prediction run columns or unique index are not applied")


def validate_post_body_keys(body: dict[str, Any]) -> None:
    extra = sorted(set(body) - ALLOWED_POST_BODY_KEYS)
    if extra:
        raise RaceGuardError(
            ERROR_UNEXPECTED_BODY_KEYS,
            "only race_id is allowed, unexpected keys: %s" % ",".join(extra),
        )


def validate_race_id_format(race_id: str) -> None:
    if RACE_ID_PUBLIC.match(race_id) or RACE_ID_CORE.match(race_id):
        return
    raise RaceGuardError(ERROR_INVALID_RACE_ID_FORMAT, "race_id format is not accepted")


def _catalog_race(race_id: str) -> dict[str, Any] | None:
    try:
        from ..engine import data as engine_data

        for row in (engine_data.load_races() or {}).get("races") or []:
            if not isinstance(row, dict):
                continue
            if str(row.get("race_id") or "") == race_id:
                return row
            if str(row.get("core_race_id") or "") == race_id:
                return row
            if str(row.get("public_race_id") or "") == race_id:
                return row
    except Exception:
        return None
    return None


def resolve_existing_race(race_id: str) -> dict[str, Any]:
    ident = None
    try:
        from ..data.race_resolver import resolve_identity

        ident = resolve_identity(race_id)
    except Exception:
        ident = None
    row = None
    if ident is not None:
        row = ident.race_row
    if not row:
        try:
            from ..data.repository import RaceRepository

            row = RaceRepository().get(race_id)
        except Exception:
            row = None
    if not row:
        row = _catalog_race(race_id)
    if not row:
        raise RaceGuardError(ERROR_RACE_NOT_FOUND, "race_id is not an existing race")
    return dict(row)


def validate_race_date(row: dict[str, Any]) -> str:
    raw = str(row.get("date") or row.get("race_date") or "").strip()
    if not raw and str(row.get("race_id") or "").startswith("20"):
        rid = str(row["race_id"])
        if len(rid) >= 8 and rid[:8].isdigit():
            raw = "%s-%s-%s" % (rid[:4], rid[4:6], rid[6:8])
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        raise RaceGuardError(ERROR_RACE_DATE_NOT_ALLOWED, "race date is missing or invalid")
    dates = prediction_run_allowed_dates()
    if not dates:
        raise RaceGuardError(
            ERROR_ALLOWLIST_REQUIRED,
            "PREDICTION_RUN_ALLOWED_DATES must be set when POST is enabled",
        )
    if raw not in dates:
        raise RaceGuardError(ERROR_RACE_DATE_NOT_ALLOWED, "race date is outside the allowed set")
    return raw


def guard_prediction_run_request(body: dict[str, Any]) -> dict[str, Any]:
    """enabled 済み前提。schema → body keys → race_id 形式 → 存在 → 必須 allowlist。"""
    require_prediction_run_schema()
    if not isinstance(body, dict):
        raise RaceGuardError(ERROR_UNEXPECTED_BODY_KEYS, "body_not_object")
    validate_post_body_keys(body)
    race_id = str(body.get("race_id") or "").strip()
    if not race_id:
        raise RaceGuardError(ERROR_INVALID_RACE_ID_FORMAT, "race_id_required")
    validate_race_id_format(race_id)
    row = resolve_existing_race(race_id)
    date = validate_race_date(row)
    return {"race_id": race_id, "race": row, "race_date": date}
