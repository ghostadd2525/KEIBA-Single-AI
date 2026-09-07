# -*- coding: utf-8 -*-
"""I4 — Operational readiness audit (ops wiring, freezes, docs)."""
from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


class I4OperationalReadinessAuditTest(unittest.TestCase):
    def test_observability_module_exists(self):
        p = REPO / "functions" / "_lib" / "singleDetailObservability.js"
        src = p.read_text(encoding="utf-8")
        self.assertIn("recordSingleDetailEvent", src)
        self.assertIn("evaluateSingleDetailAlerts", src)
        self.assertIn("ALT-SD01", src)
        self.assertIn("ALT-SD05", src)
        self.assertIn("error_fallback_of_attempted", src)

    def test_adapter_records_events(self):
        src = (
            REPO / "functions" / "_lib" / "adapters" / "singleDetailAdapter.js"
        ).read_text(encoding="utf-8")
        self.assertIn("recordSingleDetailEvent", src)
        self.assertIn("singleDetailObservability", src)

    def test_ops_endpoint(self):
        p = REPO / "functions" / "api" / "ops" / "single-detail.js"
        src = p.read_text(encoding="utf-8")
        self.assertIn("snapshotSingleDetailMetrics", src)
        self.assertIn("evaluateSingleDetailAlerts", src)
        self.assertIn("OPS_MONITOR_KEY", src)

    def test_monitor_probe_wired(self):
        mon = (REPO / "functions" / "_lib" / "opsMonitor.js").read_text(encoding="utf-8")
        self.assertIn("probeSingleDetailOps", mon)
        self.assertIn("single_detail_ops", mon)
        dash = (REPO / "functions" / "_lib" / "opsDashboard.js").read_text(encoding="utf-8")
        self.assertIn("ALT-SD01", dash)
        self.assertIn("single-detail-runbook.md", dash)

    def test_list_and_ui_untouched(self):
        races = (REPO / "public" / "races.html").read_text(encoding="utf-8")
        self.assertNotIn("single-detail.js", races)
        race = (REPO / "public" / "race.html").read_text(encoding="utf-8")
        # I3 wiring remains; I4 must not remove it
        self.assertIn("single-detail.js", race)
        ui = (REPO / "public" / "assets" / "api" / "ui-features.js").read_text(encoding="utf-8")
        self.assertRegex(ui, r"single_ai_detail:\s*false")

    def test_ops_docs_present(self):
        ops = REPO / "docs" / "ops"
        for name in (
            "single-detail-operation-guide.md",
            "single-detail-alert-rules.md",
            "single-detail-metrics.md",
            "single-detail-dashboard.md",
            "single-detail-runbook.md",
        ):
            self.assertTrue((ops / name).is_file(), name)
        self.assertTrue(
            (REPO / "docs" / "research" / "v109-i4-governance.md").is_file()
        )
        self.assertTrue(
            (REPO / "docs" / "research" / "v109-i4-operational-readiness.md").is_file()
        )


if __name__ == "__main__":
    unittest.main()
