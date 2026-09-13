# -*- coding: utf-8 -*-
"""Persist provenance, fingerprint, idempotency key, response envelope."""
from __future__ import annotations

import copy
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .snapshot import (
    FEATURE_SNAPSHOT_SCHEMA_VERSION,
    PREDICTION_CONTRACT_VERSION,
    sha256_hex,
)

PERSIST_SOURCE_SITE_PREDICTION_RUN = "site_prediction_run"
PERSIST_SOURCE_CONVERSATION_CHAT = "conversation_chat"
PERSIST_SOURCE_CHALLENGE_CACHE = "challenge_cache"
PERSIST_SOURCE_RA_CACHE = "ra_cache"
PERSIST_SOURCE_SITE_DISPLAY = "site_display"
PERSIST_SOURCE_MOCK_FALLBACK = "mock_fallback"

ERROR_IDEMPOTENCY_CONTENT_CONFLICT = "IDEMPOTENCY_CONTENT_CONFLICT"
ERROR_CLIENT_BUNDLE_REJECTED = "CLIENT_BUNDLE_REJECTED"

IDEMPOTENCY_KEY_FIELDS = (
    "race_id",
    "engine_source",
    "persist_source",
    "model_version",
    "engine_build_fingerprint",
    "input_snapshot_hash",
    "prediction_contract_version",
    "feature_snapshot_schema_version",
)
WEAK_MODEL_VERSIONS = frozenset(
    {
        "",
        "core-delegated",
        "list-projection",
        "unknown",
        "unspecified",
    }
)
TRAINING_AUTO_ADOPT_SOURCES = frozenset({PERSIST_SOURCE_SITE_PREDICTION_RUN})
TRAINING_EXCLUDED_SOURCES = frozenset(
    {
        PERSIST_SOURCE_CHALLENGE_CACHE,
        PERSIST_SOURCE_RA_CACHE,
        PERSIST_SOURCE_CONVERSATION_CHAT,
        PERSIST_SOURCE_SITE_DISPLAY,
        PERSIST_SOURCE_MOCK_FALLBACK,
    }
)
CLIENT_FORBIDDEN_BODY_KEYS = ("bundle", "bundle_json", "prediction_time_features")


class ClientBundleRejected(ValueError):
    pass


class IdempotencyConflictError(Exception):
    def __init__(self, message: str, *, prediction_id: int, idempotency_key: str) -> None:
        super().__init__(message)
        self.prediction_id = prediction_id
        self.idempotency_key = idempotency_key


@dataclass(frozen=True)
class IdempotentSaveResult:
    prediction_id: int
    replayed: bool
    persist_source: str
    idempotency_key: str
    prediction_semantic_hash: str
    bundle: dict[str, Any]


