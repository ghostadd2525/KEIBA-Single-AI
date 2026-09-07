# -*- coding: utf-8 -*-
"""Phase C5 — Single Shadow Validation (Consumer Validation only).

No feature addition. Shadow Observation only.
"""
from __future__ import annotations

import ast
import copy
import json
import os
from pathlib import Path
from typing import Any

from app.consumer.core_client import InMemoryCoreClient
from app.consumer.core_payload import CORE_SCHEMA, fingerprint_payload
from app.consumer.decision_service.dto import PLATFORM_CONTRACT, version_info_dict
from app.consumer.flags import snapshot_consumer_flags
from app.consumer.single_api import build_single_response

# Semantic keys that Consumer must not alter on Core
_CORE_SEMANTIC_KEYS = (
    "prediction",
    "world_id",
    "near_miss",
    "affinity",
    "explanation_confidence",
    "exclusion_reasons",
    "transition",
    "trigger_path",
    "decision_trace",
)

# Keys allowed as Consumer additions on the response (not Core mutations)
_CONSUMER_ADDITION_TOP_KEYS = frozenset(
    {
        "schema",
        "core_ref",
        "registry",
        "ticket",
        "presentation",
        "flags_snapshot",
        "warnings",
        "selectors",
        "single_response_schema",
        "version",
        "core_payload",
        "policy_metadata",
        "mode",
        "natural_explanation",
        "decision_reason",
    }
)

_FORBIDDEN_RESPONSE_MEANING = frozenset(
    {
        "inferred_world",
        "rewritten_ranks",
        "adjusted_scores",
        "new_affinity",
        "derived_ec",
        "why",
    }
)


def _fixture_core(race_id: str = "c5-r1") -> dict[str, Any]:
    return {
        "schema": CORE_SCHEMA,
        "race_id": race_id,
        "world_id": "rank7_world",
        "prediction": {
            "ranks": ["A", "B", "C", "D", "E", "F", "G"],
            "scores": [0.30, 0.20, 0.15, 0.10, 0.10, 0.10, 0.05],
            "top1": "A",
        },
        "decision_trace": {"rank7_world": {"must": True, "match": True}},
        "transition": "dual→rank7",
        "trigger_path": "path/c5",
        "near_miss": None,
        "affinity": {
            "rank7_world": 0.88,
            "core_world": 0.12,
            "definition": "v96/must_affinity",
        },
        "exclusion_reasons": {"midhole_world": ["gate_x"]},
        "explanation_confidence": {
            "semantic_confidence": 1.0,
            "world_confidence": 0.95,
            "near_miss_confidence": None,
            "trace_confidence": 1.0,
            "explanation_confidence": 0.97,
            "definition_version": "v101/1.0",
            "not": ["prediction_probability", "odds", "calibration"],
        },
        "expected_strategy_ref": {"registry": "v75-expected-strategy", "key": "rank7_world"},
    }


def _clear_flags() -> None:
    for k in list(os.environ.keys()):
        if k.startswith("W_CONSUMER_") or k.startswith("W_CORE_") or k.startswith("W_DECISION_"):
            os.environ.pop(k, None)


