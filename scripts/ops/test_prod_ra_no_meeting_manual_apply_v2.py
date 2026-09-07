# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "prod_ra_no_meeting_manual_apply_v2",
    Path(__file__).resolve().parent / "prod-ra-no-meeting-manual-apply-v2.py",
)
_MOD = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MOD)
apply_hunk1_provider = _MOD.apply_hunk1_provider
apply_hunk2_runner = _MOD.apply_hunk2_runner
decide_pre_run_action = _MOD.decide_pre_run_action
Stop = _MOD.Stop
HELPER_SRC = _MOD.HELPER_SRC


class CaseRuleTest(unittest.TestCase):
    def test_case_a_nonempty_runs(self):
        self.assertEqual(decide_pre_run_action([{"race_id": "x"}] * 36, {}), "run")

    def test_case_b_true_no_meeting_skips(self):
        self.assertEqual(
            decide_pre_run_action(
                [],
                {"EXPECTED_RACE_COUNT": 0, "SETTLED_RACE_COUNT": 0},
            ),
            "skip",
        )

    def test_case_c_final_predictions_runs(self):
        self.assertEqual(
            decide_pre_run_action(
                [],
                {"EXPECTED_RACE_COUNT": 4, "SETTLED_RACE_COUNT": 0},
            ),
            "run",
        )

    def test_case_c_race_results_runs(self):
        self.assertEqual(
            decide_pre_run_action(
                [],
                {"EXPECTED_RACE_COUNT": 0, "SETTLED_RACE_COUNT": 3},
            ),
            "run",
        )

    def test_case_d_e_failure_runs(self):
        self.assertEqual(decide_pre_run_action("FAILURE", {}), "run")
        self.assertEqual(
            decide_pre_run_action(
                "FAILURE",
                {"EXPECTED_RACE_COUNT": 0, "SETTLED_RACE_COUNT": 0},
            ),
            "run",
        )


class HunkSafetyTest(unittest.TestCase):
    def test_helper_does_not_import_settlement_or_sql(self):
        self.assertNotIn("build_day_settlement", HELPER_SRC)
        self.assertNotIn("SELECT ", HELPER_SRC)
        self.assertIn("fetch_pi_race_catalog", HELPER_SRC)
        self.assertIn("count_unsettled_races", HELPER_SRC)
        self.assertIn("catalog_races=[]", HELPER_SRC)
        self.assertIn("NO_CATALOG_EXPECTED", HELPER_SRC)

    def test_hunk1_provider(self):
        src = (
            "        catalog = fetch_pi_race_catalog(race_date)\n"
            "        if not catalog:\n"
            "            raise NetkeibaResultError(f\"PI catalog empty for {race_date}\")\n"
            "        for race in catalog:\n"
            "            rows.append(race)\n"
        )
        out = apply_hunk1_provider(src)
        self.assertIn("return []", out)
        self.assertNotIn("PI catalog empty", out)
        self.assertIn("        for race in catalog:\n", out)

    def test_hunk2_common_job_loop(self):
        src = (
            "from app.ops import ra_cadence\n"
            "\n"
            "def _load_race_days():\n"
            "    return set()\n"
            "\n"
            "def run_auto():\n"
            "    results = []\n"
            "    jobs = plan_auto_jobs()\n"
            "    svc = get_result_automation()\n"
            "    for job in jobs:\n"
            "        out = svc.run(\n"
            "            job[\"race_date\"],\n"
            "            trigger=job.get(\"trigger\"),\n"
            "            force=True,\n"
            "        )\n"
            "        results.append(out)\n"
            "    return results\n"
        )
        out = apply_hunk2_runner(src)
        self.assertIn("PROD_RA_NO_MEETING_PRE_RUN_GATE_V2", out)
        self.assertIn("from app.ops.netkeiba_results import", out)
        self.assertIn("from app.ops.result_day_contract import NO_CATALOG_EXPECTED", out)
        self.assertNotIn("from app.ops.result_day_contract import build_day_settlement", out)
        self.assertEqual(out.count("out = svc.run("), 1)
        self.assertIn("if _gate.get(\"action\") == \"skip\":", out)
        self.assertIn("continue", out)
        self.assertIn("for job in jobs:", out)
        self.assertNotIn("build_day_settlement(", out)

    def test_hunk2_uses_existing_is_race_day(self):
        src = (
            "from app.ops import ra_cadence\n"
            "\n"
            "def _is_race_day(d):\n"
            "    return True\n"
            "\n"
            "def run_auto():\n"
            "    results = []\n"
            "    for job in jobs:\n"
            "        out = svc.run(job[\"race_date\"], force=True)\n"
            "    return results\n"
        )
        out = apply_hunk2_runner(src)
        self.assertIn("_is_race_day(job[\"race_date\"])", out)

    def test_hunk2_stops_without_common_site(self):
        src = (
            "from app.ops import ra_cadence\n"
            "def _load_race_days():\n"
            "    return set()\n"
            "def run_auto():\n"
            "    svc.run(today)\n"
            "    svc.run(yesterday)\n"
        )
        with self.assertRaises(Stop):
            apply_hunk2_runner(src)


if __name__ == "__main__":
    unittest.main()
