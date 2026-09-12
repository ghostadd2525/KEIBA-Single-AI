# -*- coding: utf-8 -*-
"""Step-1 deploy prep: 022 already applied, POST stays disabled.

Local HTTP only. Does not touch Production. Does not enable systemd env.
"""
from __future__ import annotations

import inspect
import os
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.ops.helpers import http_json, isolated_env, running_server

OWNER_MIGRATIONS = (
    "001_init",
    "002_race_identity",
    "003_supply_platform",
    "004_user_domain",
    "005_results_eval",
    "006_result_automation",
    "007_collect_c0",
    "008_collect_contract_1_1",
    "009_user_race_results",
    "010_user_progress_audit",
    "011_research_evidence",
    "012_research_snapshot_features",
    "013_research_prediction_corpus",
    "014_research_historical_ingest",
    "015_research_race_meta",
    "016_research_knowledge_base",
    "017_research_knowledge_validation",
    "018_research_candidate_review",
    "019_final_predictions",
    "020_research_corpus_canonical",
    "020_user_challenge_lifecycle",
    "021_user_challenge_point_events",
    "022_prediction_run_idempotency",
)
OWNER_PRED_COLUMNS = (
    "id",
    "race_id",
    "core_race_id",
    "engine_source",
    "fallback_reason",
    "model_version",
    "bundle_json",
    "created_at",
)
NEW_COLS = (
    "idempotency_key",
    "persist_source",
    "input_snapshot_hash",
    "prediction_semantic_hash",
)


def _seed_prod_like_022_applied(path: Path, rows: int = 2) -> None:
    conn = sqlite3.connect(str(path))
    cols = ", ".join(
        "id INTEGER PRIMARY KEY" if c == "id" else "%s TEXT" % c for c in OWNER_PRED_COLUMNS
    )
    conn.execute("CREATE TABLE schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
    conn.execute("CREATE TABLE predictions(%s)" % cols)
    conn.execute("CREATE INDEX idx_predictions_race ON predictions(race_id, created_at)")
    for col in NEW_COLS:
        conn.execute("ALTER TABLE predictions ADD COLUMN %s TEXT" % col)
    conn.execute(
        "CREATE UNIQUE INDEX uq_predictions_idempotency_key_not_null "
        "ON predictions(idempotency_key) WHERE idempotency_key IS NOT NULL"
    )
    for ver in OWNER_MIGRATIONS:
        conn.execute("INSERT INTO schema_migrations VALUES (?, 't')", (ver,))
    for i in range(rows):
        conn.execute(
            "INSERT INTO predictions(race_id, created_at) VALUES (?, 't')",
            ("local-%d" % i,),
        )
    conn.commit()
    conn.close()


def _snapshot(path: Path) -> tuple[list[str], list[str], int, str]:
    conn = sqlite3.connect(str(path))
    cols = [r[1] for r in conn.execute("PRAGMA table_info(predictions)")]
    versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]
    rows = int(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])
    idx_sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name='uq_predictions_idempotency_key_not_null'"
    ).fetchone()
    conn.close()
    return cols, versions, rows, (idx_sql[0] if idx_sql else "")


class AlreadyAppliedMigrateTests(unittest.TestCase):
    def test_migrate_noop_without_022_flag(self):
        with isolated_env(allow_migration_019=False, allow_migration_022=False):
            os.environ.pop("PREDICTION_RUNS_ENABLED", None)
            os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
            os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_019", None)
            db = Path(os.environ["EXPECT_AI_DB_PATH"])
            _seed_prod_like_022_applied(db)
            before = _snapshot(db)
            from app.data.db import migrate, prediction_run_schema_ready, repair_prediction_run_schema

            applied = migrate()
            after = _snapshot(db)
            self.assertEqual(applied, [])
            self.assertEqual(before, after)
            self.assertTrue(prediction_run_schema_ready())
            self.assertEqual(len(after[1]), 23)
            self.assertEqual(len(after[0]), 12)
            src = inspect.getsource(repair_prediction_run_schema)
            self.assertIn("DROP INDEX IF EXISTS", src)

    def test_migrate_complete_with_flag_still_noop_when_row_exists(self):
        with isolated_env(allow_migration_022=True):
            db = Path(os.environ["EXPECT_AI_DB_PATH"])
            _seed_prod_like_022_applied(db)
            before = _snapshot(db)
            from app.data.db import migrate

            applied = migrate()
            after = _snapshot(db)
            self.assertEqual(applied, [])
            self.assertEqual(before[0], after[0])
            self.assertEqual(before[2], after[2])
            self.assertIn("022_prediction_run_idempotency", after[1])
            self.assertNotIn("019_prediction_run_idempotency", after[1])

    def test_superseded_019_not_applied(self):
        migr = Path(__file__).resolve().parents[2] / "app" / "data" / "migrations"
        self.assertFalse((migr / "019_prediction_run_idempotency.sql").exists())
        self.assertTrue((migr / "022_prediction_run_idempotency.sql").exists())


