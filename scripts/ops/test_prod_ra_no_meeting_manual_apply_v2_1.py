# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock

_SPEC = importlib.util.spec_from_file_location(
    "prod_ra_no_meeting_manual_apply_v2_1",
    Path(__file__).resolve().parent / "prod-ra-no-meeting-manual-apply-v2-1.py",
)
_MOD = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MOD)
apply_v21_runner = _MOD.apply_v21_runner
Stop = _MOD.Stop
OLD = _MOD.OLD
NEW = _MOD.NEW

V2_APPLIED_SNIPPET = '''
from app.ops import ra_cadence

def _load_race_days():
    return set()

def run_auto():
    results = []
    days = _load_race_days()
    def is_race_day_fn(d: str) -> bool:
        return (not days) or (d in days)
    jobs = plan_auto_jobs()
    svc = get_result_automation()
    for job in jobs:
        _pre_run_days = _load_race_days()
        _gate = _pre_run_catalog_gate(
            job["race_date"],
            ((not _pre_run_days) or (job["race_date"] in _pre_run_days))
        )
        if _gate.get("action") == "skip":
            results.append({
                "status": "skipped",
                "run_status": "NOOP",
                "race_date": job["race_date"],
                "reason": _gate.get("reason"),
            })
            continue
        out = svc.run(
            job["race_date"],
            trigger=job.get("trigger"),
            force=True,
        )
        results.append(out)
    return results
'''


def _simulate_job_loop(jobs, gate_fn, svc_run):
    """Production-shaped common loop after v2.1 correction."""
    results = []
    days = set()

    def is_race_day_fn(d: str) -> bool:
        return (not days) or (d in days)

    for job in jobs:
        _gate = gate_fn(job["race_date"], is_race_day_fn(job["race_date"]))
        if _gate.get("action") == "skip":
            results.append(
                {
                    "status": "skipped",
                    "run_status": "NOOP",
                    "race_date": job["race_date"],
                    "reason": _gate.get("reason") or "NO_CATALOG_EXPECTED",
                    "result_sync": False,
                }
            )
            continue
        out = svc_run(
            job["race_date"],
            trigger=job.get("trigger"),
            force=True,
        )
        results.append(out)
    return results


class V21HunkTest(unittest.TestCase):
    def test_exact_one_replacement(self):
        out = apply_v21_runner(V2_APPLIED_SNIPPET)
        self.assertEqual(out.count(OLD), 0)
        self.assertEqual(out.count("_pre_run_days"), 0)
        self.assertEqual(out.count('is_race_day_fn(job["race_date"])'), 1)
        self.assertIn("_gate = _pre_run_catalog_gate(", out)
        self.assertIn("for job in jobs:", out)
        self.assertEqual(out.count("out = svc.run("), 1)
        self.assertIn("def is_race_day_fn(d: str) -> bool:", out)

    def test_stop_if_old_missing(self):
        with self.assertRaises(Stop):
            apply_v21_runner("is_race_day_fn(job[\"race_date\"])\n")


class V21RuntimePathTest(unittest.TestCase):
    def test_case_b_success_empty_does_not_call_svc_run(self):
        svc = Mock(name="svc.run")

        def gate(race_date, is_race_day):
            self.assertIsInstance(is_race_day, bool)
            return {
                "action": "skip",
                "reason": "NO_CATALOG_EXPECTED",
                "EXPECTED_RACE_COUNT": 0,
                "SETTLED_RACE_COUNT": 0,
            }

        jobs = [
            {"race_date": "2026-09-07", "kind": "today"},
            {"race_date": "2026-09-06", "kind": "morning"},
            {"race_date": "2026-09-07", "kind": "recovery"},
        ]
        out = _simulate_job_loop(jobs, gate, svc)
        svc.assert_not_called()
        self.assertEqual(len(out), 3)
        self.assertTrue(all(r["run_status"] == "NOOP" for r in out))
        self.assertTrue(all(r["reason"] == "NO_CATALOG_EXPECTED" for r in out))

    def test_case_a_nonempty_calls_svc_run(self):
        svc = Mock(name="svc.run", side_effect=lambda *a, **k: {"run_status": "COMPLETED"})

        def gate(race_date, is_race_day):
            return {"action": "run", "reason": "catalog_present", "catalog_count": 36}

        jobs = [
            {"race_date": "2026-09-06", "kind": "today", "trigger": "scheduled"},
            {"race_date": "2026-09-05", "kind": "morning", "trigger": "retry"},
            {"race_date": "2026-09-06", "kind": "recovery", "trigger": "retry"},
        ]
        out = _simulate_job_loop(jobs, gate, svc)
        self.assertEqual(svc.call_count, 3)
        self.assertTrue(all(r["run_status"] == "COMPLETED" for r in out))

    def test_corrected_source_does_not_nameerror(self):
        ns = {}
        calls = []

        def _pre_run_catalog_gate(race_date, is_race_day):
            calls.append((race_date, is_race_day))
            if race_date == "2026-09-07":
                return {"action": "skip", "reason": "NO_CATALOG_EXPECTED"}
            return {"action": "run", "reason": "catalog_present"}

        def plan_auto_jobs():
            return [
                {"race_date": "2026-09-07", "trigger": "scheduled"},
                {"race_date": "2026-09-06", "trigger": "retry"},
            ]

        class Svc:
            def run(self, race_date, trigger=None, force=False):
                return {"run_status": "COMPLETED", "race_date": race_date}

        src = apply_v21_runner(V2_APPLIED_SNIPPET)
        self.assertNotIn("_pre_run_days", src)
        src = src.replace("from app.ops import ra_cadence\n", "")
        ns = {
            "ra_cadence": object(),
            "_pre_run_catalog_gate": _pre_run_catalog_gate,
            "plan_auto_jobs": plan_auto_jobs,
            "get_result_automation": lambda: Svc(),
        }
        exec(src, ns)
        out = ns["run_auto"]()
        self.assertEqual(len(calls), 2)
        self.assertEqual(out[0]["run_status"], "NOOP")
        self.assertEqual(out[1]["run_status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
