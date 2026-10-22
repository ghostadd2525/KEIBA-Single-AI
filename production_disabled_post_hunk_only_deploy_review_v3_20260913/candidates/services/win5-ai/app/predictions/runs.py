# -*- coding: utf-8 -*-
"""POST /v1/prediction-runs orchestrator. GET 経路は使わない。"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ..data.race_resolver import resolve_identity
from ..data.repository import PredictionRepository
from ..engine.adapters import prediction_adapter
from .feature_pin import FeatureLoadFailed, pin_feature_load
from .guards import (
    ERROR_AUTH_REQUIRED,
    ERROR_ALLOWLIST_REQUIRED,
    ERROR_BODY_TOO_LARGE,
    ERROR_INVALID_RACE_ID_FORMAT,
    ERROR_PREDICTION_RUNS_DISABLED,
    ERROR_RACE_DATE_NOT_ALLOWED,
    ERROR_RACE_NOT_FOUND,
    ERROR_RATE_LIMITED,
    ERROR_SCHEMA_NOT_READY,
    ERROR_UNEXPECTED_BODY_KEYS,
    PredictionRunsDisabledError,
    RaceGuardError,
    SchemaNotReadyError,
    guard_prediction_run_request,
    require_prediction_run_schema,
    require_prediction_runs_enabled,
)
from .provenance import (
    ERROR_CLIENT_BUNDLE_REJECTED,
    ERROR_IDEMPOTENCY_CONTENT_CONFLICT,
    ClientBundleRejected,
    IdempotencyConflictError,
    build_response_envelope,
    compute_idempotency_key,
    declared_model_version,
    intended_engine_source,
    resolve_engine_build_fingerprint,
    stamp_persist_provenance,
    stamp_server_persist_source,
    training_auto_adopt,
    validate_post_request,
)
from .snapshot import (
    attach_prediction_time_features_fail_open,
    canonical_feature_load_object,
    compute_input_snapshot_hash,
    compute_prediction_semantic_hash,
    observations_from_feature_frame,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ConfirmedInputs:
    race_id: str
    core_race_id: str | None
    feature_result: Any
    race_obs: dict[str, Any]
    runner_obs: dict[str, dict[str, Any]]
    captured_at: str
    input_payload: dict[str, Any]
    input_snapshot_hash: str


def confirm_prediction_inputs(race_id: str) -> ConfirmedInputs:
    """入力を一度だけ確定する。この object を hash / infer / snapshot が共有する。"""
    captured_at = _now()
    ident = resolve_identity(race_id)
    core_id = None
    race_row = None
    if ident:
        core_id = ident.core_race_id
        race_row = ident.race_row
    if race_row is None:
        try:
            from ..data.repository import RaceRepository

            race_row = RaceRepository().get(race_id) or (RaceRepository().get(str(core_id)) if core_id else None)
        except Exception:
            race_row = None
    feature_result = None
    try:
        from ai_platform.core.features.feature_loader import FeatureLoader

        loader = FeatureLoader()
        load_id = str(core_id or race_id)
        feature_result = loader.load(load_id)
    except FeatureLoadFailed:
        raise
    except Exception as exc:
        raise FeatureLoadFailed("feature loader failed: %s" % type(exc).__name__) from exc
    if feature_result is None:
        raise FeatureLoadFailed("feature loader returned no result")
    # persist POST はここで入力を確定する。以降の FeatureLoader.load は再取得禁止。
    frozen = feature_result
    try:
        frozen = type(feature_result)(
            frame=feature_result.frame.copy(deep=True),
            feature_source=feature_result.feature_source,
            metadata=dict(feature_result.metadata or {}),
        )
    except Exception:
        frozen = feature_result
    race_obs, runner_obs = observations_from_feature_frame(frozen, race_row)
    input_payload = canonical_feature_load_object(
        frozen,
        race_id=str(race_id),
        core_race_id=str(core_id) if core_id else None,
        race_row=race_row if isinstance(race_row, dict) else None,
    )
    return ConfirmedInputs(
        race_id=str(race_id),
        core_race_id=str(core_id) if core_id else None,
        feature_result=frozen,
        race_obs=race_obs,
        runner_obs=runner_obs,
        captured_at=captured_at,
        input_payload=input_payload,
        input_snapshot_hash=compute_input_snapshot_hash(input_payload),
    )


def _replay_envelope(found: dict[str, Any], *, key: str, persist_source: str) -> dict[str, Any]:
    bundle = found.get("bundle") or {}
    snap = bundle.get("prediction_time_features") if isinstance(bundle, dict) else None
    prov = bundle.get("persist_provenance") if isinstance(bundle.get("persist_provenance"), dict) else {}
    eligible = training_auto_adopt(
        persist_source=found.get("persist_source") or persist_source,
        engine_source=found.get("engine_source"),
        fallback_reason=found.get("fallback_reason"),
        snapshot=snap if isinstance(snap, dict) else None,
        fingerprint_status=prov.get("fingerprint_status"),
        model_version=found.get("model_version"),
    )
    return build_response_envelope(
        prediction_id=int(found["id"]),
        idempotency_key=key,
        persist_source=persist_source,
        bundle=bundle,
        replayed=True,
        training_eligible=eligible,
    )


def execute_prediction_run(payload: dict[str, Any]) -> dict[str, Any]:
    require_prediction_runs_enabled()
    require_prediction_run_schema()
    errors = validate_post_request(payload)
    if ERROR_CLIENT_BUNDLE_REJECTED in errors:
        raise ClientBundleRejected("client must not send bundle, bundle_json, or prediction_time_features")
    if errors:
        raise ValueError(",".join(errors))
    guarded = guard_prediction_run_request(payload)

    race_id = str(guarded["race_id"])
    persist_source = stamp_server_persist_source()
    confirmed = confirm_prediction_inputs(race_id)
    fingerprint = resolve_engine_build_fingerprint()
    intended = intended_engine_source()
    model_version = declared_model_version(intended)
    repo = PredictionRepository()

    def make_key(engine_source: str) -> str:
        return compute_idempotency_key(
            race_id=race_id,
            engine_source=engine_source,
            persist_source=persist_source,
            model_version=model_version,
            engine_build_fingerprint=str(fingerprint["engine_build_fingerprint"]),
            input_snapshot_hash=confirmed.input_snapshot_hash,
        )

    key = make_key(intended)
    existing = repo.lookup_by_idempotency_key(key)
    if existing:
        return _replay_envelope(existing, key=key, persist_source=persist_source)

    with pin_feature_load(
        confirmed.feature_result,
        core_race_id=str(confirmed.core_race_id or confirmed.race_id),
    ):
        bundle, meta = prediction_adapter.get_with_meta(race_id)
        if not bundle:
            raise LookupError("PredictionBundle not found")
        stored = attach_prediction_time_features_fail_open(
            copy.deepcopy(bundle),
            prediction_created_at=confirmed.captured_at,
            race_obs=confirmed.race_obs,
            runner_obs=confirmed.runner_obs,
            input_snapshot_hash=confirmed.input_snapshot_hash,
        )
        meta = meta or {}
        actual_source = str(meta.get("engine_source") or intended)
        fallback_reason = meta.get("fallback_reason")
        stored = stamp_persist_provenance(
            stored,
            persist_source=persist_source,
            engine_source=actual_source,
            fallback_reason=fallback_reason,
            engine_build_fingerprint=str(fingerprint["engine_build_fingerprint"]),
            fingerprint_status=str(fingerprint["fingerprint_status"]),
            model_version=model_version,
        )
        semantic = compute_prediction_semantic_hash(stored)
        if actual_source != intended:
            key = make_key(actual_source)
            existing = repo.lookup_by_idempotency_key(key)
            if existing:
                return _replay_envelope(existing, key=key, persist_source=persist_source)
        result = repo.save_idempotent(
            race_id=race_id,
            bundle=stored,
            engine_source=actual_source,
            fallback_reason=fallback_reason,
            core_race_id=confirmed.core_race_id or meta.get("core_race_id"),
            model_version=model_version,
            idempotency_key=key,
            persist_source=persist_source,
            input_snapshot_hash=confirmed.input_snapshot_hash,
            prediction_semantic_hash=semantic,
        )
        eligible = training_auto_adopt(
            persist_source=persist_source,
            engine_source=actual_source,
            fallback_reason=fallback_reason,
            snapshot=stored.get("prediction_time_features") if isinstance(stored.get("prediction_time_features"), dict) else None,
            fingerprint_status=str(fingerprint["fingerprint_status"]),
            model_version=model_version,
        )
        return build_response_envelope(
            prediction_id=result.prediction_id,
            idempotency_key=key,
            persist_source=persist_source,
            bundle=result.bundle,
            replayed=result.replayed,
            training_eligible=eligible,
        )


def _ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data}


def _err(code: str, message: str, status: int = 400) -> tuple[int, dict[str, Any]]:
    return status, {"ok": False, "error": {"code": code, "message": message, "details": None}}


def handle_post_prediction_run(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    try:
        envelope = execute_prediction_run(payload)
        return 200, _ok(envelope)
    except PredictionRunsDisabledError as exc:
        return _err(ERROR_PREDICTION_RUNS_DISABLED, str(exc), 503)
    except FeatureLoadFailed as exc:
        return _err(exc.code, str(exc), 503)
    except SchemaNotReadyError as exc:
        return _err(ERROR_SCHEMA_NOT_READY, str(exc), 503)
    except ClientBundleRejected as exc:
        return _err(ERROR_CLIENT_BUNDLE_REJECTED, str(exc), 400)
    except RaceGuardError as exc:
        status = 404 if exc.code == ERROR_RACE_NOT_FOUND else 400
        if exc.code == ERROR_RACE_DATE_NOT_ALLOWED:
            status = 400
        if exc.code in (
            ERROR_UNEXPECTED_BODY_KEYS,
            ERROR_INVALID_RACE_ID_FORMAT,
            ERROR_ALLOWLIST_REQUIRED,
        ):
            status = 400
        if exc.code in (ERROR_AUTH_REQUIRED,):
            status = 401
        if exc.code == ERROR_RATE_LIMITED:
            status = 429
        if exc.code == ERROR_BODY_TOO_LARGE:
            status = 413
        return _err(exc.code, str(exc), status)
    except IdempotencyConflictError as exc:
        return _err(ERROR_IDEMPOTENCY_CONTENT_CONFLICT, str(exc), 409)
    except LookupError as exc:
        return _err("NOT_FOUND", str(exc), 404)
    except ValueError as exc:
        return _err("BAD_REQUEST", str(exc), 400)
    except Exception as exc:
        return _err("PREDICTION_RUN_FAILED", str(exc), 500)
