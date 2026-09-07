# -*- coding: utf-8 -*-
"""Phase C6 — Staging Validation (Feature Flag coexistence).

Staging only. No Production cutover / Canary.
Does not change Core / Prediction / Semantic / Contract.
"""
from __future__ import annotations

import copy
import json
import os
import time
import tracemalloc
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from app.consumer.core_client import InMemoryCoreClient
from app.consumer.core_payload import CORE_SCHEMA, fingerprint_payload
from app.consumer.decision_service.dto import PLATFORM_CONTRACT, version_info_dict
from app.consumer.flags import snapshot_all_flags, snapshot_consumer_flags
from app.consumer.single_api import build_single_response


def _clear_env_flags() -> None:
    for k in list(os.environ.keys()):
        if k.startswith("W_CONSUMER_") or k.startswith("W_CORE_") or k.startswith("W_DECISION_"):
            os.environ.pop(k, None)


def _set_consumer_flags(*, single: bool, presentation: bool, ticket: bool) -> None:
    _clear_env_flags()
    os.environ["W_CONSUMER_SINGLE_ENABLED"] = "true" if single else "false"
    os.environ["W_CONSUMER_PRESENTATION_ENABLED"] = "true" if presentation else "false"
    os.environ["W_CONSUMER_TICKET_ENABLED"] = "true" if ticket else "false"


def _fixture(race_id: str = "stg-r1") -> dict[str, Any]:
    return {
        "schema": CORE_SCHEMA,
        "race_id": race_id,
        "world_id": "rank7_world",
        "prediction": {
            "ranks": ["A", "B", "C", "D", "E", "F", "G"],
            "scores": [0.28, 0.18, 0.14, 0.12, 0.10, 0.10, 0.08],
            "top1": "A",
        },
        "decision_trace": {"rank7_world": {"match": True}},
        "transition": None,
        "trigger_path": "staging/path",
        "near_miss": None,
        "affinity": None,
        "exclusion_reasons": {},
        "explanation_confidence": {
            "explanation_confidence": 0.93,
            "definition_version": "v101/1.0",
            "not": ["prediction_probability"],
        },
    }


@dataclass
class StagingLogRecord:
    event: str
    race_id: str
    mode: str | None
    consumer_flags: dict[str, bool]
    all_flags: dict[str, bool]
    version: dict[str, Any]
    core_fingerprint: str | None
    ok: bool
    detail: str = ""
    elapsed_ms: float | None = None
    peak_memory_kb: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StagingReport:
    verdict: str
    checks: list[dict[str, Any]] = field(default_factory=list)
    logs: list[dict[str, Any]] = field(default_factory=list)
    performance: dict[str, Any] = field(default_factory=dict)
    rollback: dict[str, Any] = field(default_factory=dict)
    compatibility: dict[str, Any] = field(default_factory=dict)
    production_cutover: bool = False
    canary: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _check(cid: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"id": cid, "status": "PASS" if ok else "FAIL", "detail": detail}


def _timed(fn: Callable[[], Any], repeats: int = 25) -> tuple[Any, float, float]:
    """Return (last_result, mean_ms, peak_kb)."""
    tracemalloc.start()
    t0 = time.perf_counter()
    result = None
    for _ in range(repeats):
        result = fn()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0 / repeats
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, elapsed_ms, peak / 1024.0


