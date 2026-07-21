# -*- coding: utf-8 -*-
"""Collector Contract 1.1 tests."""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.data.collect import (
    CollectArtifactRepository,
    CollectJobRepository,
    CollectRunRepository,
    CollectTargetRepository,
    JobIdempotencyError,
    PlannerContract,
    assert_valid_manifest,
    load_schema,
    state,
    validate_collect_target,
)
from app.data.collect.contracts.manifest import MANIFEST_SCHEMA_VERSION, schema_path
from app.data.db import connect, migrate


def _sample_manifest() -> dict:
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "week_id": "2026-07-25",
        "calendar_version": "jra-calendar-2026-w30",
        "planner_run_id": "planner-2026-07-25-test",
        "generated_at": "2026-07-21T06:00:00+09:00",
        "races": {
            "total_races_expected": 72,
            "total_races_ready": 68,
            "venue_count": 3,
            "race_count_per_venue": {
                "2026-07-25": {"函館": 12, "小倉": 12, "新潟": 12},
                "2026-07-26": {"函館": 12, "小倉": 12, "新潟": 12},
            },
            "prediction_ready_races": 65,
        },
        "collect": {"ready": 180, "partial": 12, "failed": 2, "retry": 14},
        "budget": {"daily_limit": 150, "used": 142, "remaining": 8},
        "status": {"prediction_ready": False, "complete_ready": False, "dynamic_ready": False, "dynamic_stale": False},
    }


def _sample_targets(week_id: str = "2026-07-25") -> list[dict]:
    return [
        {
            "week_id": week_id,
            "calendar_version": "jra-calendar-2026-w30",
            "race_date": "2026-07-25",
            "venue": "函館",
            "race_no": 11,
        },
        {
            "week_id": week_id,
            "calendar_version": "jra-calendar-2026-w30",
            "race_date": "2026-07-26",
            "venue": "小倉",
            "race_no": 10,
        },
    ]


class CollectStateMachineTest(unittest.TestCase):
    def test_dynamic_stale_path(self):
        path = [
            state.PENDING,
            state.RUNNING,
            state.READY,
            state.STALE_DYNAMIC,
            state.PENDING,
        ]
        kind = state.KIND_DYNAMIC
        for a, b in zip(path, path[1:]):
            self.assertTrue(state.can_transition(a, b, kind=kind), f"{a}->{b}")

    def test_static_cannot_stale(self):
        self.assertFalse(
            state.can_transition(state.READY, state.STALE_DYNAMIC, kind="STATIC_CORE")
        )
        with self.assertRaises(ValueError):
            state.assert_transition(state.READY, state.STALE_DYNAMIC, kind="STATIC_CORE")

    def test_static_ready_maintained(self):
        self.assertTrue(state.can_transition(state.RUNNING, state.READY, kind="STATIC_CORE"))

    def test_running_outcomes(self):
        for nxt in (state.READY, state.PARTIAL, state.FAILED, state.SKIPPED):
            self.assertTrue(state.can_transition(state.RUNNING, nxt, kind="STATIC_CORE"))

    def test_retry_paths(self):
        self.assertTrue(state.can_transition(state.PARTIAL, state.PENDING, kind="STATIC_CORE"))
        self.assertTrue(state.can_transition(state.FAILED, state.PENDING, kind="STATIC_CORE"))

    def test_illegal(self):
        self.assertFalse(state.can_transition(state.PENDING, state.READY, kind="STATIC_CORE"))
        with self.assertRaises(ValueError):
            state.assert_transition(state.PENDING, state.READY, kind="STATIC_CORE")


class CollectTargetContractTest(unittest.TestCase):
    def test_valid_target(self):
        t = validate_collect_target(_sample_targets()[0])
        self.assertEqual(t.venue, "函館")
        self.assertEqual(t.race_no, 11)

    def test_planner_contract_calendar_only(self):
        targets = PlannerContract.validate_targets_from_calendar(
            calendar_version="jra-calendar-2026-w30",
            week_id="2026-07-25",
            targets=_sample_targets(),
        )
        self.assertEqual(len(targets), 2)


class CollectManifestContractTest(unittest.TestCase):
    def test_schema_file_exists(self):
        self.assertTrue(schema_path().is_file())

    def test_assert_valid_manifest(self):
        assert_valid_manifest(_sample_manifest())


class CollectRepositoryTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._db = Path(self._tmpdir.name) / "collect_c1_1.db"
        os.environ["EXPECT_AI_DB_PATH"] = str(self._db)
        migrate()

    def tearDown(self):
        os.environ.pop("EXPECT_AI_DB_PATH", None)
        self._tmpdir.cleanup()

    def test_migration_008_indexes(self):
        conn = connect()
        try:
            indexes = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='collect_jobs'"
                ).fetchall()
            }
        finally:
            conn.close()
        self.assertIn("uq_collect_jobs_week_target_artifact", indexes)
        self.assertIn("idx_collect_jobs_dequeue", indexes)

    def test_job_idempotency(self):
        runs = CollectRunRepository()
        targets = CollectTargetRepository()
        jobs = CollectJobRepository()

        run = runs.create(week_id="2026-07-25", calendar_version="jra-calendar-2026-w30")
        inserted = targets.insert_many(
            planner_run_id=run["planner_run_id"],
            targets=_sample_targets(),
        )
        target_id = inserted[0]["id"]

        jobs.create(
            job_id="job-1",
            week_id="2026-07-25",
            race_date="2026-07-25",
            artifact_type="race_meta",
            kind="STATIC_CORE",
            priority="P1",
            target_id=target_id,
            planner_run_id=run["planner_run_id"],
        )
        with self.assertRaises(JobIdempotencyError):
            jobs.create(
                job_id="job-2",
                week_id="2026-07-25",
                race_date="2026-07-25",
                artifact_type="race_meta",
                kind="STATIC_CORE",
                priority="P1",
                target_id=target_id,
                planner_run_id=run["planner_run_id"],
            )

    def test_transition_metadata(self):
        runs = CollectRunRepository()
        targets = CollectTargetRepository()
        jobs = CollectJobRepository()

        run = runs.create(week_id="2026-07-25", calendar_version="jra-calendar-2026-w30")
        inserted = targets.insert_many(
            planner_run_id=run["planner_run_id"],
            targets=_sample_targets()[:1],
        )
        target_id = inserted[0]["id"]

        jobs.create(
            job_id="job-meta",
            week_id="2026-07-25",
            race_date="2026-07-25",
            artifact_type="entries_core",
            kind="STATIC_CORE",
            priority="P1",
            target_id=target_id,
            planner_run_id=run["planner_run_id"],
        )
        jobs.transition("job-meta", state.RUNNING)
        updated = jobs.transition(
            "job-meta",
            state.PARTIAL,
            attempt=2,
            retry_after="2026-07-22",
            validation_errors=[{"code": "required_null", "field": "entries[0].jockey"}],
            last_error="validator ng",
        )
        self.assertEqual(updated["status"], state.PARTIAL)
        self.assertEqual(updated["attempt"], 2)
        self.assertEqual(updated["retry_after"], "2026-07-22")
        self.assertEqual(updated["last_error"], "validator ng")
        errors = json.loads(updated["validation_errors_json"])
        self.assertEqual(errors[0]["code"], "required_null")

    def test_link_job_artifact(self):
        runs = CollectRunRepository()
        targets = CollectTargetRepository()
        jobs = CollectJobRepository()
        artifacts = CollectArtifactRepository()

        run = runs.create(week_id="2026-07-25", calendar_version="jra-calendar-2026-w30")
        inserted = targets.insert_many(
            planner_run_id=run["planner_run_id"],
            targets=_sample_targets()[:1],
        )

        jobs.create(
            job_id="job-link",
            week_id="2026-07-25",
            race_date="2026-07-25",
            artifact_type="race_meta",
            kind="STATIC_CORE",
            priority="P1",
            target_id=inserted[0]["id"],
            planner_run_id=run["planner_run_id"],
        )
        artifacts.create(
            artifact_uid="art-link",
            job_id="job-link",
            week_id="2026-07-25",
            race_date="2026-07-25",
            artifact_type="race_meta",
            kind="STATIC_CORE",
        )
        linked = jobs.link_artifact("job-link", "art-link")
        self.assertIsNotNone(linked.get("artifact_id"))
        art = artifacts.get("art-link")
        assert art is not None
        self.assertEqual(linked["artifact_id"], art["id"])

    def test_kind_aware_repository_transition(self):
        runs = CollectRunRepository()
        targets = CollectTargetRepository()
        jobs = CollectJobRepository()

        run = runs.create(week_id="2026-07-25", calendar_version="jra-calendar-2026-w30")
        inserted = targets.insert_many(
            planner_run_id=run["planner_run_id"],
            targets=_sample_targets(),
        )
        tid_dyn = inserted[0]["id"]
        tid_static = inserted[1]["id"]

        jobs.create(
            job_id="job-dyn",
            week_id="2026-07-25",
            race_date="2026-07-25",
            artifact_type="odds",
            kind="DYNAMIC",
            priority="P1",
            target_id=tid_dyn,
            planner_run_id=run["planner_run_id"],
        )
        jobs.transition("job-dyn", state.RUNNING)
        jobs.transition("job-dyn", state.READY)
        jobs.transition("job-dyn", state.STALE_DYNAMIC)

        jobs.create(
            job_id="job-static",
            week_id="2026-07-25",
            race_date="2026-07-26",
            artifact_type="race_meta",
            kind="STATIC_CORE",
            priority="P1",
            target_id=tid_static,
            planner_run_id=run["planner_run_id"],
        )
        jobs.transition("job-static", state.RUNNING)
        jobs.transition("job-static", state.READY)
        with self.assertRaises(ValueError):
            jobs.transition("job-static", state.STALE_DYNAMIC)


if __name__ == "__main__":
    unittest.main()
