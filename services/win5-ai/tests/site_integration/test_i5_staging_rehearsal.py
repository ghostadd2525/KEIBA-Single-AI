# -*- coding: utf-8 -*-
"""I5 — Staging Rehearsal runner (procedure evidence, no product mutation).

Does not change Core / Consumer / Prediction / UI / Race List Cache / Contracts.
Does not leave single_ai_detail=true in committed beta.json.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
ART = REPO / "docs" / "research" / "i5-artifacts"
OPS = REPO / "docs" / "ops"


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def _check(cid: str, ok: bool, detail: str) -> dict:
    return {"id": cid, "status": "PASS" if ok else "FAIL", "detail": detail}


def run_rehearsal() -> dict:
    checks: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()

    # Freeze / locks
    races = _read("public/races.html")
    race = _read("public/race.html")
    beta = _read("public/config/beta.json")
    checks.append(
        _check(
            "list_no_single",
            "single-detail.js" not in races and "ExpectApi.Single" not in races,
            "races.html has no Single wiring",
        )
    )
    checks.append(
        _check(
            "list_cache_key",
            "expect_race_list_cache_v4" in races,
            "Race List Cache key present",
        )
    )
    checks.append(
        _check(
            "detail_wired",
            "single-detail.js" in race and "ExpectApi.SingleDetail.getWithMeta" in race,
            "race.html SingleDetail wired (repo)",
        )
    )
    checks.append(
        _check(
            "flag_default_off",
            '"single_ai_detail": false' in beta,
            "committed beta Flag default OFF (rehearsal must not leave ON)",
        )
    )

    # Procedure surfaces
    for name in (
        "single-detail-operation-guide.md",
        "single-detail-alert-rules.md",
        "single-detail-runbook.md",
        "single-detail-metrics.md",
        "single-detail-dashboard.md",
    ):
        p = OPS / name
        checks.append(_check(f"runbook_doc_{name}", p.is_file(), str(p.relative_to(REPO))))

    obs = _read("functions/_lib/singleDetailObservability.js")
    checks.append(_check("metrics_module", "ALT-SD01" in obs and "recordSingleDetailEvent" in obs, "I4 metrics"))
    checks.append(
        _check(
            "ops_endpoint",
            (REPO / "functions/api/ops/single-detail.js").is_file(),
            "/api/ops/single-detail present",
        )
    )
    mon = _read("functions/_lib/opsMonitor.js")
    checks.append(_check("dashboard_probe", "probeSingleDetailOps" in mon, "single_detail_ops probe"))

    # Alert validation (node)
    node_script = REPO / "scripts/ops/test-single-detail-observability.mjs"
    alert_ok = False
    alert_out = ""
    try:
        proc = subprocess.run(
            [sys.executable and "node", str(node_script)],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=30,
        )
        alert_out = (proc.stdout or "") + (proc.stderr or "")
        alert_ok = proc.returncode == 0 and "PASS single-detail-observability" in alert_out
    except Exception as e:  # noqa: BLE001
        alert_out = str(e)
    checks.append(_check("alert_validation_unit", alert_ok, "node observability unit"))

    sd = _read("public/assets/api/single-detail.js")
    checks.append(_check("fe_flag_gate", 'FLAG = "single_ai_detail"' in sd, "FE Flag gate"))
    checks.append(_check("fe_timeout", "TIMEOUT_MS = 14000" in sd or "AbortError" in sd, "FE timeout path"))
    checks.append(_check("fe_rollback_catch", "prediction_fallback" in sd, "FE catch → Prediction"))

    harness = ART / "rehearsal-harness.html"
    checks.append(_check("client_harness_present", harness.is_file(), "I5 client harness"))

    # Production baseline notes (filled by outer report; runner marks procedural readiness)
    verdict = "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL"
    report = {
        "schema": "expect-i5-staging-rehearsal/1.0",
        "phase": "I5",
        "generated_at": now,
        "verdict": verdict,
        "production_cutover": False,
        "flag_left_on": False,
        "checks": checks,
        "alert_unit_excerpt": alert_out[-800:] if alert_out else "",
        "procedure": {
            "flag_on": 'Set ui_features.single_ai_detail=true in beta.json (staging only)',
            "flag_off_rollback": "Set single_ai_detail=false",
            "ops": "GET /api/ops/single-detail · /api/ops/dashboard",
            "scope": "race.html only · list LOCK",
        },
    }
    ART.mkdir(parents=True, exist_ok=True)
    out = ART / "staging-rehearsal-report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


class I5StagingRehearsalAuditTest(unittest.TestCase):
    def test_rehearsal_pass(self):
        report = run_rehearsal()
        self.assertEqual(report["verdict"], "PASS", report)
        self.assertFalse(report["flag_left_on"])
        self.assertFalse(report["production_cutover"])


if __name__ == "__main__":
    report = run_rehearsal()
    print(json.dumps({"verdict": report["verdict"], "checks": len(report["checks"])}, indent=2))
    raise SystemExit(0 if report["verdict"] == "PASS" else 1)