def _check(name: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"id": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def validate_core_integrity(client: InMemoryCoreClient, race_id: str, stored: dict[str, Any]) -> dict[str, Any]:
    before_fp = fingerprint_payload(stored)
    before = copy.deepcopy(stored)
    resp = build_single_response(
        client,
        race_id,
        force=True,
        include_tickets=True,
        include_presentation=True,
    )
    after = client._store[race_id]
    ok_store = after == before and fingerprint_payload(after) == before_fp
    ok_echo = resp.get("core_payload") == before
    ok_fp = resp.get("core_ref", {}).get("payload_fingerprint") == before_fp
    ok = ok_store and ok_echo and ok_fp
    return _check(
        "core_integrity",
        ok,
        f"store_equal={ok_store} echo_equal={ok_echo} fp_equal={ok_fp}",
    )


def validate_contract_integrity(client: InMemoryCoreClient, race_id: str, stored: dict[str, Any]) -> dict[str, Any]:
    before = {k: copy.deepcopy(stored.get(k)) for k in _CORE_SEMANTIC_KEYS}
    build_single_response(
        client, race_id, force=True, include_tickets=True, include_presentation=True
    )
    after_store = client._store[race_id]
    diffs = []
    for k in _CORE_SEMANTIC_KEYS:
        if after_store.get(k) != before[k]:
            diffs.append(k)
    ok = not diffs
    return _check("contract_integrity", ok, "unchanged" if ok else f"mutated:{diffs}")


def validate_response_integrity(client: InMemoryCoreClient, race_id: str) -> dict[str, Any]:
    resp = build_single_response(
        client, race_id, force=True, include_tickets=True, include_presentation=True
    )
    # Top-level keys must be known consumer additions or null forbidden meaning
    unknown = [k for k in resp.keys() if k not in _CONSUMER_ADDITION_TOP_KEYS]
    forbidden_hit = [k for k in _FORBIDDEN_RESPONSE_MEANING if resp.get(k) is not None]
    nl = resp.get("natural_explanation")
    reason = resp.get("decision_reason")
    has_pres = resp.get("presentation") is not None
    has_ticket = resp.get("ticket") is not None
    has_policy = resp.get("registry") is not None and resp.get("policy_metadata") is not None
    # Ticket must not invent reason
    ticket_reason = (resp.get("ticket") or {}).get("reason")
    ok = (
        not unknown
        and not forbidden_hit
        and nl is None
        and reason is None
        and ticket_reason is None
        and has_pres
        and has_ticket
        and has_policy
    )
    return _check(
        "response_integrity",
        ok,
        f"unknown={unknown} forbidden={forbidden_hit} presentation={has_pres} ticket={has_ticket} policy={has_policy}",
    )


def validate_feature_flags(client: InMemoryCoreClient, race_id: str) -> dict[str, Any]:
    _clear_flags()
    # all consumer flags OFF
    flags = snapshot_consumer_flags()
    all_off = all(v is False for v in flags.values())
    legacy = build_single_response(client, race_id, force=True)
    legacy_ok = (
        all_off
        and legacy.get("presentation") is None
        and legacy.get("ticket") is None
        and legacy.get("mode") == "LEGACY"
        and legacy.get("registry") is not None
    )

    # Shadow ON path (force includes consumer additions without env ON)
    shadow = build_single_response(
        client, race_id, force=True, include_tickets=True, include_presentation=True
    )
    shadow_ok = (
        shadow.get("presentation") is not None
        and shadow.get("ticket") is not None
        and shadow.get("mode") == "SHADOW"
        and shadow.get("core_payload") == legacy.get("core_payload")
        and shadow.get("registry", {}).get("policy_id") == legacy.get("registry", {}).get("policy_id")
    )
    ok = legacy_ok and shadow_ok
    return _check(
        "feature_flag",
        ok,
        f"legacy_ok={legacy_ok} shadow_ok={shadow_ok} flags_off={flags}",
    )


def validate_version_integrity() -> dict[str, Any]:
    v = version_info_dict()
    ok = (
        v.get("core_schema") == CORE_SCHEMA
        and v.get("consumer_api_schema") == "consumer-api/single/v1"
        and v.get("platform_contract") == PLATFORM_CONTRACT
        and v.get("single_response_schema") == "single-response/v1"
        and "ADR-009" in (v.get("parents") or [])
        and "ADR-010" in (v.get("parents") or [])
        and "ADR-011" in (v.get("parents") or [])
    )
    return _check(
        "version_integrity",
        ok,
        json.dumps(
            {
                "core": v.get("core_schema"),
                "consumer": v.get("consumer_api_schema"),
                "contract": v.get("platform_contract"),
                "single": v.get("single_response_schema"),
            },
            ensure_ascii=False,
        ),
    )


def _imports_from_file(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return set()
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                mods.add(n.name.split(".")[0] if n.name.startswith("app") else n.name)
                if n.name.startswith("app."):
                    mods.add(n.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


def validate_boundary_audit(consumer_root: Path | None = None) -> dict[str, Any]:
    """Consumer may depend on decision.flags (read-only). Core/PE must not import consumer."""
    root = consumer_root or Path(__file__).resolve().parents[1]  # app/
    consumer_dir = root / "consumer"
    # Reverse: who imports app.consumer?
    reverse_hits: list[str] = []
    for py in root.rglob("*.py"):
        if "consumer" in py.parts:
            continue
        text = py.read_text(encoding="utf-8", errors="ignore")
        if "app.consumer" in text or "from app import consumer" in text:
            reverse_hits.append(str(py.relative_to(root)))

    # Consumer internal: allow app.consumer.* and app.decision.flags only from outside consumer
    external: list[str] = []
    for py in consumer_dir.rglob("*.py"):
        for mod in _imports_from_file(py):
            if not mod.startswith("app."):
                continue
            if mod.startswith("app.consumer"):
                continue
            if mod in ("app.decision.flags",) or mod.startswith("app.decision.flags"):
                continue
            # importing app.decision package broadly is a boundary smell
            if mod.startswith("app.decision") or mod.startswith("app.research") or mod.startswith("app.ops"):
                external.append(f"{py.name}:{mod}")

    ok = not reverse_hits and not external
    return _check(
        "boundary_audit",
        ok,
        f"reverse_imports={reverse_hits} consumer_external={external}",
    )


def run_shadow_validation() -> dict[str, Any]:
    """Execute all C5 checks. Returns machine-readable report."""
    _clear_flags()
    race_id = "c5-r1"
    core = _fixture_core(race_id)
    client = InMemoryCoreClient()
    client.put_for_test(race_id, core)
    stored = copy.deepcopy(client._store[race_id])

    checks = [
        validate_core_integrity(client, race_id, stored),
        validate_contract_integrity(client, race_id, stored),
        validate_response_integrity(client, race_id),
        validate_feature_flags(client, race_id),
        validate_version_integrity(),
        validate_boundary_audit(),
    ]
    passed = sum(1 for c in checks if c["status"] == "PASS")
    failed = [c for c in checks if c["status"] == "FAIL"]
    verdict = "PASS" if not failed else "FAIL"
    return {
        "phase": "C5",
        "title": "Single Shadow Validation",
        "mode": "Shadow Observation",
        "verdict": verdict,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "production_wiring": False,
        "feature_addition": False,
    }


if __name__ == "__main__":
    report = run_shadow_validation()
    print(json.dumps(report, ensure_ascii=False, indent=2))
