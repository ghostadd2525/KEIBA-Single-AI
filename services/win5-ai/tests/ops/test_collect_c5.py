# -*- coding: utf-8 -*-
"""
C-5 E2E — Friday Gate / Prediction Ready / Complete Ready / OPS Monitor.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from app.data.collect import (
    AFTER_DRAW,
    AvailabilityContext,
    COMPLETE_READY,
    CollectBudget,
    CollectJobRepository,
    CollectPlanner,
    CollectRunRepository,
    CollectTargetRepository,
    FridayGate,
    NOT_READY,
    PREDICTION_READY,
    RaceCalendar,
    classify_ops_state,
    evaluate_collect_ops,
    read_manifest,
    state,
)
from app.data.db import migrate


def _calendar() -> RaceCalendar:
    return RaceCalendar.from_dict(
        {
            "calendar_version": "jra-calendar-2026-w29-c5",
            "week_id": "2026-07-18",
            "days": [
                {
                    "race_date": "2026-07-19",
                    "venues": {"福島": 11},
                    "venue_races": {"福島": [11]},
                }
            ],
        }
    )


class CollectC5Base(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        root = Path(self._tmpdir.name)
        os.environ["EXPECT_AI_DB_PATH"] = str(root / "c5.db")
        os.environ["EXPECT_COLLECT_MANIFEST_DIR"] = str(root / "manifests")
        os.environ["EXPECT_COLLECT_DAILY_LIMIT"] = "20"
        migrate()
        self.calendar = _calendar()
        self.week_id = self.calendar.week_id

    def tearDown(self) -> None:
        for key in (
            "EXPECT_AI_DB_PATH",
            "EXPECT_COLLECT_MANIFEST_DIR",
            "EXPECT_COLLECT_DAILY_LIMIT",
        ):
            os.environ.pop(key, None)
        self._tmpdir.cleanup()

    def _plan(self, *, draw_confirmed: bool):
        return CollectPlanner(budget=CollectBudget(daily_limit=20)).run(
            self.calendar,
            availability=AvailabilityContext(
                as_of_date="2026-07-17",
                draw_confirmed=draw_confirmed,
            ),
            scheduled_for="2026-07-17",
        )

    def _force_ready(self, artifact_type: str) -> None:
        jobs = CollectJobRepository()
        for job in jobs.list_by_week(self.week_id):
            if job["artifact_type"] != artifact_type:
                continue
            if job["status"] == state.PENDING:
                jobs.transition(job["job_id"], state.RUNNING)
                jobs.transition(job["job_id"], state.READY)


class FridayGateCaseTest(CollectC5Base):
    def test_case1_both_ready_prediction_ready(self):
        """race_meta READY + entries_core READY → Prediction Ready."""
        plan = self._plan(draw_confirmed=True)
        self.assertEqual(sorted(plan.enqueued_types), ["entries_core", "race_meta"])

        self._force_ready("race_meta")
        self._force_ready("entries_core")

        gate = FridayGate(week_id=self.week_id).run()
        self.assertTrue(gate.prediction_ready)
        self.assertFalse(gate.complete_ready)  # odds/track 未取得
        self.assertEqual(gate.prediction_ready_races, 1)
        self.assertEqual(gate.total_races_expected, 1)

        manifest = read_manifest(self.week_id)
        assert manifest is not None
        self.assertTrue(manifest["status"]["prediction_ready"])
        self.assertFalse(manifest["status"]["complete_ready"])
        self.assertEqual(manifest["races"]["prediction_ready_races"], 1)

        ops = evaluate_collect_ops(self.week_id)
        self.assertEqual(ops.state, PREDICTION_READY)

    def test_case2_entries_missing_not_ready(self):
        """entries_core 未取得 → Prediction Not Ready."""
        plan = self._plan(draw_confirmed=False)
        self.assertEqual(plan.enqueued_types, ["race_meta"])
        self.assertIn("entries_core", plan.not_generated_types)

        self._force_ready("race_meta")

        gate = FridayGate(week_id=self.week_id).run()
        self.assertFalse(gate.prediction_ready)
        self.assertFalse(gate.complete_ready)
        self.assertEqual(gate.prediction_ready_races, 0)

        race = gate.readiness.races[0]
        self.assertIn("entries_core", race.missing_prediction)

        ops = evaluate_collect_ops(self.week_id)
        self.assertEqual(ops.state, NOT_READY)

    def test_case3_odds_missing_prediction_ready_complete_false(self):
        """Prediction 必須 READY + odds 未取得 → Prediction Ready / Complete Ready=false."""
        self._plan(draw_confirmed=True)
        self._force_ready("race_meta")
        self._force_ready("entries_core")

        # odds ジョブは未生成のまま（Availability / 取得未実装）
        jobs = CollectJobRepository().list_by_week(self.week_id)
        self.assertFalse(any(j["artifact_type"] == "odds" for j in jobs))

        gate = FridayGate(week_id=self.week_id).run()
        self.assertTrue(gate.prediction_ready)
        self.assertFalse(gate.complete_ready)

        race = gate.readiness.races[0]
        self.assertEqual(race.missing_prediction, ())
        self.assertIn("odds", race.missing_complete)
        self.assertIn("track", race.missing_complete)

        ops = evaluate_collect_ops(self.week_id)
        self.assertEqual(ops.state, PREDICTION_READY)
        self.assertNotEqual(ops.state, COMPLETE_READY)


class OpsStateClassifyTest(unittest.TestCase):
    def test_three_states(self):
        self.assertEqual(
            classify_ops_state(prediction_ready=False, complete_ready=False),
            NOT_READY,
        )
        self.assertEqual(
            classify_ops_state(prediction_ready=True, complete_ready=False),
            PREDICTION_READY,
        )
        self.assertEqual(
            classify_ops_state(prediction_ready=True, complete_ready=True),
            COMPLETE_READY,
        )


class ManifestResponsibilityTest(CollectC5Base):
    def test_scheduler_does_not_set_prediction_ready(self):
        """Scheduler は status を正式確定しない（Friday Gate 正本）。"""
        from app.data.collect import CollectScheduler

        self._plan(draw_confirmed=True)
        self._force_ready("race_meta")
        self._force_ready("entries_core")

        sched = CollectScheduler(
            week_id=self.week_id,
            as_of_date="2026-07-17",
            budget=CollectBudget(daily_limit=20),
        )
        sched.finish()

        manifest = read_manifest(self.week_id)
        assert manifest is not None
        # Scheduler 後も Gate 前は false のまま
        self.assertFalse(manifest["status"]["prediction_ready"])
        self.assertFalse(manifest["status"]["complete_ready"])
        # 進捗カウントは更新される
        self.assertEqual(manifest["races"]["prediction_ready_races"], 1)

        FridayGate(week_id=self.week_id).run()
        after = read_manifest(self.week_id)
        assert after is not None
        self.assertTrue(after["status"]["prediction_ready"])


if __name__ == "__main__":
    unittest.main()
