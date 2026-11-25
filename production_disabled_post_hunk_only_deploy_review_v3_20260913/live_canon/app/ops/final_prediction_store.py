# -*- coding: utf-8 -*-
"""
Persistent Final PredictionStore (race_id scoped, shared across users).

Serving contract (when AI_PRED_PERSISTENT_STORE=1):
  C1 memory → final_predictions lookup → inflight/semaphore → inference → persist → C1.

Does not alter ranking / scores / marks / authority / Feature / model selection.
Existing append-only `predictions` table is intentionally not reused.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

logger = logging.getLogger(__name__)

AUTHORITY_CONTRACT_VERSION = "1"
DEFAULT_SCHEMA_VERSION = "single-prediction-bundle/2.0"

# Race-day freeze policy (serving contract constants)
PERSIST_BEFORE_POST_TIME = True
REGENERATE_ON_FEATURE_CHANGE = True
FREEZE_AT_POST_TIME = True
ALLOW_POST_RACE_REINFERENCE = False

FingerprintResolver = Callable[[str], str | None]
PostTimeResolver = Callable[[str], datetime | None]
ConnectFn = Callable[[], sqlite3.Connection]


def _env_flag(key: str, default: str = "0") -> bool:
    return (os.environ.get(key) or default).strip().lower() in ("1", "true", "yes")


def persistent_store_enabled() -> bool:
    """Feature flag — OFF restores pre-persistent serving contract."""
    return _env_flag("AI_PRED_PERSISTENT_STORE", "0")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def compute_input_fingerprint(
    *,
    race_id: str,
    feature_fingerprint: str,
    model_fingerprint: str,
    authority: str,
    schema_version: str = DEFAULT_SCHEMA_VERSION,
    authority_contract_version: str = AUTHORITY_CONTRACT_VERSION,
) -> str:
    """Stable hash of semantic inputs that justify regenerating a Final."""
    payload = "|".join(
        [
            str(race_id or "").strip(),
            str(feature_fingerprint or "").strip(),
            str(model_fingerprint or "").strip(),
            str(authority or "").strip(),
            str(schema_version or "").strip(),
            str(authority_contract_version or "").strip(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def extract_fingerprint_parts(
    race_id: str,
    bundle: Mapping[str, Any] | None,
    meta: Mapping[str, Any] | None,
) -> dict[str, str]:
    """Derive fingerprint parts from Final Bundle/meta without regenerating Features."""
    b = bundle or {}
    m = meta or {}
    authority = str(
        b.get("decision_authority")
        or m.get("decision_authority")
        or ""
    ).strip()
    model_fp = str(
        m.get("model_fingerprint")
        or b.get("model_fingerprint")
        or m.get("model_sha256")
        or b.get("model_sha256")
        or b.get("model_version")
        or m.get("model_version")
        or ""
    ).strip()
    feature_fp = str(
        m.get("feature_fingerprint")
        or b.get("feature_fingerprint")
        or m.get("feature_artifact_hash")
        or b.get("feature_artifact_hash")
        or m.get("feature_generated_at")
        or b.get("feature_generated_at")
        or m.get("feature_lookup_key")
        or b.get("feature_lookup_key")
        or b.get("feature_source")
        or m.get("feature_source")
        or ""
    ).strip()
    schema_version = str(
        b.get("schema_version") or m.get("schema_version") or DEFAULT_SCHEMA_VERSION
    ).strip()
    return {
        "race_id": str(race_id or b.get("race_id") or "").strip(),
        "feature_fingerprint": feature_fp,
        "model_fingerprint": model_fp,
        "authority": authority,
        "schema_version": schema_version,
        "authority_contract_version": AUTHORITY_CONTRACT_VERSION,
    }


def fingerprint_from_bundle_meta(
    race_id: str,
    bundle: Mapping[str, Any] | None,
    meta: Mapping[str, Any] | None,
) -> str:
    parts = extract_fingerprint_parts(race_id, bundle, meta)
    return compute_input_fingerprint(**parts)


def runner_count(bundle: Mapping[str, Any] | None) -> int:
    if not isinstance(bundle, dict):
        return 0
    ev = bundle.get("evaluation")
    if isinstance(ev, dict):
        runners = ev.get("runners")
        if isinstance(runners, list):
            return len(runners)
    runners = bundle.get("runners")
    if isinstance(runners, list):
        return len(runners)
    return 0


def is_persistable_final(
    bundle: Mapping[str, Any] | None,
    meta: Mapping[str, Any] | None,
) -> bool:
    """Only real_ai Final bundles with runners may be persisted."""
    if not isinstance(bundle, dict):
        return False
    m = meta or {}
    eng = str(m.get("engine_source") or bundle.get("engine_source") or "").strip()
    if eng != "real_ai":
        return False
    if eng in ("mock_fallback", "mock", "prediction_unavailable"):
        return False
    if bundle.get("prediction_available") is False:
        return False
    if bundle.get("status") == "unavailable":
        return False
    if m.get("is_mock") or bundle.get("is_mock"):
        return False
    reason = str(
        bundle.get("fallback_reason") or m.get("fallback_reason") or ""
    ).strip()
    if reason in (
        "mock_fallback",
        "race_not_found",
        "feature_not_ready",
        "history_not_ready",
        "input_not_ready",
        "inference_error",
    ):
        return False
    model = str(bundle.get("model_version") or m.get("model_version") or "").lower()
    if "dummy" in model:
        return False
    if runner_count(bundle) <= 0:
        return False
    rid = str(bundle.get("race_id") or "").strip()
    if not rid:
        return False
    authority = str(
        bundle.get("decision_authority") or m.get("decision_authority") or ""
    ).strip()
    if authority not in ("CURRENT_PATH", "RESTORED_V2"):
        return False
    if bundle.get("status") != "ok":
        return False
    return True


def is_bundle_schema_valid(bundle: Mapping[str, Any] | None) -> bool:
    if not isinstance(bundle, dict):
        return False
    if not str(bundle.get("race_id") or "").strip():
        return False
    if runner_count(bundle) <= 0:
        return False
    if not str(bundle.get("decision_authority") or "").strip():
        return False
    return True


@dataclass
class FinalPredictionRecord:
    race_id: str
    bundle: dict[str, Any]
    meta: dict[str, Any]
    input_fingerprint: str
    decision_authority: str
    engine_source: str
    model_version: str | None
    schema_version: str
    frozen_at: str | None
    created_at: str
    updated_at: str


class FinalPredictionStore:
    """SQLite-backed Final Prediction persistence (race_id PRIMARY KEY)."""

    def __init__(
        self,
        *,
        connect: ConnectFn | None = None,
        fingerprint_resolver: FingerprintResolver | None = None,
        post_time_resolver: PostTimeResolver | None = None,
        ensure_schema: bool = True,
    ) -> None:
        self._connect = connect or self._default_connect
        self._fingerprint_resolver = fingerprint_resolver
        self._post_time_resolver = post_time_resolver
        self._lock = threading.RLock()
        self.persistent_hits = 0
        self.persistent_misses = 0
        self.persistent_writes = 0
        self.persistent_invalidations = 0
        self.persistent_errors = 0
        if ensure_schema:
            try:
                self.ensure_schema()
            except Exception as exc:  # noqa: BLE001 — fail closed later
                self.persistent_errors += 1
                logger.warning("final_prediction_store schema ensure failed: %s", exc)

    @staticmethod
    def _default_connect() -> sqlite3.Connection:
        from app.data.db import connect

        return connect()

    def ensure_schema(self) -> None:
        """Idempotent table create (also covered by migration 019)."""
        ddl = """
        CREATE TABLE IF NOT EXISTS final_predictions (
          race_id TEXT PRIMARY KEY,
          source_race_id TEXT,
          core_race_id TEXT,
          bundle_json TEXT NOT NULL,
          decision_authority TEXT NOT NULL,
          engine_source TEXT NOT NULL,
          model_version TEXT,
          product_version TEXT,
          core_version TEXT,
          input_fingerprint TEXT NOT NULL,
          feature_fingerprint TEXT,
          model_fingerprint TEXT,
          schema_version TEXT NOT NULL,
          authority_contract_version TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          frozen_at TEXT
        );
        """
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(ddl)
                conn.commit()
            finally:
                conn.close()

    def reset_metrics(self) -> None:
        with self._lock:
            self.persistent_hits = 0
            self.persistent_misses = 0
            self.persistent_writes = 0
            self.persistent_invalidations = 0
            self.persistent_errors = 0

    def metrics(self) -> dict[str, int]:
        with self._lock:
            return {
                "persistent_hits": self.persistent_hits,
                "persistent_misses": self.persistent_misses,
                "persistent_writes": self.persistent_writes,
                "persistent_invalidations": self.persistent_invalidations,
                "persistent_errors": self.persistent_errors,
            }

    def resolve_current_fingerprint(self, race_id: str) -> str | None:
        """Cheap current fingerprint. None = unknown (do not force Feature regen)."""
        if self._fingerprint_resolver is not None:
            try:
                return self._fingerprint_resolver(race_id)
            except Exception as exc:  # noqa: BLE001
                self.persistent_errors += 1
                logger.warning("fingerprint resolver failed race_id=%s: %s", race_id, exc)
                return None
        return None

    def _is_frozen(self, row_frozen_at: str | None, race_id: str, now: datetime) -> bool:
        if row_frozen_at:
            return True
        if not FREEZE_AT_POST_TIME or self._post_time_resolver is None:
            return False
        try:
            post = self._post_time_resolver(race_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("post_time resolver failed race_id=%s: %s", race_id, exc)
            return False
        if post is None:
            return False
        if post.tzinfo is None:
            post = post.replace(tzinfo=timezone.utc)
        return now >= post

    def get_valid(
        self,
        race_id: str,
        *,
        now: datetime | None = None,
    ) -> FinalPredictionRecord | None:
        """Lookup Final; return None on miss / corrupt / stale fingerprint / errors."""
        rid = str(race_id or "").strip()
        if not rid:
            return None
        now = now or datetime.now(timezone.utc)
        try:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM final_predictions WHERE race_id = ?",
                    (rid,),
                ).fetchone()
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001 — fail closed to inference
            with self._lock:
                self.persistent_errors += 1
                self.persistent_misses += 1
            logger.warning("final_predictions read failed race_id=%s: %s", rid, exc)
            return None

        if row is None:
            with self._lock:
                self.persistent_misses += 1
            return None

        try:
            row_d = dict(row)
            bundle = json.loads(row_d["bundle_json"])
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self.persistent_errors += 1
                self.persistent_invalidations += 1
                self.persistent_misses += 1
            logger.warning("corrupt final_predictions race_id=%s: %s", rid, exc)
            return None

        if not is_bundle_schema_valid(bundle):
            with self._lock:
                self.persistent_invalidations += 1
                self.persistent_misses += 1
            return None

        meta = {
            "service": "PredictionService",
            "adapter": "PredictionAdapter",
            "engine_source": row_d.get("engine_source") or "real_ai",
            "decision_authority": row_d.get("decision_authority"),
            "model_version": row_d.get("model_version"),
            "product_version": row_d.get("product_version"),
            "core_version": row_d.get("core_version"),
            "feature_fingerprint": row_d.get("feature_fingerprint"),
            "model_fingerprint": row_d.get("model_fingerprint"),
            "schema_version": row_d.get("schema_version"),
            "prediction_source": "persistent_store",
            "input_fingerprint": row_d.get("input_fingerprint"),
            "source_race_id": row_d.get("source_race_id"),
            "core_race_id": row_d.get("core_race_id"),
        }

        frozen = self._is_frozen(row_d.get("frozen_at"), rid, now)
        if frozen and not ALLOW_POST_RACE_REINFERENCE:
            # Still reject corrupt / non-persistable shapes
            if not is_persistable_final(bundle, meta):
                with self._lock:
                    self.persistent_invalidations += 1
                    self.persistent_misses += 1
                return None
            with self._lock:
                self.persistent_hits += 1
            return FinalPredictionRecord(
                race_id=rid,
                bundle=bundle,
                meta=meta,
                input_fingerprint=str(row_d.get("input_fingerprint") or ""),
                decision_authority=str(row_d.get("decision_authority") or ""),
                engine_source=str(row_d.get("engine_source") or ""),
                model_version=row_d.get("model_version"),
                schema_version=str(row_d.get("schema_version") or DEFAULT_SCHEMA_VERSION),
                frozen_at=row_d.get("frozen_at"),
                created_at=str(row_d.get("created_at") or ""),
                updated_at=str(row_d.get("updated_at") or ""),
            )

        stored_fp = str(row_d.get("input_fingerprint") or "")
        current_fp = self.resolve_current_fingerprint(rid)
        if current_fp is not None and current_fp != stored_fp:
            if REGENERATE_ON_FEATURE_CHANGE:
                with self._lock:
                    self.persistent_invalidations += 1
                    self.persistent_misses += 1
                return None

        if not is_persistable_final(bundle, meta):
            with self._lock:
                self.persistent_invalidations += 1
                self.persistent_misses += 1
            return None

        with self._lock:
            self.persistent_hits += 1
        return FinalPredictionRecord(
            race_id=rid,
            bundle=bundle,
            meta=meta,
            input_fingerprint=stored_fp,
            decision_authority=str(row_d.get("decision_authority") or ""),
            engine_source=str(row_d.get("engine_source") or ""),
            model_version=row_d.get("model_version"),
            schema_version=str(row_d.get("schema_version") or DEFAULT_SCHEMA_VERSION),
            frozen_at=row_d.get("frozen_at"),
            created_at=str(row_d.get("created_at") or ""),
            updated_at=str(row_d.get("updated_at") or ""),
        )

    def put_final(
        self,
        race_id: str,
        bundle: Mapping[str, Any],
        meta: Mapping[str, Any] | None,
        *,
        input_fingerprint: str | None = None,
        frozen_at: str | None = None,
        now: datetime | None = None,
    ) -> bool:
        """Upsert Final Bundle. Returns False on skip / write failure (never raises)."""
        rid = str(race_id or "").strip()
        if not rid or not is_persistable_final(bundle, meta):
            return False
        now = now or datetime.now(timezone.utc)
        parts = extract_fingerprint_parts(rid, bundle, meta)
        fp = input_fingerprint or compute_input_fingerprint(**parts)
        ts = _utc_now_iso()
        m = meta or {}

        # Auto-freeze: explicit frozen_at, post_time_resolver, or bundle race_info.post_time
        auto_frozen = frozen_at
        if auto_frozen is None and FREEZE_AT_POST_TIME:
            post = None
            if self._post_time_resolver:
                try:
                    post = self._post_time_resolver(rid)
                except Exception:  # noqa: BLE001
                    post = None
            if post is None:
                ri = bundle.get("race_info") if isinstance(bundle, Mapping) else None
                raw_pt = None
                if isinstance(ri, Mapping):
                    raw_pt = ri.get("post_time") or ri.get("start_time")
                raw_pt = raw_pt or (m.get("post_time") if isinstance(m, Mapping) else None)
                if raw_pt:
                    try:
                        if isinstance(raw_pt, datetime):
                            post = raw_pt
                        else:
                            s = str(raw_pt).strip().replace("Z", "+00:00")
                            post = datetime.fromisoformat(s)
                    except Exception:  # noqa: BLE001
                        post = None
            if post is not None:
                if post.tzinfo is None:
                    post = post.replace(tzinfo=timezone.utc)
                if now >= post:
                    auto_frozen = ts

        payload = {
            "race_id": rid,
            "source_race_id": str(
                m.get("source_race_id") or bundle.get("source_race_id") or rid
            ),
            "core_race_id": str(
                m.get("core_race_id") or bundle.get("core_race_id") or ""
            )
            or None,
            "bundle_json": json.dumps(dict(bundle), ensure_ascii=False, separators=(",", ":")),
            "decision_authority": parts["authority"],
            "engine_source": str(m.get("engine_source") or "real_ai"),
            "model_version": str(
                bundle.get("model_version") or m.get("model_version") or ""
            )
            or None,
            "product_version": str(
                m.get("product_version") or bundle.get("product_version") or ""
            )
            or None,
            "core_version": str(m.get("core_version") or bundle.get("core_version") or "")
            or None,
            "input_fingerprint": fp,
            "feature_fingerprint": parts["feature_fingerprint"] or None,
            "model_fingerprint": parts["model_fingerprint"] or None,
            "schema_version": parts["schema_version"],
            "authority_contract_version": AUTHORITY_CONTRACT_VERSION,
            "created_at": ts,
            "updated_at": ts,
            "frozen_at": auto_frozen,
        }

        sql = """
        INSERT INTO final_predictions (
          race_id, source_race_id, core_race_id, bundle_json,
          decision_authority, engine_source, model_version,
          product_version, core_version, input_fingerprint,
          feature_fingerprint, model_fingerprint, schema_version,
          authority_contract_version, created_at, updated_at, frozen_at
        ) VALUES (
          :race_id, :source_race_id, :core_race_id, :bundle_json,
          :decision_authority, :engine_source, :model_version,
          :product_version, :core_version, :input_fingerprint,
          :feature_fingerprint, :model_fingerprint, :schema_version,
          :authority_contract_version, :created_at, :updated_at, :frozen_at
        )
        ON CONFLICT(race_id) DO UPDATE SET
          source_race_id=excluded.source_race_id,
          core_race_id=excluded.core_race_id,
          bundle_json=excluded.bundle_json,
          decision_authority=excluded.decision_authority,
          engine_source=excluded.engine_source,
          model_version=excluded.model_version,
          product_version=excluded.product_version,
          core_version=excluded.core_version,
          input_fingerprint=excluded.input_fingerprint,
          feature_fingerprint=excluded.feature_fingerprint,
          model_fingerprint=excluded.model_fingerprint,
          schema_version=excluded.schema_version,
          authority_contract_version=excluded.authority_contract_version,
          updated_at=excluded.updated_at,
          frozen_at=COALESCE(excluded.frozen_at, final_predictions.frozen_at)
        """
        try:
            with self._lock:
                conn = self._connect()
                try:
                    # Preserve created_at on update
                    existing = conn.execute(
                        "SELECT created_at, frozen_at FROM final_predictions WHERE race_id=?",
                        (rid,),
                    ).fetchone()
                    if existing is not None:
                        payload["created_at"] = existing["created_at"]
                        if auto_frozen is None and existing["frozen_at"]:
                            payload["frozen_at"] = existing["frozen_at"]
                    conn.execute(sql, payload)
                    conn.commit()
                finally:
                    conn.close()
                self.persistent_writes += 1
            return True
        except Exception as exc:  # noqa: BLE001 — response must still succeed
            with self._lock:
                self.persistent_errors += 1
            logger.warning("final_predictions write failed race_id=%s: %s", rid, exc)
            return False


_STORE: FinalPredictionStore | None = None
_STORE_LOCK = threading.Lock()


def get_store() -> FinalPredictionStore:
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = FinalPredictionStore()
        return _STORE


def set_store(store: FinalPredictionStore | None) -> None:
    """Test helper — inject / clear process store."""
    global _STORE
    with _STORE_LOCK:
        _STORE = store


def reset_store_state() -> None:
    store = get_store()
    store.reset_metrics()


__all__ = [
    "ALLOW_POST_RACE_REINFERENCE",
    "AUTHORITY_CONTRACT_VERSION",
    "FREEZE_AT_POST_TIME",
    "FinalPredictionRecord",
    "FinalPredictionStore",
    "PERSIST_BEFORE_POST_TIME",
    "REGENERATE_ON_FEATURE_CHANGE",
    "compute_input_fingerprint",
    "extract_fingerprint_parts",
    "fingerprint_from_bundle_meta",
    "get_store",
    "is_persistable_final",
    "persistent_store_enabled",
    "reset_store_state",
    "set_store",
]
