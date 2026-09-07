# -*- coding: utf-8 -*-
import json
import os
import tempfile
import unittest
from pathlib import Path

from app.ops.miss_evidence import build_miss_evidence, classify_miss
from app.ops import state_machine as sm
from app.ops.evidence.registry import build_event, registered_types
from app.ops.result_providers import CsvResultProvider


class MissEvidenceTest(unittest.TestCase):
    def test_classify_miss_top1(self):
        self.assertEqual(classify_miss(hit_at_1=False, hit_at_3=True, hit_at_5=True), "miss_top1")

    def test_classify_hit_none(self):
        self.assertIsNone(classify_miss(hit_at_1=True, hit_at_3=True, hit_at_5=True))

    def test_build_evidence(self):
        bundle = {
            "race_id": "r1",
            "race_info": {"venue": "阪神"},
            "evaluation": {
                "runners": [
                    {"horse_number": 7, "model_rank": 1},
                    {"horse_number": 3, "model_rank": 2},
                ]
            },
            "ai_confidence": {"score": 0.87},
            "explain": {"narrative": "test"},
        }
        ev = build_miss_evidence(
            race_id="r1",
            bundle=bundle,
            meta={"engine_source": "real_ai"},
            winner_horse_number=3,
            winner_name="Winner",
            hit_at_1=False,
            hit_at_3=True,
            hit_at_5=True,
        )
        self.assertIsNotNone(ev)
        assert ev is not None
        self.assertEqual(ev["miss_category"], "miss_top1")
        self.assertEqual(ev["winner"]["horse_number"], 3)


class StateMachineTest(unittest.TestCase):
    def test_happy_path_transitions(self):
        path = [
            sm.PENDING,
            sm.RESULT_SYNCING,
            sm.PREDICTION_MATCHING,
            sm.EVALUATING,
            sm.STATS_UPDATING,
            sm.SELF_EVAL_UPDATING,
            sm.EVIDENCE_EXPORTING,
            sm.USER_SETTLING,
            sm.POINT_UPDATING,
            sm.LEVEL_UPDATING,
            sm.ARCHIVING,
            sm.COMPLETED,
        ]
        for a, b in zip(path, path[1:]):
            self.assertTrue(sm.can_transition(a, b), f"{a}->{b}")

    def test_evidence_only_can_complete(self):
        self.assertTrue(sm.can_transition(sm.EVIDENCE_EXPORTING, sm.COMPLETED))

    def test_illegal(self):
        self.assertFalse(sm.can_transition(sm.PENDING, sm.COMPLETED))


class EvidenceRegistryTest(unittest.TestCase):
    def test_registered(self):
        types = registered_types()
        for t in ("miss", "feature_missing", "prediction_failed", "result_sync_failed"):
            self.assertIn(t, types)

    def test_miss_envelope(self):
        env = build_event(
            "miss",
            {
                "race_id": "r1",
                "race_date": "2026-07-19",
                "bundle": {
                    "evaluation": {
                        "runners": [
                            {"horse_number": 1, "model_rank": 1},
                            {"horse_number": 2, "model_rank": 2},
                        ]
                    },
                    "ai_confidence": {"score": 0.5},
                    "explain": {},
                },
                "meta": {"engine_source": "real_ai"},
                "winner_horse_number": 2,
                "winner_name": "W",
                "hit_at_1": False,
                "hit_at_3": True,
                "hit_at_5": True,
            },
        )
        self.assertIsNotNone(env)
        assert env is not None
        self.assertEqual(env["event_type"], "miss")
        self.assertEqual(env["schema_version"], "expect-improvement-evidence/1.0")
        self.assertIn("payload", env)


class CsvProviderTest(unittest.TestCase):
    def test_read_fixture(self):
        fixtures = Path(__file__).resolve().parent / "fixtures"
        # write temp csv
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "results_2026-07-19.csv"
            p.write_text(
                "race_id,race_date,venue,winner_horse_number,field_size,winner_name\n"
                "2026-07-19-04-11,2026-07-19,福島,2,4,テスト馬B\n",
                encoding="utf-8",
            )
            rows = CsvResultProvider(data_dir=Path(td)).fetch("2026-07-19")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].winner_horse_number, 2)


class ResultAutomationIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.miss_dir = Path(self.tmp.name) / "miss-evidence"
        self.imp_dir = Path(self.tmp.name) / "improvement"
        self.arch_dir = Path(self.tmp.name) / "race-archives"
        os.environ["EXPECT_AI_DB_PATH"] = str(self.db_path)
        os.environ["EXPECT_MISS_EVIDENCE_DIR"] = str(self.miss_dir)
        os.environ["EXPECT_IMPROVEMENT_EVIDENCE_DIR"] = str(self.imp_dir)
        os.environ["EXPECT_RACE_ARCHIVE_DIR"] = str(self.arch_dir)

        from app.data import db as app_db

        app_db.migrate()
        conn = app_db.connect()
        conn.execute(
            """
            INSERT INTO race_results(
              race_id, race_date, venue, winner_horse_number, field_size, finalized_at, source,
              result_json
            ) VALUES (?,?,?,?,?, datetime('now'), ?, ?)
            """,
            (
                "2026-07-19-04-11",
                "2026-07-19",
                "福島",
                2,
                4,
                "test",
                json.dumps({"winner_name": "テスト馬B"}),
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
                        "race_info": {
                            "date": "2026-07-19",
                            "venue": "福島",
                            "distance": 1200,
                            "surface": "turf",
                        },
                        "evaluation": {
                            "runners": [
                                {"horse_number": 7, "model_rank": 1},
                                {"horse_number": 2, "model_rank": 2},
                            ]
                        },
                        "ai_confidence": {"score": 0.9},
                        "explain": {
                            "narrative": "n",
                            "meta": {"track_condition": "良"},
                        },
                    }
                ),
            ),
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tmp.cleanup()
        for k in (
            "EXPECT_AI_DB_PATH",
            "EXPECT_MISS_EVIDENCE_DIR",
            "EXPECT_IMPROVEMENT_EVIDENCE_DIR",
            "EXPECT_RACE_ARCHIVE_DIR",
        ):
            os.environ.pop(k, None)
        from app.ops import result_automation as ra

        ra._service = None
        try:
            from app.stats import service as stats_service_mod

            stats_service_mod._stats_service = None
        except Exception:
            pass

    def test_post_race_pipeline(self):
        from app.ops.result_automation import ResultAutomationService

        svc = ResultAutomationService()
        result = svc.run(
            "2026-07-19",
            trigger=sm.TRIGGER_MANUAL,
            force=True,
            skip_result_sync=True,
        )
        self.assertEqual(result["run_status"], sm.COMPLETED)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["misses_recorded"], 1)
        self.assertTrue((self.miss_dir / "2026-07-19" / "manifest.json").exists())
        self.assertTrue(
            (self.imp_dir / "miss" / "2026-07-19" / "2026-07-19-04-11.json").exists()
        )
        summary = self.imp_dir / "manifest" / "2026-07-19" / "summary.json"
        self.assertTrue(summary.exists())
        doc = json.loads(summary.read_text(encoding="utf-8"))
        self.assertEqual(doc["run_id"], result["run_id"])
        self.assertEqual(doc["status"], sm.COMPLETED)
        self.assertGreaterEqual(doc["event_total"], 1)
        for name in ("run.json", "summary.json", "index.json"):
            self.assertTrue((self.imp_dir / "manifest" / "2026-07-19" / name).exists())
        self.assertIsNotNone(result.get("archive"))
        self.assertEqual(result["archive"].get("race_count"), 1)
        self.assertIn("stages", result)

        from app.data import db as app_db

        conn = app_db.connect()
        try:
            ev = conn.execute(
                "SELECT meta_json FROM race_evaluations WHERE race_id=?",
                ("2026-07-19-04-11",),
            ).fetchone()
            self.assertIsNotNone(ev)
            meta = json.loads(ev["meta_json"])
            self.assertEqual(meta.get("going"), "良")
            self.assertEqual(meta.get("distance"), 1200)
            row = conn.execute(
                "SELECT going, distance, surface FROM race_results WHERE race_id=?",
                ("2026-07-19-04-11",),
            ).fetchone()
            self.assertEqual(row["going"], "良")
            self.assertEqual(row["distance"], 1200)
            # Miss research queue = improvement_evidence_index
            idx = conn.execute(
                """
                SELECT COUNT(*) AS n FROM improvement_evidence_index
                WHERE race_date=? AND event_type='miss'
                """,
                ("2026-07-19",),
            ).fetchone()
            self.assertGreaterEqual(int(idx["n"]), 1)
            # Archive must NOT delete predictions / race_results
            pred = conn.execute(
                "SELECT COUNT(*) AS n FROM predictions WHERE race_id=?",
                ("2026-07-19-04-11",),
            ).fetchone()
            self.assertEqual(int(pred["n"]), 1)
        finally:
            conn.close()

    def test_new_run_id_each_time(self):
        from app.ops.result_automation import ResultAutomationService

        svc = ResultAutomationService()
        a = svc.run("2026-07-19", trigger=sm.TRIGGER_MANUAL, force=True, skip_result_sync=True)
        b = svc.run(
            "2026-07-19",
            trigger=sm.TRIGGER_RETRY,
            parent_run_id=a["run_id"],
            force=True,
            skip_result_sync=True,
        )
        self.assertNotEqual(a["run_id"], b["run_id"])


class ResultAutomationCanaryTest(unittest.TestCase):
    """Canary: pipeline completes without touching Prediction Core."""

    def test_canary_gates(self):
        # Gates documented in development/canary — structural checks
        from app.ops.evidence.registry import registered_types
        from app.ops.state_machine import (
            TRANSITIONS,
            COMPLETED,
            EVIDENCE_EXPORTING,
            USER_SETTLING,
            ARCHIVING,
        )

        self.assertIn("miss", registered_types())
        self.assertIn(COMPLETED, TRANSITIONS[EVIDENCE_EXPORTING])
        self.assertIn(USER_SETTLING, TRANSITIONS[EVIDENCE_EXPORTING])
        self.assertIn(COMPLETED, TRANSITIONS[ARCHIVING])


if __name__ == "__main__":
    unittest.main()
