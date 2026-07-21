#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OPS-GameDay validation harness — outputs JSON report (no prod changes)."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import traceback
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data import db as app_db
from app.ops import state_machine as sm
from app.ops.result_automation import ResultAutomationService
from app.ops.result_providers import CsvResultProvider
from app.ops.evidence.registry import registered_types


def fresh_env():
    td = tempfile.mkdtemp(prefix="gameday-")
    db = Path(td) / "test.db"
    miss = Path(td) / "miss"
    imp = Path(td) / "improvement"
    os.environ["EXPECT_AI_DB_PATH"] = str(db)
    os.environ["EXPECT_MISS_EVIDENCE_DIR"] = str(miss)
    os.environ["EXPECT_IMPROVEMENT_EVIDENCE_DIR"] = str(imp)
    app_db.migrate()
    return td, db, miss, imp


def seed_race(conn, race_id="2026-07-19-04-11", winner=2, bundle=None, engine="real_ai", fb=None):
    conn.execute(
        """
        INSERT INTO race_results(race_id,race_date,venue,winner_horse_number,field_size,finalized_at,source,result_json)
        VALUES (?,?,?,?,?,datetime('now'),?,?)
        """,
        (race_id, "2026-07-19", "福島", winner, 4, "seed", json.dumps({"winner_name": "W"})),
    )
    if bundle is None:
        bundle = {
            "evaluation": {
                "runners": [
                    {"horse_number": 7, "model_rank": 1},
                    {"horse_number": winner, "model_rank": 2},
                ]
            },
            "ai_confidence": {"score": 0.9},
            "explain": {"narrative": "n", "meta": {"feature_source": "platform"}},
        }
    conn.execute(
        """
        INSERT INTO predictions(race_id,engine_source,fallback_reason,bundle_json,created_at)
        VALUES (?,?,?,?,datetime('now'))
        """,
        (race_id, engine, fb, json.dumps(bundle)),
    )
    conn.commit()


def run_status(conn, run_id):
    row = conn.execute(
        "SELECT status, trigger, parent_run_id, attempt FROM result_automation_runs WHERE id=?",
        (run_id,),
    ).fetchone()
    return dict(row) if row else {}


def scenario_happy_path():
    td, db, miss, imp = fresh_env()
    conn = app_db.connect()
    seed_race(conn)
    conn.close()
    svc = ResultAutomationService(provider=CsvResultProvider(data_dir=Path(td)))
    r = svc.run("2026-07-19", trigger=sm.TRIGGER_SCHEDULED, force=True, skip_result_sync=True)
    manifest_ok = all(
        (imp / "manifest" / "2026-07-19" / f).exists() for f in ("run.json", "summary.json", "index.json")
    )
    dual = (miss / "2026-07-19" / "2026-07-19-04-11.json").exists() and (
        imp / "miss" / "2026-07-19" / "2026-07-19-04-11.json"
    ).exists()
    conn = app_db.connect()
    evals = conn.execute("SELECT COUNT(*) c FROM race_evaluations").fetchone()["c"]
    self_eval = conn.execute("SELECT COUNT(*) c FROM self_evaluation_runs").fetchone()["c"]
    conn.close()
    return {
        "name": "happy_path",
        "ok": r["run_status"] == sm.COMPLETED and manifest_ok and dual and evals >= 1,
        "run_status": r["run_status"],
        "manifest_ok": manifest_ok,
        "dual_write": dual,
        "evals": evals,
        "self_eval": self_eval,
    }


def scenario_csv_missing():
    td, db, miss, imp = fresh_env()
    conn = app_db.connect()
    seed_race(conn)
    conn.close()
    svc = ResultAutomationService(provider=CsvResultProvider(data_dir=Path(td) / "empty"))
    r = svc.run("2026-07-19", trigger=sm.TRIGGER_SCHEDULED, force=True, skip_result_sync=False)
    # degraded: existing results used
    sync_ev = list((imp / "result_sync_failed" / "2026-07-19").glob("*.json")) if (
        imp / "result_sync_failed" / "2026-07-19"
    ).exists() else []
    return {
        "name": "result_csv_missing",
        "ok": r["run_status"] in (sm.COMPLETED, sm.DEGRADED),
        "run_status": r["run_status"],
        "result_sync_failed_events": len(sync_ev),
        "evaluated": r.get("races_evaluated", 0),
    }


def scenario_csv_missing_no_results():
    td, db, miss, imp = fresh_env()
    svc = ResultAutomationService(provider=CsvResultProvider(data_dir=Path(td) / "empty"))
    r = svc.run("2026-07-19", trigger=sm.TRIGGER_SCHEDULED, force=True)
    sync_ev = list((imp / "result_sync_failed" / "2026-07-19").glob("*.json")) if (
        imp / "result_sync_failed" / "2026-07-19"
    ).exists() else []
    return {
        "name": "result_provider_fail_no_db",
        "ok": r["run_status"] == sm.FAILED and len(sync_ev) >= 1,
        "run_status": r["run_status"],
        "events": r.get("event_counts", {}),
    }