def validate_post_request(body: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    if not isinstance(body, dict):
        return ["body_not_object"]
    if any(k in body for k in CLIENT_FORBIDDEN_BODY_KEYS):
        errors.append(ERROR_CLIENT_BUNDLE_REJECTED)
    if not str(body.get("race_id") or "").strip():
        errors.append("race_id_required")
    persist_source = body.get("persist_source")
    if persist_source is not None and persist_source != PERSIST_SOURCE_SITE_PREDICTION_RUN:
        errors.append("persist_source_must_be_site_prediction_run")
    return errors


def stamp_server_persist_source() -> str:
    return PERSIST_SOURCE_SITE_PREDICTION_RUN


def intended_engine_source() -> str:
    raw = (os.environ.get("AI_ENGINE") or "mock").lower()
    return "real_ai" if raw == "real" else "mock"


def declared_model_version(engine_source: str) -> str:
    explicit = (os.environ.get("PREDICTION_MODEL_VERSION") or "").strip()
    if explicit:
        return explicit
    if engine_source == "real_ai":
        return "core-delegated"
    return "dummy-model-0.0.0"


def _file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _product_version() -> str:
    try:
        from ai_platform.single import PRODUCT_VERSION

        return str(PRODUCT_VERSION or "").strip()
    except Exception:
        return ""


def _core_facade_version() -> str:
    try:
        from ai_platform.core.facade.core_facade import CORE_FACADE_VERSION

        return str(CORE_FACADE_VERSION or "").strip()
    except Exception:
        return ""


def resolve_engine_build_fingerprint() -> dict[str, Any]:
    artifact = ""
    model_path: Path | None = None
    try:
        from ai_platform.core.scoring.model_registry import ModelRegistry

        model_path = ModelRegistry.resolve_model_path()
        artifact = _file_sha256(model_path) or ""
    except Exception:
        env_path = (os.environ.get("CORE_MODEL_PATH") or "").strip()
        if env_path:
            model_path = Path(env_path)
            artifact = _file_sha256(model_path) or ""
    code_ver = _core_facade_version()
    product_ver = _product_version()
    config = {
        "CORE_SOFTMAX_TEMP_BASE": os.environ.get("CORE_SOFTMAX_TEMP_BASE") or "1.0",
        "CORE_SOFTMAX_TEMP_SLOPE": os.environ.get("CORE_SOFTMAX_TEMP_SLOPE") or "0.04",
        "CORE_SOFTMAX_FIELD_THRESHOLD": os.environ.get("CORE_SOFTMAX_FIELD_THRESHOLD") or "12",
        "WIN5_CE_V2_ENABLED": os.environ.get("WIN5_CE_V2_ENABLED") or "",
        "CE_V2_A_TEMP": os.environ.get("CE_V2_A_TEMP") or "",
        "CORE_MODEL_PATH_PRESENT": bool(model_path is not None and model_path.is_file()),
        "CORE_MODEL_BASENAME": model_path.name if model_path is not None else None,
    }
    missing: list[str] = []
    if len(artifact) != 64 or any(c not in "0123456789abcdef" for c in artifact):
        missing.append("model_artifact_sha256")
    if not code_ver or code_ver in WEAK_MODEL_VERSIONS:
        missing.append("inference_code_version")
    if not product_ver or product_ver in WEAK_MODEL_VERSIONS:
        missing.append("product_version")
    material = {
        "model_artifact_sha256": artifact or None,
        "inference_code_version": {
            "core_facade_version": code_ver or None,
            "product_version": product_ver or None,
            "scorer_module": "ai_platform.core.scoring.Scorer",
            "mapper_module": "single_prediction_mapper.prediction_response_to_bundle",
        },
        "config_version": config,
        "prediction_contract_version": PREDICTION_CONTRACT_VERSION,
        "feature_snapshot_schema_version": FEATURE_SNAPSHOT_SCHEMA_VERSION,
    }
    return {
        "engine_build_fingerprint": sha256_hex(material),
        "fingerprint_status": "determined" if not missing else "undetermined",
        "missing": missing,
        "material": material,
    }


def compute_idempotency_key(
    *,
    race_id: str,
    engine_source: str,
    persist_source: str,
    model_version: str,
    engine_build_fingerprint: str,
    input_snapshot_hash: str,
    prediction_contract_version: str = PREDICTION_CONTRACT_VERSION,
    feature_snapshot_schema_version: str = FEATURE_SNAPSHOT_SCHEMA_VERSION,
) -> str:
    payload = {
        "race_id": str(race_id or "").strip(),
        "engine_source": str(engine_source or "").strip(),
        "persist_source": str(persist_source or "").strip(),
        "model_version": str(model_version or "").strip(),
        "engine_build_fingerprint": str(engine_build_fingerprint or "").strip(),
        "input_snapshot_hash": str(input_snapshot_hash or "").strip(),
        "prediction_contract_version": str(prediction_contract_version or "").strip(),
        "feature_snapshot_schema_version": str(feature_snapshot_schema_version or "").strip(),
    }
    if set(payload) != set(IDEMPOTENCY_KEY_FIELDS):
        raise ValueError("idempotency_key_field_mismatch")
    if any(not payload[k] for k in IDEMPOTENCY_KEY_FIELDS):
        raise ValueError("idempotency_key_incomplete")
    return sha256_hex(payload)


def training_auto_adopt(
    *,
    persist_source: str | None,
    engine_source: str | None,
    fallback_reason: str | None,
    snapshot: dict[str, Any] | None,
    fingerprint_status: str | None,
    model_version: str | None = None,
) -> bool:
    if persist_source != PERSIST_SOURCE_SITE_PREDICTION_RUN:
        return False
    if persist_source in TRAINING_EXCLUDED_SOURCES:
        return False
    if str(engine_source or "") != "real_ai":
        return False
    if fallback_reason:
        return False
    if not snapshot or snapshot.get("capture_status") != "complete":
        return False
    if snapshot.get("training_coverage") != "complete":
        return False
    if fingerprint_status != "determined":
        return False
    _ = model_version
    return True


def stamp_persist_provenance(
    bundle: dict[str, Any],
    *,
    persist_source: str,
    engine_source: str,
    fallback_reason: str | None,
    engine_build_fingerprint: str,
    fingerprint_status: str,
    model_version: str | None = None,
) -> dict[str, Any]:
    out = copy.deepcopy(bundle)
    out.pop("prediction_id", None)
    snap = out.get("prediction_time_features") if isinstance(out.get("prediction_time_features"), dict) else None
    eligible = training_auto_adopt(
        persist_source=persist_source,
        engine_source=engine_source,
        fallback_reason=fallback_reason,
        snapshot=snap,
        fingerprint_status=fingerprint_status,
        model_version=model_version,
    )
    out["persist_provenance"] = {
        "persist_source": persist_source,
        "engine_source": engine_source,
        "fallback_reason": fallback_reason,
        "engine_build_fingerprint": engine_build_fingerprint,
        "fingerprint_status": fingerprint_status,
        "prediction_contract_version": PREDICTION_CONTRACT_VERSION,
        "feature_snapshot_schema_version": FEATURE_SNAPSHOT_SCHEMA_VERSION,
        "training_eligible": eligible,
    }
    return out


def build_response_envelope(
    *,
    prediction_id: int,
    idempotency_key: str,
    persist_source: str,
    bundle: dict[str, Any],
    replayed: bool,
    training_eligible: bool,
) -> dict[str, Any]:
    stored = copy.deepcopy(bundle)
    stored.pop("prediction_id", None)
    if "prediction_id" in stored:
        raise RuntimeError("prediction_id_in_bundle_json_forbidden")
    return {
        "prediction_id": int(prediction_id),
        "idempotency_key": idempotency_key,
        "persist_source": persist_source,
        "replayed": bool(replayed),
        "training_eligible": bool(training_eligible),
        "bundle": stored,
    }