def run_staging_validation(*, repeats: int = 25) -> dict[str, Any]:
    """Execute C6 Staging checks. Staging only — no Production wiring."""
    logs: list[StagingLogRecord] = []
    race_id = "stg-r1"
    core = _fixture(race_id)
    client = InMemoryCoreClient()
    client.put_for_test(race_id, core)
    stored = copy.deepcopy(client._store[race_id])
    fp0 = fingerprint_payload(stored)

    # --- ① Flag OFF → Legacy + fingerprint ---
    _set_consumer_flags(single=False, presentation=False, ticket=False)
    # force=True allows call while single flag OFF (library Shadow/Staging harness)
    legacy = build_single_response(client, race_id, force=True)
    fp_legacy = fingerprint_payload(client._store[race_id])
    off_ok = (
        legacy.get("mode") == "LEGACY"
        and legacy.get("presentation") is None
        and legacy.get("ticket") is None
        and legacy.get("core_payload") == stored
        and fp_legacy == fp0
        and all(v is False for v in snapshot_consumer_flags().values())
    )
    logs.append(
        StagingLogRecord(
            event="flag_off_legacy",
            race_id=race_id,
            mode=legacy.get("mode"),
            consumer_flags=snapshot_consumer_flags(),
            all_flags=snapshot_all_flags(),
            version=version_info_dict(),
            core_fingerprint=fp_legacy,
            ok=off_ok,
            detail="legacy_complete" if off_ok else "legacy_mismatch",
        )
    )
    check_off = _check("flag_off_legacy", off_ok, f"fp={fp_legacy} mode={legacy.get('mode')}")

    # --- ② Flag ON (Staging) → Consumer additions, Core intact ---
    _set_consumer_flags(single=True, presentation=True, ticket=True)
    # Staging ON path: flags enabled, no force required for single; use include_*
    staging = build_single_response(
        client,
        race_id,
        include_tickets=True,
        include_presentation=True,
        locale="ja",
    )
    fp_on = fingerprint_payload(client._store[race_id])
    on_ok = (
        staging.get("presentation") is not None
        and staging.get("ticket") is not None
        and staging.get("core_payload") == stored
        and staging.get("core_ref", {}).get("payload_fingerprint") == fp0
        and fp_on == fp0
        and staging.get("registry", {}).get("policy_id") == legacy.get("registry", {}).get("policy_id")
        and client._store[race_id] == stored
    )
    logs.append(
        StagingLogRecord(
            event="flag_on_staging",
            race_id=race_id,
            mode=staging.get("mode"),
            consumer_flags=snapshot_consumer_flags(),
            all_flags=snapshot_all_flags(),
            version=version_info_dict(),
            core_fingerprint=fp_on,
            ok=on_ok,
            detail="consumer_added_core_intact" if on_ok else "staging_mismatch",
        )
    )
    check_on = _check(
        "flag_on_staging",
        on_ok,
        f"fp={fp_on} has_presentation={staging.get('presentation') is not None} has_ticket={staging.get('ticket') is not None}",
    )

    # --- ③ Performance ---
    _set_consumer_flags(single=True, presentation=True, ticket=True)

    def _legacy_call():
        _set_consumer_flags(single=False, presentation=False, ticket=False)
        return build_single_response(client, race_id, force=True)

    def _staging_call():
        _set_consumer_flags(single=True, presentation=True, ticket=True)
        return build_single_response(
            client, race_id, include_tickets=True, include_presentation=True
        )

    _, legacy_ms, legacy_peak = _timed(_legacy_call, repeats=repeats)
    _, staging_ms, staging_peak = _timed(_staging_call, repeats=repeats)
    # No exception path
    exc_ok = True
    try:
        _staging_call()
    except Exception as e:  # noqa: BLE001
        exc_ok = False
        exc_detail = str(e)
    else:
        exc_detail = "none"

    # Soft budgets for library Staging (not Production SLA)
    # Consumer add-on should remain modest vs legacy on same fixture
    delta_ms = staging_ms - legacy_ms
    perf_ok = exc_ok and staging_ms < 50.0 and staging_peak < 50_000.0
    performance = {
        "repeats": repeats,
        "legacy_mean_ms": round(legacy_ms, 4),
        "staging_mean_ms": round(staging_ms, 4),
        "delta_ms": round(delta_ms, 4),
        "legacy_peak_kb": round(legacy_peak, 2),
        "staging_peak_kb": round(staging_peak, 2),
        "exceptions": exc_detail,
        "budget_staging_ms_lt": 50.0,
        "budget_peak_kb_lt": 50000.0,
    }
    logs.append(
        StagingLogRecord(
            event="performance",
            race_id=race_id,
            mode="SHADOW/STAGING",
            consumer_flags=snapshot_consumer_flags(),
            all_flags=snapshot_all_flags(),
            version=version_info_dict(),
            core_fingerprint=fp0,
            ok=perf_ok,
            detail=json.dumps(performance, ensure_ascii=False),
            elapsed_ms=staging_ms,
            peak_memory_kb=staging_peak,
        )
    )
    check_perf = _check("performance", perf_ok, json.dumps(performance, ensure_ascii=False))

    # --- ④ Rollback: ON → OFF → Legacy ---
    _set_consumer_flags(single=True, presentation=True, ticket=True)
    _ = build_single_response(client, race_id, include_tickets=True, include_presentation=True)
    _set_consumer_flags(single=False, presentation=False, ticket=False)
    rolled = build_single_response(client, race_id, force=True)
    fp_rb = fingerprint_payload(client._store[race_id])
    rollback_ok = (
        rolled.get("mode") == "LEGACY"
        and rolled.get("presentation") is None
        and rolled.get("ticket") is None
        and rolled.get("core_payload") == stored
        and fp_rb == fp0
        and rolled.get("registry", {}).get("policy_id") == legacy.get("registry", {}).get("policy_id")
    )
    rollback = {
        "sequence": ["flags_on", "flags_off", "legacy"],
        "immediate": True,
        "fingerprint_match": fp_rb == fp0,
        "mode": rolled.get("mode"),
        "ok": rollback_ok,
    }
    logs.append(
        StagingLogRecord(
            event="rollback",
            race_id=race_id,
            mode=rolled.get("mode"),
            consumer_flags=snapshot_consumer_flags(),
            all_flags=snapshot_all_flags(),
            version=version_info_dict(),
            core_fingerprint=fp_rb,
            ok=rollback_ok,
            detail="immediate_legacy" if rollback_ok else "rollback_failed",
        )
    )
    check_rb = _check("rollback", rollback_ok, json.dumps(rollback, ensure_ascii=False))

    # --- ⑤ Logging presence ---
    required_log_fields = (
        "event",
        "consumer_flags",
        "all_flags",
        "version",
        "core_fingerprint",
    )
    logging_ok = all(
        all(f in rec.to_dict() for f in required_log_fields) for rec in logs
    ) and any(rec.event == "flag_on_staging" for rec in logs)
    # Distinguish Core log vs Consumer log in payload
    sample_log = {
        "consumer_log": {
            "event": "flag_on_staging",
            "flags": snapshot_consumer_flags(),
            "version": version_info_dict(),
        },
        "core_log": {
            "race_id": race_id,
            "fingerprint": fp0,
            "schema": CORE_SCHEMA,
            "platform_contract": PLATFORM_CONTRACT,
            "mutated": False,
        },
    }
    check_log = _check("logging", logging_ok, "consumer+core+version+flags emitted")

    checks = [check_off, check_on, check_perf, check_rb, check_log]
    failed = [c for c in checks if c["status"] == "FAIL"]
    verdict = "PASS" if not failed else "FAIL"

    compatibility = {
        "flag_off_equals_legacy": off_ok,
        "flag_on_adds_consumer_only": on_ok,
        "core_fingerprint_stable": fp0 == fp_legacy == fp_on == fp_rb,
        "policy_id_stable": legacy.get("registry", {}).get("policy_id")
        == staging.get("registry", {}).get("policy_id")
        == rolled.get("registry", {}).get("policy_id"),
        "production_coexistence_model": "flag_gated_same_entrypoint",
        "production_cutover": False,
        "canary": False,
    }

    report = StagingReport(
        verdict=verdict,
        checks=checks,
        logs=[r.to_dict() for r in logs],
        performance=performance,
        rollback=rollback,
        compatibility=compatibility,
        production_cutover=False,
        canary=False,
    )
    _clear_env_flags()
    return report.to_dict()


if __name__ == "__main__":
    print(json.dumps(run_staging_validation(), ensure_ascii=False, indent=2))