def scenario_prediction_missing():
    td, db, miss, imp = fresh_env()
    conn = app_db.connect()
    conn.execute(
        """
        INSERT INTO race_results(race_id,race_date,venue,winner_horse_number,field_size,finalized_at,source,result_json)
        VALUES (?,?,?,?,?,datetime('now'),?,?)
        """,
        ("r-no-pred", "2026-07-19", "阪神", 1, 8, "seed", "{}"),
    )
    conn.commit()
    conn.close()
    svc = ResultAutomationService()
    r = svc.run("2026-07-19", trigger=sm.TRIGGER_MANUAL, force=True, skip_result_sync=True)
    ev = list((imp / "prediction_failed" / "2026-07-19").glob("*.json")) if (
        imp / "prediction_failed" / "2026-07-19"
    ).exists() else []
    return {
        "name": "prediction_missing",
        "ok": r["run_status"] == sm.DEGRADED and len(ev) >= 1,
        "run_status": r["run_status"],
        "prediction_failed_events": len(ev),
    }


def scenario_feature_missing():
    td, db, miss, imp = fresh_env()
    conn = app_db.connect()
    bundle = {
        "evaluation": {"runners": [{"horse_number": 1, "model_rank": 1}]},
        "ai_confidence": {"score": 0.5},
        "explain": {"meta": {"feature_source": "missing"}},
    }
    seed_race(conn, race_id="r-feat", winner=1, bundle=bundle, engine="mock_fallback", fb="feature_missing")
    conn.close()
    svc = ResultAutomationService()
    r = svc.run("2026-07-19", trigger=sm.TRIGGER_MANUAL, force=True, skip_result_sync=True)
    ev = list((imp / "feature_missing" / "2026-07-19").glob("*.json")) if (
        imp / "feature_missing" / "2026-07-19"
    ).exists() else []
    return {
        "name": "feature_missing",
        "ok": len(ev) >= 1,
        "run_status": r["run_status"],
        "feature_missing_events": len(ev),
    }


def scenario_double_start():
    td, db, miss, imp = fresh_env()
    conn = app_db.connect()
    seed_race(conn)
    # Simulate in-progress run (process stopped mid-pipeline).
    conn.execute(
        """
        INSERT INTO result_automation_runs(
          race_date, status, trigger, attempt, max_attempts, started_at
        ) VALUES (?,?,?,?,?,datetime('now'))
        """,
        ("2026-07-19", sm.EVALUATING, sm.TRIGGER_MANUAL, 1, 5),
    )
    conn.commit()
    conn.close()
    svc = ResultAutomationService()
    blocked = False
    try:
        svc.run("2026-07-19", trigger=sm.TRIGGER_MANUAL, force=False, skip_result_sync=True)
    except RuntimeError:
        blocked = True
    return {"name": "double_start_exclusion", "ok": blocked}


def scenario_force_retry():
    td, db, miss, imp = fresh_env()
    conn = app_db.connect()
    seed_race(conn)
    conn.close()
    svc = ResultAutomationService()
    a = svc.run("2026-07-19", trigger=sm.TRIGGER_MANUAL, force=True, skip_result_sync=True)
    b = svc.run(
        "2026-07-19",
        trigger=sm.TRIGGER_RETRY,
        parent_run_id=a["run_id"],
        force=True,
        skip_result_sync=True,
    )
    return {
        "name": "force_retry_new_run_id",
        "ok": a["run_id"] != b["run_id"],
        "run_a": a["run_id"],
        "run_b": b["run_id"],
    }


def scenario_evidence_only():
    td, db, miss, imp = fresh_env()
    conn = app_db.connect()
    seed_race(conn)
    conn.close()
    svc = ResultAutomationService()
    svc.run("2026-07-19", trigger=sm.TRIGGER_MANUAL, force=True, skip_result_sync=True)
    r = svc.run(
        "2026-07-19",
        trigger=sm.TRIGGER_MANUAL,
        force=True,
        evidence_only=True,
    )
    return {
        "name": "evidence_only_reexport",
        "ok": r["run_status"] in (sm.COMPLETED, sm.DEGRADED),
        "events": r.get("event_counts", {}),
    }


def scenario_state_transitions():
    path = [
        sm.PENDING,
        sm.RESULT_SYNCING,
        sm.PREDICTION_MATCHING,
        sm.EVALUATING,
        sm.STATS_UPDATING,
        sm.SELF_EVAL_UPDATING,
        sm.EVIDENCE_EXPORTING,
        sm.COMPLETED,
    ]
    ok = all(sm.can_transition(a, b) for a, b in zip(path, path[1:]))
    return {"name": "state_machine_happy_path", "ok": ok}


def scenario_registry():
    types = registered_types()
    need = {"miss", "feature_missing", "prediction_failed", "result_sync_failed"}
    return {"name": "evidence_registry", "ok": need.issubset(set(types)), "types": types}


def main():
    scenarios = [
        scenario_state_transitions,
        scenario_registry,
        scenario_happy_path,
        scenario_csv_missing,
        scenario_csv_missing_no_results,
        scenario_prediction_missing,
        scenario_feature_missing,
        scenario_double_start,
        scenario_force_retry,
        scenario_evidence_only,
    ]
    results = []
    for fn in scenarios:
        try:
            results.append(fn())
        except Exception as exc:
            results.append({"name": fn.__name__, "ok": False, "error": str(exc), "trace": traceback.format_exc()})

    # unittest suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName("tests.ops.test_result_automation")
    runner = unittest.TextTestRunner(verbosity=0)
    ut = runner.run(suite)

    report = {
        "phase": "OPS-GameDay",
        "scenarios": results,
        "scenario_pass": sum(1 for r in results if r.get("ok")),
        "scenario_total": len(results),
        "unittest_failures": len(ut.failures),
        "unittest_errors": len(ut.errors),
        "unittest_pass": ut.testsRun - len(ut.failures) - len(ut.errors),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["scenario_pass"] == report["scenario_total"] and not ut.failures and not ut.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