class DisabledPostGateTests(unittest.TestCase):
    def test_unset_env_is_disabled_503_no_infer_no_loader_no_insert(self):
        os.environ.pop("PREDICTION_RUNS_ENABLED", None)
        infer_calls = {"n": 0}
        insert_calls = {"n": 0}

        def boom_infer(*_a, **_k):
            infer_calls["n"] += 1
            raise AssertionError("infer must not run")

        def boom_insert(*_a, **_k):
            insert_calls["n"] += 1
            raise AssertionError("INSERT must not run")

        with running_server(allow_migration_019=False, prediction_runs=False) as base:
            from app.data.db import connect
            from app.main import Handler

            src = inspect.getsource(Handler._handle_prediction_runs_post)
            self.assertIn("if not prediction_runs_enabled()", src)
            self.assertLess(
                src.find("if not prediction_runs_enabled()"),
                src.find("handle_post_prediction_run("),
            )

            conn = connect()
            before = int(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])
            conn.close()
            with (
                patch("app.predictions.runs.handle_post_prediction_run", side_effect=boom_infer),
                patch("app.data.repository.PredictionRepository.save_idempotent", side_effect=boom_insert),
            ):
                status, body = http_json(
                    f"{base}/v1/prediction-runs",
                    method="POST",
                    body={"race_id": "20260719_hanshin_11"},
                )
            self.assertEqual(status, 503, body)
            self.assertEqual(body.get("error", {}).get("code"), "PREDICTION_RUNS_DISABLED")
            self.assertEqual(infer_calls["n"], 0)
            self.assertEqual(insert_calls["n"], 0)
            conn = connect()
            after = int(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])
            conn.close()
            self.assertEqual(before, after)

    def test_get_shape_and_zero_write_default_server(self):
        os.environ.pop("PREDICTION_RUNS_ENABLED", None)
        with running_server(allow_migration_019=False, prediction_runs=False) as base:
            from app.data.db import connect

            conn = connect()
            before = int(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])
            conn.close()
            st, body = http_json(base + "/v1/predictions")
            self.assertEqual(st, 200, body)
            self.assertTrue(body.get("ok"))
            self.assertIn("data", body)
            st2, body2 = http_json(base + "/v1/predictions/20260719_hanshin_11")
            self.assertEqual(st2, 200, body2)
            data = body2.get("data") or {}
            self.assertNotIn("prediction_id", data)
            self.assertNotIn("replayed", body2)
            self.assertIn("evaluation", data)
            conn = connect()
            after = int(conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0])
            conn.close()
            self.assertEqual(before, after)


class ExistingWritePathNullColsTests(unittest.TestCase):
    def test_conversation_and_legacy_inserts_leave_new_cols_null(self):
        with isolated_env(allow_migration_022=True):
            os.environ.pop("PREDICTION_RUNS_ENABLED", None)
            from app.conversation.service import ConversationService
            from app.data.db import connect, migrate
            from app.data.repository import PredictionRepository

            first = migrate()
            self.assertIn("022_prediction_run_idempotency", first)
            os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)
            self.assertEqual(migrate(), [])
            svc = ConversationService()
            out = svc.chat({"message": "hello-no-race", "session_id": "s-null-1"})
            self.assertIn("reply", out)
            repo = PredictionRepository()
            repo.save(
                race_id="legacy-1",
                bundle={
                    "schema_version": "single-prediction-bundle/2.0",
                    "race_id": "legacy-1",
                    "evaluation": {
                        "runners": [
                            {"horse_number": 1, "win_prob": 0.5, "model_rank": 1, "mark": "honmei"}
                        ]
                    },
                },
                engine_source="real_ai",
            )
            conn = connect()
            try:
                conn.execute(
                    """
                    INSERT INTO predictions(
                      race_id, engine_source, fallback_reason, model_version, bundle_json, created_at
                    ) VALUES (?,?,?,?,?,?)
                    """,
                    ("challenge-1", "real_ai", None, "m", "{}", "t"),
                )
                conn.execute(
                    """
                    INSERT INTO predictions(
                      race_id, engine_source, fallback_reason, model_version, bundle_json, created_at
                    ) VALUES (?,?,?,?,?,?)
                    """,
                    ("ra-1", "real_ai", None, "m", "{}", "t"),
                )
                conn.commit()
                rows = conn.execute(
                    "SELECT race_id, idempotency_key, persist_source, "
                    "input_snapshot_hash, prediction_semantic_hash FROM predictions"
                ).fetchall()
                self.assertGreaterEqual(len(rows), 2)
                for row in rows:
                    self.assertIsNone(row["idempotency_key"])
                    self.assertIsNone(row["persist_source"])
                    self.assertIsNone(row["input_snapshot_hash"])
                    self.assertIsNone(row["prediction_semantic_hash"])
            finally:
                conn.close()

    def test_v4_connector_has_no_predictions_insert(self):
        from app.conversation.v4 import orchestrator as orch

        src = inspect.getsource(orch)
        self.assertNotIn("INSERT INTO predictions", src)
        self.assertNotIn("save_idempotent", src)

    def test_legacy_save_source_omits_new_cols(self):
        from app.data.repository import PredictionRepository
        from app.challenge import service as challenge_service
        from app.ops import result_automation as ra

        save_src = inspect.getsource(PredictionRepository.save)
        self.assertNotIn("idempotency_key", save_src)
        ch_src = inspect.getsource(challenge_service)
        self.assertIn("INSERT INTO predictions(", ch_src)
        self.assertNotIn("idempotency_key", ch_src)
        ra_src = inspect.getsource(ra.ResultAutomationService._cache_pi_prediction)
        self.assertIn("INSERT INTO predictions(", ra_src)
        self.assertNotIn("idempotency_key", ra_src)


if __name__ == "__main__":
    unittest.main()
