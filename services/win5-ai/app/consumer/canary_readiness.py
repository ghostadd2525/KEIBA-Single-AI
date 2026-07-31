# -*- coding: utf-8 -*-
"""Phase C7 — Canary Readiness Validation.

Judges Canary operational readiness only.
Does NOT cut over Production. No feature / Core / Contract changes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.consumer.flags import snapshot_all_flags, snapshot_consumer_flags
from app.consumer.shadow_validation import run_shadow_validation
from app.consumer.staging_validation import run_staging_validation


def _item(item_id: str, status: str, detail: str, blocker: bool = False) -> dict[str, Any]:
    return {
        "id": item_id,
        "status": status,  # PASS | GAP | FAIL
        "detail": detail,
        "blocker_for_canary": blocker,
    }


def build_deployment_checklist() -> list[dict[str, Any]]:
    """Canary prerequisites. GAP = missing for full traffic Canary; not all are blockers for library Canary."""
    return [
        _item(
            "lib_consumer_c1_c4",
            "PASS",
            "Consumer API / Registry / Presentation / Ticket / Decision Service present",
        ),
        _item(
            "shadow_validation_c5",
            "PASS",
            "C5 Shadow Validation PASS 6/6",
        ),
        _item(
            "ux_validation_c55",
            "PASS",
            "C5.5 UX PASS_WITH_NOTES (structured labels; NL intentionally absent)",
        ),
        _item(
            "staging_validation_c6",
            "PASS",
            "C6 Staging Flag OFF/ON / Rollback / Perf / Logging PASS",
        ),
        _item(
            "feature_flags",
            "PASS",
            "W_CONSUMER_SINGLE/PRESENTATION/TICKET default OFF; Flag rollback proven",
        ),
        _item(
            "version_contract",
            "PASS",
            "core-semantic-payload/v1 + consumer-api/single/v1 + PLATFORM-V1-CONTRACT",
        ),
        _item(
            "boundary_integrity",
            "PASS",
            "C5 boundary_audit: no reverse Core→Consumer dependency",
        ),
        _item(
            "failure_recovery_flag_off",
            "PASS",
            "C6 rollback: Flag OFF → LEGACY immediate",
        ),
        _item(
            "http_canary_route",
            "GAP",
            "Public HTTP / edge route for percentage traffic not wired",
            blocker=True,
        ),
        _item(
            "metrics_dashboard",
            "GAP",
            "Canary metrics (error rate, latency p95, flag snapshot) dashboard not provisioned",
            blocker=True,
        ),
        _item(
            "alert_rules",
            "GAP",
            "Pager/alert on Consumer exception rate vs Legacy baseline not configured",
            blocker=True,
        ),
        _item(
            "traffic_split_control",
            "GAP",
            "1%%/5%%/10%% traffic split controller not implemented",
            blocker=True,
        ),
        _item(
            "ops_oncall_runbook_signoff",
            "GAP",
            "On-call sign-off for Canary window not recorded (guideline exists in C7 docs)",
            blocker=False,
        ),
    ]


def evaluate_release_readiness(shadow: dict[str, Any], staging: dict[str, Any]) -> dict[str, Any]:
    ok = shadow.get("verdict") == "PASS" and staging.get("verdict") == "PASS"
    return {
        "id": "release_readiness",
        "status": "PASS" if ok else "FAIL",
        "detail": f"shadow={shadow.get('verdict')} staging={staging.get('verdict')}",
        "version1_consumer_releasable_as_library": ok,
        "production_cutover": False,
    }


def evaluate_operational_readiness(flags: dict[str, bool], staging: dict[str, Any]) -> dict[str, Any]:
    has_flags = set(flags.keys()) >= {
        "W_CONSUMER_SINGLE_ENABLED",
        "W_CONSUMER_PRESENTATION_ENABLED",
        "W_CONSUMER_TICKET_ENABLED",
    }
    has_logging = any(l.get("event") for l in staging.get("logs") or [])
    has_rollback = bool((staging.get("rollback") or {}).get("ok"))
    has_version = bool((staging.get("logs") or [{}])[0].get("version"))
    # Monitoring: library logs exist; external monitoring = GAP (not FAIL of library ops core)
    monitoring = "PARTIAL"  # logs yes, dashboard no
    ok = has_flags and has_logging and has_rollback and has_version
    return {
        "id": "operational_readiness",
        "status": "PASS" if ok else "FAIL",
        "detail": {
            "feature_flag": has_flags,
            "logging": has_logging,
            "rollback": has_rollback,
            "version": has_version,
            "monitoring": monitoring,
        },
    }


def evaluate_failure_recovery(staging: dict[str, Any]) -> dict[str, Any]:
    rb = staging.get("rollback") or {}
    ok = bool(rb.get("ok") and rb.get("immediate") and rb.get("fingerprint_match"))
    return {
        "id": "failure_recovery",
        "status": "PASS" if ok else "FAIL",
        "detail": rb,
    }


def evaluate_boundary_integrity(shadow: dict[str, Any]) -> dict[str, Any]:
    checks = {c["id"]: c for c in shadow.get("checks") or []}
    b = checks.get("boundary_audit") or {}
    c = checks.get("contract_integrity") or {}
    ok = b.get("status") == "PASS" and c.get("status") == "PASS"
    return {
        "id": "boundary_integrity",
        "status": "PASS" if ok else "FAIL",
        "detail": {
            "boundary_audit": b.get("detail"),
            "contract_integrity": c.get("detail"),
            "decision_is_composer_only": True,
        },
    }


def run_canary_readiness() -> dict[str, Any]:
    """Aggregate C5/C6 evidence + checklist → Canary readiness verdict."""
    shadow = run_shadow_validation()
    staging = run_staging_validation(repeats=5)
    flags = snapshot_consumer_flags()
    all_flags = snapshot_all_flags()

    axes = [
        evaluate_release_readiness(shadow, staging),
        evaluate_operational_readiness(flags, staging),
        evaluate_failure_recovery(staging),
        evaluate_boundary_integrity(shadow),
    ]
    checklist = build_deployment_checklist()
    blockers = [i for i in checklist if i.get("blocker_for_canary") and i["status"] == "GAP"]
    axis_fail = [a for a in axes if a["status"] == "FAIL"]

    if axis_fail:
        verdict = "NOT_READY"
    elif blockers:
        verdict = "READY_WITH_GAPS"
    else:
        verdict = "READY"

    recommendation = {
        "canary_library_path": "APPROVE" if verdict in ("READY", "READY_WITH_GAPS") else "BLOCK",
        "canary_traffic_split": "BLOCK until HTTP route + metrics + alerts + traffic split GAP closed",
        "production_cutover": "DO_NOT_EXECUTE",
        "next_actions": [b["id"] + ": " + b["detail"] for b in blockers],
        "notes": [
            "Version1 Consumer library + Flag/Rollback proven (C6)",
            "Canary traffic requires edge wiring - out of C7 scope to implement",
            "No Prediction/Semantic/Core/Contract/Feature changes in C7",
        ],
    }

    return {
        "phase": "C7",
        "title": "Canary Readiness Validation",
        "verdict": verdict,
        "production_cutover": False,
        "feature_addition": False,
        "axes": axes,
        "deployment_checklist": checklist,
        "blockers": blockers,
        "recommendation": recommendation,
        "evidence": {
            "shadow_verdict": shadow.get("verdict"),
            "staging_verdict": staging.get("verdict"),
            "flags_default": flags,
            "all_flags_sample": all_flags,
        },
        "docs_expected": [
            "v109-c7-canary-readiness-report.md",
            "v109-c7-deployment-checklist.md",
            "v109-c7-operational-guideline.md",
            "v109-c7-release-recommendation.md",
            "v109-c7-governance.md",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(run_canary_readiness(), ensure_ascii=False, indent=2))
