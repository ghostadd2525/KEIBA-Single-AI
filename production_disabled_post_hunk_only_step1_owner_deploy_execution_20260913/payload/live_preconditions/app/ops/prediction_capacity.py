# -*- coding: utf-8 -*-
"""
Phase C1 — Prediction capacity shell (HTTP get periphery).

Order (AI_PRED_PERSISTENT_STORE=1):
  memory cache → persistent Final store → in-flight dedup → semaphore → inference
  → persistent write → memory cache → return

Order (flag OFF / default):
  memory cache → in-flight dedup → semaphore → inference → memory cache → return

Does not alter RESTORED_V2 / CURRENT_PATH / scoring / FeatureLoader / P1 / PI.
"""
from __future__ import annotations

import copy
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, MutableMapping

FetchFn = Callable[[str], tuple[dict[str, Any] | None, dict[str, Any] | None]]


def _env_flag(key: str, default: str = "1") -> bool:
    return (os.environ.get(key) or default).strip().lower() in ("1", "true", "yes")


def _env_int(key: str, default: int) -> int:
    raw = (os.environ.get(key) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def dedup_enabled() -> bool:
    return _env_flag("AI_PRED_INFLIGHT_DEDUP", "1")


def cache_ttl_sec() -> int:
    return max(0, _env_int("AI_PRED_BUNDLE_CACHE_TTL_SEC", 60))


def infer_concurrency() -> int:
    """0 disables semaphore (unlimited). Default 1. C1 forbids raising above 1 via ops policy."""
    return max(0, _env_int("AI_PRED_INFER_CONCURRENCY", 1))


def canonicalize_race_id(race_id: str) -> str:
    return str(race_id or "").strip()


@dataclass
class _CacheEntry:
    bundle: dict[str, Any]
    meta: dict[str, Any] | None
    expires_at: float


@dataclass
class _InflightEntry:
    event: threading.Event = field(default_factory=threading.Event)
    bundle: dict[str, Any] | None = None
    meta: dict[str, Any] | None = None
    error: BaseException | None = None
    done: bool = False


@dataclass
class CapacityMetrics:
    prediction_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    inflight_leaders: int = 0
    inflight_followers: int = 0
    active_inferences: int = 0
    max_active_inferences: int = 0
    semaphore_wait_ms_total: float = 0.0
    inference_ms_total: float = 0.0
    underlying_calls: int = 0
    persistent_hits: int = 0
    persistent_misses: int = 0
    persistent_writes: int = 0
    persistent_invalidations: int = 0
    persistent_errors: int = 0

    def as_dict(self) -> dict[str, Any]:
        from app.ops.final_prediction_store import persistent_store_enabled

        return {
            "prediction_requests": self.prediction_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "inflight_leaders": self.inflight_leaders,
            "inflight_followers": self.inflight_followers,
            "active_inferences": self.active_inferences,
            "max_active_inferences": self.max_active_inferences,
            "semaphore_wait_ms": round(self.semaphore_wait_ms_total, 3),
            "inference_ms": round(self.inference_ms_total, 3),
            "underlying_calls": self.underlying_calls,
            "persistent_hits": self.persistent_hits,
            "persistent_misses": self.persistent_misses,
            "persistent_writes": self.persistent_writes,
            "persistent_invalidations": self.persistent_invalidations,
            "persistent_errors": self.persistent_errors,
            "cache_entries": 0,  # filled by controller
            "flags": {
                "AI_PRED_INFLIGHT_DEDUP": dedup_enabled(),
                "AI_PRED_BUNDLE_CACHE_TTL_SEC": cache_ttl_sec(),
                "AI_PRED_INFER_CONCURRENCY": infer_concurrency(),
                "AI_PRED_PERSISTENT_STORE": persistent_store_enabled(),
            },
        }


class PredictionCapacityController:
    """Thread-safe capacity shell around a get_with_meta-compatible fetch."""

    def __init__(self, *, store: Any | None = None) -> None:
        self._lock = threading.RLock()
        self._cache: dict[str, _CacheEntry] = {}
        self._inflight: dict[str, _InflightEntry] = {}
        self._metrics = CapacityMetrics()
        self._sem: threading.Semaphore | None = None
        self._sem_n = -1
        self._store = store  # optional injected FinalPredictionStore
        self._refresh_semaphore()

    def _refresh_semaphore(self) -> None:
        n = infer_concurrency()
        if n != self._sem_n:
            self._sem_n = n
            self._sem = threading.Semaphore(n) if n > 0 else None

    def reset(self) -> None:
        """Test helper — clear state and metrics."""
        with self._lock:
            self._cache.clear()
            self._inflight.clear()
            self._metrics = CapacityMetrics()
            self._sem_n = -1
            self._refresh_semaphore()

    def metrics_snapshot(self) -> dict[str, Any]:
        with self._lock:
            out = self._metrics.as_dict()
            out["cache_entries"] = len(self._cache)
            out["inflight_entries"] = len(self._inflight)
            return out

    def _copy_pair(
        self,
        bundle: dict[str, Any] | None,
        meta: dict[str, Any] | None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        return (
            copy.deepcopy(bundle) if bundle is not None else None,
            copy.deepcopy(meta) if meta is not None else None,
        )

    def _annotate_source(
        self,
        meta: dict[str, Any] | None,
        source: str,
    ) -> dict[str, Any] | None:
        if meta is None:
            return {"prediction_source": source}
        out = dict(meta)
        out["prediction_source"] = source
        return out

    def _is_cacheable(
        self,
        bundle: dict[str, Any] | None,
        meta: dict[str, Any] | None,
    ) -> bool:
        """Cache real success only. prediction_unavailable / mock are never cached."""
        if not isinstance(bundle, dict):
            return False
        eng = str((meta or {}).get("engine_source") or "")
        if eng in ("mock_fallback", "mock", "prediction_unavailable"):
            return False
        if bundle.get("status") == "unavailable":
            return False
        if bundle.get("prediction_available") is False:
            return False
        if (meta or {}).get("is_mock") or bundle.get("is_mock"):
            return False
        # Successful real path: status ok (RESTORED_V2 / CURRENT_PATH / real_ai)
        if bundle.get("status") == "ok":
            return True
        if eng == "real_ai":
            return True
        return False

    def _cache_get(
        self, race_id: str
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None] | None:
        ttl = cache_ttl_sec()
        if ttl <= 0:
            return None
        now = time.monotonic()
        with self._lock:
            ent = self._cache.get(race_id)
            if ent is None:
                return None
            if ent.expires_at <= now:
                del self._cache[race_id]
                return None
            return self._copy_pair(ent.bundle, ent.meta)

    def _cache_put(
        self,
        race_id: str,
        bundle: dict[str, Any] | None,
        meta: dict[str, Any] | None,
    ) -> None:
        ttl = cache_ttl_sec()
        if ttl <= 0 or not self._is_cacheable(bundle, meta):
            return
        assert bundle is not None
        with self._lock:
            self._cache[race_id] = _CacheEntry(
                bundle=copy.deepcopy(bundle),
                meta=copy.deepcopy(meta) if meta is not None else None,
                expires_at=time.monotonic() + float(ttl),
            )

    def _get_store(self) -> Any | None:
        from app.ops.final_prediction_store import (
            get_store,
            persistent_store_enabled,
        )

        if not persistent_store_enabled():
            return None
        if self._store is not None:
            return self._store
        return get_store()

    def _persistent_get(
        self, race_id: str
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None] | None:
        store = self._get_store()
        if store is None:
            return None
        before = store.metrics()
        try:
            rec = store.get_valid(race_id)
        except Exception:
            with self._lock:
                self._metrics.persistent_errors += 1
                self._metrics.persistent_misses += 1
            return None
        after = store.metrics()
        with self._lock:
            self._metrics.persistent_hits += max(
                0, after["persistent_hits"] - before["persistent_hits"]
            )
            self._metrics.persistent_misses += max(
                0, after["persistent_misses"] - before["persistent_misses"]
            )
            self._metrics.persistent_invalidations += max(
                0,
                after["persistent_invalidations"] - before["persistent_invalidations"],
            )
            self._metrics.persistent_errors += max(
                0, after["persistent_errors"] - before["persistent_errors"]
            )
        if rec is None:
            return None
        meta = self._annotate_source(rec.meta, "persistent_store")
        return self._copy_pair(rec.bundle, meta)

    def _persistent_put(
        self,
        race_id: str,
        bundle: dict[str, Any] | None,
        meta: dict[str, Any] | None,
    ) -> None:
        store = self._get_store()
        if store is None or bundle is None:
            return
        before = store.metrics()
        try:
            store.put_final(race_id, bundle, meta)
        except Exception:
            with self._lock:
                self._metrics.persistent_errors += 1
            return
        after = store.metrics()
        with self._lock:
            self._metrics.persistent_writes += max(
                0, after["persistent_writes"] - before["persistent_writes"]
            )
            self._metrics.persistent_errors += max(
                0, after["persistent_errors"] - before["persistent_errors"]
            )

    def _begin_inflight(self, race_id: str) -> tuple[_InflightEntry, bool]:
        """Return (entry, is_leader)."""
        with self._lock:
            existing = self._inflight.get(race_id)
            if existing is not None:
                self._metrics.inflight_followers += 1
                return existing, False
            entry = _InflightEntry()
            self._inflight[race_id] = entry
            self._metrics.inflight_leaders += 1
            return entry, True

    def _finish_inflight(
        self,
        race_id: str,
        entry: _InflightEntry,
        *,
        bundle: dict[str, Any] | None = None,
        meta: dict[str, Any] | None = None,
        error: BaseException | None = None,
    ) -> None:
        entry.bundle = bundle
        entry.meta = meta
        entry.error = error
        entry.done = True
        entry.event.set()
        with self._lock:
            cur = self._inflight.get(race_id)
            if cur is entry:
                del self._inflight[race_id]

    def _run_underlying(
        self,
        race_id: str,
        fetch: FetchFn,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        self._refresh_semaphore()
        sem = self._sem
        wait_ms = 0.0
        if sem is not None:
            t0 = time.perf_counter()
            sem.acquire()
            wait_ms = (time.perf_counter() - t0) * 1000.0
        with self._lock:
            self._metrics.semaphore_wait_ms_total += wait_ms
            self._metrics.active_inferences += 1
            self._metrics.max_active_inferences = max(
                self._metrics.max_active_inferences,
                self._metrics.active_inferences,
            )
            self._metrics.underlying_calls += 1
        t1 = time.perf_counter()
        try:
            bundle, meta = fetch(race_id)
            meta = self._annotate_source(meta, "inference")
            return bundle, meta
        finally:
            infer_ms = (time.perf_counter() - t1) * 1000.0
            with self._lock:
                self._metrics.inference_ms_total += infer_ms
                self._metrics.active_inferences = max(
                    0, self._metrics.active_inferences - 1
                )
            if sem is not None:
                sem.release()

    def _after_inference(
        self,
        race_id: str,
        bundle: dict[str, Any] | None,
        meta: dict[str, Any] | None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        self._persistent_put(race_id, bundle, meta)
        self._cache_put(race_id, bundle, meta)
        return self._copy_pair(bundle, meta)

    def get_with_meta(
        self,
        race_id: str,
        *,
        fetch: FetchFn | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        from app.engine.adapters import prediction_adapter

        rid = canonicalize_race_id(race_id)
        fetch_fn: FetchFn = fetch or prediction_adapter.get_with_meta

        with self._lock:
            self._metrics.prediction_requests += 1

        cached = self._cache_get(rid)
        if cached is not None:
            with self._lock:
                self._metrics.cache_hits += 1
            b, m = cached
            return b, self._annotate_source(m, "memory_cache")

        with self._lock:
            self._metrics.cache_misses += 1

        # Persistent Final lookup (between C1 miss and inference)
        persisted = self._persistent_get(rid)
        if persisted is not None:
            b, m = persisted
            # Warm C1 so subsequent requests within TTL skip SQLite
            self._cache_put(rid, b, m)
            return self._copy_pair(b, m)

        if not dedup_enabled():
            bundle, meta = self._run_underlying(rid, fetch_fn)
            return self._after_inference(rid, bundle, meta)

        entry, is_leader = self._begin_inflight(rid)
        if not is_leader:
            entry.event.wait()
            if entry.error is not None:
                raise entry.error
            return self._copy_pair(entry.bundle, entry.meta)

        try:
            bundle, meta = self._run_underlying(rid, fetch_fn)
            out = self._after_inference(rid, bundle, meta)
            self._finish_inflight(rid, entry, bundle=out[0], meta=out[1])
            return out
        except BaseException as exc:
            self._finish_inflight(rid, entry, error=exc)
            raise


_CONTROLLER = PredictionCapacityController()


def get_controller() -> PredictionCapacityController:
    return _CONTROLLER


def reset_capacity_state() -> None:
    _CONTROLLER.reset()


def metrics_snapshot() -> dict[str, Any]:
    return _CONTROLLER.metrics_snapshot()


def get_with_meta(
    race_id: str,
    *,
    fetch: FetchFn | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """HTTP GET /v1/predictions/{race_id} capacity entrypoint."""
    return _CONTROLLER.get_with_meta(race_id, fetch=fetch)


__all__ = [
    "PredictionCapacityController",
    "canonicalize_race_id",
    "get_controller",
    "get_with_meta",
    "metrics_snapshot",
    "reset_capacity_state",
]
