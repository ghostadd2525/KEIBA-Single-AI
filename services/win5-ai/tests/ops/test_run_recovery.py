# -*- coding: utf-8 -*-
"""OPS-Hardening — orphan recovery + result_automation health."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


class OrphanRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.miss_dir = Path(self.tmp.name) / "miss"
        self.imp_dir = Path(self.tmp.name) / "improvement"
        os.environ["EXPECT_AI_DB_PATH"] = str(self.db_path)
        os.environ["EXPECT_MISS_EVIDENCE_DIR"] = str(self.miss_dir)
        os.environ["EXPECT_IMPROVEMENT_EVIDENCE_DIR"] = str(self.imp_dir)
        os.environ["EXPECT_RA_ACTIVE_STALE_MINUTES"] = "60"
        from app.data import db as app_db

        app_db.migrate()

    def tearDown(self):
        self.tmp.cleanup()
        for k in (
            "EXPECT_AI_DB_PATH",
            "EXPECT_MISS_EVIDENCE_DIR",
            "EXPECT_IMPROVEMENT_EVIDENCE_DIR",
            "EXPECT_RA_ACTIVE_STALE_MINUTES",
        ):
            os.environ.pop(k, None)
        from app.ops import result_automation as ra

        ra._service = None

    def test_fail_orphan_active_then_retry_with_parent(self):
        from app.data import db as app_db
        from app.ops import state_machine as sm
        from app.ops.result_automation import ResultAutomationService
        from app.ops.run_recovery import fail_orphan_active_runs

        conn = app_db.connect()
        started = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        conn.execute(
            """
            INSERT INTO result_automation_runs(
              race_date, status, trigger, attempt, max_attempts, started_at
            ) VALUES (?,?,?,?,?,?)
            """,
            ("2026-07-19", sm.EVALUATING, sm.TRIGGER_SCHEDULED, 1, 5, started),
        )
        conn.commit()
        orphan_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        conn.close()

        failed = fail_orphan_active_runs(reason="test_orphan")
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["run_id"], orphan_id)

        conn = app_db.connect()
        row = conn.execute(
            "SELECT status, error_json FROM result_automation_runs WHERE id=?",
            (orphan_id,),
        ).fetchone()
        self.assertEqual(row["status"], sm.FAILED)
        err = json.loads(row["error_json"])
        self.assertEqual(err["previous_status"], sm.EVALUATING)
        conn.close()

        # seed minimal data for retry
        conn = app_db.connect()
        conn.execute(
            """
            INSERT INTO race_results(
              race_id, race_date, venue, winner_horse_number, field_size,
              finalized_at, source, result_json
            ) VALUES (?,?,?,?,?, datetime('now'), ?, ?)
            """,
            (
                "2026-07-19-04-11",
                "2026-07-19",
                "福島",
                2,
                4,
                "test",
                json.dumps({"winner_name": "W"}),
            ),
        )
        conn.execute(
            """
            INSERT INTO predictions(race_id, engine_source, bundle_json, created_at)
            VALUES (?,?,?, datetime('now'))
            """,
            (
                "2026-07-19-04-11",
                "real_ai",
                json.dumps(
                    {
                        "evaluation": {
                            "runners": [
                                {"horse_number": 7, "model_rank": 1},
                                {"horse_number": 2, "model_rank": 2},
                            ]
                        },
                        "ai_confidence": {"score": 0.9},
                        "explain": {"narrative": "n"},
                    }
                ),
            ),
        )
        conn.commit()
        conn.close()

        svc = ResultAutomationService()
        result = svc.run(
            "2026-07-19",
            trigger=sm.TRIGGER_RETRY,
            parent_run_id=orphan_id,
            force=True,
            skip_result_sync=True,
        )
        self.assertNotEqual(result["run_id"], orphan_id)
        conn = app_db.connect()
        child = conn.execute(
            "SELECT parent_run_id, trigger FROM result_automation_runs WHERE id=?",
            (result["run_id"],),
        ).fetchone()
        conn.close()
        self.assertEqual(child["parent_run_id"], orphan_id)
        self.assertEqual(child["trigger"], sm.TRIGGER_RETRY)

    def test_health_detects_failed_and_missing_manifest(self):
        from app.data import db as app_db
        from app.ops import state_machine as sm
        from app.ops.run_recovery import collect_result_automation_health

        conn = app_db.connect()
        today = datetime.now(timezone.utc).date().isoformat()
        conn.execute(
            """
            INSERT INTO result_automation_runs(
              race_date, status, trigger, attempt, max_attempts, started_at, finished_at
            ) VALUES (?,?,?,?,?, datetime('now'), datetime('now'))
            """,
            (today, sm.FAILED, sm.TRIGGER_MANUAL, 1, 5),
        )
        conn.commit()
        conn.close()

        health = collect_result_automation_health()
        self.assertFalse(health["ok"])
        self.assertEqual(health["status"], "unhealthy")
        self.assertTrue(health["detail"]["failed_latest"])

    def test_health_detects_stale_active(self):
        from app.data import db as app_db
        from app.ops import state_machine as sm
        from app.ops.run_recovery import collect_result_automation_health

        conn = app_db.connect()
        started = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        conn.execute(
            """
            INSERT INTO result_automation_runs(
              race_date, status, trigger, attempt, max_attempts, started_at
            ) VALUES (?,?,?,?,?,?)
            """,
            ("2026-07-19", sm.RESULT_SYNCING, sm.TRIGGER_SCHEDULED, 1, 5, started),
        )
        conn.commit()
        conn.close()

        health = collect_result_automation_health()
        self.assertFalse(health["ok"])
        self.assertTrue(health["detail"]["stale_active"])


if __name__ == "__main__":
    unittest.main()
