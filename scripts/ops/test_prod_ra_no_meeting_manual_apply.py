# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "prod_ra_no_meeting_manual_apply",
    Path(__file__).resolve().parent / "prod-ra-no-meeting-manual-apply.py",
)
_MOD = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MOD)
apply_hunk1_provider = _MOD.apply_hunk1_provider
apply_hunk23_runner = _MOD.apply_hunk23_runner
Stop = _MOD.Stop


class Hunk1Test(unittest.TestCase):
    def test_single_line_raise(self):
        src = (
            "        catalog = fetch_pi_race_catalog(race_date)\n"
            "        if not catalog:\n"
            "            raise NetkeibaResultError(f\"PI catalog empty for {race_date}\")\n"
            "        rows = []\n"
            "        for race in catalog:\n"
            "            rows.append(race)\n"
        )
        out = apply_hunk1_provider(src)
        self.assertIn("if not catalog:\n            return []\n", out)
        self.assertNotIn("PI catalog empty", out)
        self.assertIn("        for race in catalog:\n", out)

    def test_multiline_raise(self):
        src = (
            "        if not catalog:\n"
            "            raise NetkeibaResultError(\n"
            "                f\"PI catalog empty for {race_date}\"\n"
            "            )\n"
            "        for race in catalog:\n"
            "            pass\n"
        )
        out = apply_hunk1_provider(src)
        self.assertIn("return []", out)
        self.assertNotIn("PI catalog empty", out)
        self.assertIn("        for race in catalog:\n", out)

    def test_zero_or_two_raises_stop(self):
        with self.assertRaises(Stop):
            apply_hunk1_provider("if not catalog:\n    return []\n")
        src = (
            "if not catalog:\n"
            "    raise NetkeibaResultError(f\"PI catalog empty for {race_date}\")\n"
            "if not catalog:\n"
            "    raise NetkeibaResultError(f\"PI catalog empty for {race_date}\")\n"
        )
        with self.assertRaises(Stop):
            apply_hunk1_provider(src)


class Hunk23Test(unittest.TestCase):
    def test_wraps_post_morning_recovery(self):
        src = (
            "from app.ops.result_day_contract import NO_CATALOG_EXPECTED\n"
            "from app.ops.result_day_contract import build_day_settlement\n"
            "\n"
            "def run_auto():\n"
            "    results = []\n"
            "    svc = get_result_automation()\n"
            "    if decision.get('run'):\n"
            "        out = svc.run(today, trigger='scheduled', force=True)\n"
            "        results.append(out)\n"
            "    results.append(\n"
            "        svc.run(\n"
            "            yesterday,\n"
            "            trigger='retry',\n"
            "            force=True,\n"
            "        )\n"
            "    )\n"
            "    results.append(\n"
            "        svc.run(\n"
            "            failed_date,\n"
            "            trigger='retry',\n"
            "            force=True,\n"
            "        )\n"
            "    )\n"
            "    return results\n"
        )
        out = apply_hunk23_runner(src)
        self.assertIn("PROD_RA_NO_MEETING_PRE_RUN_GATE_V1", out)
        self.assertEqual(out.count("_gated_svc_run(svc, results, today"), 1)
        self.assertEqual(out.count("_gated_svc_run(svc, results, \n            yesterday"), 1)
        self.assertEqual(out.count("_gated_svc_run(svc, results, \n            failed_date"), 1)
        self.assertEqual(out.count("svc.run("), 1)
        self.assertIn("build_day_settlement", out)
        self.assertIn("NO_CATALOG_EXPECTED", out)

    def test_stop_without_build_day_settlement(self):
        src = "def run_auto():\n    svc.run(today)\n"
        with self.assertRaises(Stop):
            apply_hunk23_runner(src)


if __name__ == "__main__":
    unittest.main()
