# -*- coding: utf-8 -*-
"""Local prediction-run persist contract tests. Production DB は触らない。"""
from __future__ import annotations

import inspect
import json
import math
import os
import socket
import sqlite3
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from tests.ops.helpers import enable_prediction_runs, http_json, isolated_env, running_server


def _count_predictions() -> int:
    from app.data.db import connect

    conn = connect()
    try:
        return int(conn.execute("SELECT count(*) FROM predictions").fetchone()[0])
    finally:
        conn.close()


def _columns(conn: sqlite3.Connection) -> set[str]:
    return {str(r[1]) for r in conn.execute("PRAGMA table_info(predictions)").fetchall()}


class LocalMigrationTest(unittest.TestCase):
    def test_local_migration_adds_partial_unique(self):
        with isolated_env():
            from app.data.db import connect, migrate

            applied = migrate()
            self.assertIn("022_prediction_run_idempotency", applied)
            conn = connect()
            try:
                cols = _columns(conn)
                for name in (
                    "idempotency_key",
                    "persist_source",
                    "input_snapshot_hash",
                    "prediction_semantic_hash",
                ):
                    self.assertIn(name, cols)
                versions = {
                    r[0]
                    for r in conn.execute("SELECT version FROM schema_migrations").fetchall()
                }
                self.assertIn("022_prediction_run_idempotency", versions)
                idx = conn.execute(
                    "SELECT sql FROM sqlite_master WHERE name='uq_predictions_idempotency_key_not_null'"
                ).fetchone()
                self.assertIsNotNone(idx)
                self.assertIn("idempotency_key IS NOT NULL", idx[0])
            finally:
                conn.close()


class PartialUniqueUpsertTest(unittest.TestCase):
    def test_predicate_required_and_nulls_allowed(self):
        with isolated_env():
            from app.data.db import connect, migrate

            migrate()
            conn = connect()
            try:
                conn.execute(
                    "INSERT INTO predictions(race_id, engine_source, bundle_json, created_at, idempotency_key) "
                    "VALUES ('R','real_ai','{}','t','k1')"
                )
                with self.assertRaises(sqlite3.OperationalError) as ctx:
                    conn.execute(
                        "INSERT INTO predictions(race_id, engine_source, bundle_json, created_at, idempotency_key) "
                        "VALUES ('R','real_ai','{}','t','k1') ON CONFLICT(idempotency_key) DO NOTHING"
                    )
                self.assertIn("ON CONFLICT clause does not match", str(ctx.exception))
                conn.execute(
                    "INSERT INTO predictions(race_id, engine_source, bundle_json, created_at, idempotency_key) "
                    "VALUES ('R','real_ai','{}','t','k1') "
                    "ON CONFLICT(idempotency_key) WHERE idempotency_key IS NOT NULL DO NOTHING"
                )
                self.assertEqual(
                    conn.execute("SELECT count(*) FROM predictions WHERE idempotency_key='k1'").fetchone()[0],
                    1,
                )
                conn.execute(
                    "INSERT INTO predictions(race_id, engine_source, bundle_json, created_at) "
                    "VALUES ('R2','real_ai','{}','t')"
                )
                conn.execute(
                    "INSERT INTO predictions(race_id, engine_source, bundle_json, created_at) "
                    "VALUES ('R3','real_ai','{}','t')"
                )
                self.assertEqual(
                    conn.execute(
                        "SELECT count(*) FROM predictions WHERE idempotency_key IS NULL"
                    ).fetchone()[0],
                    2,
                )
                conn.commit()
            finally:
                conn.close()


def _complete_obs(created: str) -> tuple[dict, dict]:
    from app.predictions.snapshot import RACE_SNAPSHOT_KEYS, RUNNER_SNAPSHOT_KEYS

    race = {"observed_at": created}
    for key in RACE_SNAPSHOT_KEYS:
        race[key] = {"distance": 1600, "surface": "turf", "field_size": 2, "class_label": "1勝", "track_condition": "good", "weather": "fine"}[key]
    runner = {
        "horse_number": 1,
        "observed_at": created,
        "history_status": "CONFIRMED_HISTORY",
        "history_count_before_race": 3,
    }
    for key in RUNNER_SNAPSHOT_KEYS:
        if key in ("history_status", "history_count_before_race"):
            continue
        runner[key] = 1 if key in ("frame_number", "popularity") else "x"
    return race, {"1": runner}


def _bundle(win1: float = 0.4, race_id: str = "2026-08-01-01-01") -> dict:
    return {
        "schema_version": "single-prediction-bundle/2.0",
        "race_id": race_id,
        "generated_at": "2026-08-01T03:00:00+00:00",
        "evaluation": {
            "runners": [
                {"horse_number": 1, "win_prob": win1, "model_rank": 1, "mark": "honmei"},
                {"horse_number": 2, "win_prob": 0.3, "model_rank": 2, "mark": "taikou"},
            ]
        },
        "warnings": [],
    }


class SequentialReplayTest(unittest.TestCase):
    def test_second_save_replays_same_id(self):
        with isolated_env():
            from app.data.db import migrate
            from app.data.repository import PredictionRepository
            from app.predictions.snapshot import compute_prediction_semantic_hash

            migrate()
            repo = PredictionRepository()
            bundle = _bundle()
            sem = compute_prediction_semantic_hash(bundle)
            first = repo.save_idempotent(
                race_id="R",
                bundle=bundle,
                engine_source="real_ai",
                idempotency_key="same-key",
                persist_source="site_prediction_run",
                input_snapshot_hash="a" * 64,
                prediction_semantic_hash=sem,
                model_version="core-delegated",
            )
            second = repo.save_idempotent(
                race_id="R",
                bundle=bundle,
                engine_source="real_ai",
                idempotency_key="same-key",
                persist_source="site_prediction_run",
                input_snapshot_hash="a" * 64,
                prediction_semantic_hash=sem,
                model_version="core-delegated",
            )
            self.assertFalse(first.replayed)
            self.assertTrue(second.replayed)
            self.assertEqual(first.prediction_id, second.prediction_id)
            self.assertEqual(_count_predictions(), 1)


class ConcurrentReplayTest(unittest.TestCase):
    def test_threaded_upsert_single_row(self):
        with isolated_env():
            from app.data.db import migrate
            from app.data.repository import PredictionRepository
            from app.predictions.snapshot import compute_prediction_semantic_hash

            migrate()
            repo = PredictionRepository()
            bundle = _bundle()
            sem = compute_prediction_semantic_hash(bundle)
            results = []
            errors = []

            def worker() -> None:
                try:
                    results.append(
                        repo.save_idempotent(
                            race_id="R",
                            bundle=bundle,
                            engine_source="real_ai",
                            idempotency_key="concurrent-key",
                            persist_source="site_prediction_run",
                            input_snapshot_hash="b" * 64,
                            prediction_semantic_hash=sem,
                            model_version="core-delegated",
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)

            threads = [threading.Thread(target=worker) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(errors, [])
            self.assertEqual(len(results), 8)
            ids = {r.prediction_id for r in results}
            self.assertEqual(len(ids), 1)
            self.assertEqual(sum(1 for r in results if not r.replayed), 1)
            self.assertEqual(_count_predictions(), 1)


class SemanticConflictTest(unittest.TestCase):
    def test_same_key_different_semantic_raises_409(self):
        with isolated_env():
            from app.data.db import migrate
            from app.data.repository import PredictionRepository
            from app.predictions.provenance import IdempotencyConflictError
            from app.predictions.snapshot import compute_prediction_semantic_hash

            migrate()
            repo = PredictionRepository()
            a = _bundle(0.4)
            b = _bundle(0.55)
            repo.save_idempotent(
                race_id="R",
                bundle=a,
                engine_source="real_ai",
                idempotency_key="conflict-key",
                persist_source="site_prediction_run",
                input_snapshot_hash="c" * 64,
                prediction_semantic_hash=compute_prediction_semantic_hash(a),
            )
            with self.assertRaises(IdempotencyConflictError):
                repo.save_idempotent(
                    race_id="R",
                    bundle=b,
                    engine_source="real_ai",
                    idempotency_key="conflict-key",
                    persist_source="site_prediction_run",
                    input_snapshot_hash="c" * 64,
                    prediction_semantic_hash=compute_prediction_semantic_hash(b),
                )
            self.assertEqual(_count_predictions(), 1)

    def test_hash_order_independent_and_rejects_nan(self):
        from app.predictions.snapshot import (
            canonical_json,
            compute_prediction_semantic_hash,
            prediction_semantic_payload,
        )

        left = {
            "race_id": "R",
            "evaluation": {
                "runners": [
                    {"horse_number": 2, "win_prob": 0.3, "model_rank": 2, "mark": "taikou"},
                    {"horse_number": 1, "win_prob": 0.4, "model_rank": 1, "mark": "honmei"},
                ]
            },
        }
        right = {
            "race_id": "R",
            "evaluation": {
                "runners": [
                    {"horse_number": 1, "win_prob": 0.4, "model_rank": 1, "mark": "honmei"},
                    {"horse_number": 2, "win_prob": 0.3, "model_rank": 2, "mark": "taikou"},
                ]
            },
        }
        self.assertEqual(compute_prediction_semantic_hash(left), compute_prediction_semantic_hash(right))
        payload = prediction_semantic_payload(left)
        self.assertEqual(set(payload), {"race_id", "runners"})
        self.assertEqual(set(payload["runners"]["1"]), {"win_prob", "model_rank", "mark"})
        dumped = json.dumps(payload)
        self.assertNotIn("generated_at", dumped)
        self.assertNotIn("captured_at", dumped)
        self.assertNotIn("observed_at", dumped)
        with_ts = {
            "race_id": "R",
            "generated_at": "2099-01-01T00:00:00+00:00",
            "evaluation": {
                "runners": [
                    {
                        "horse_number": 1,
                        "win_prob": 0.4,
                        "model_rank": 1,
                        "mark": "honmei",
                        "observed_at": "2099-01-01T00:00:00+00:00",
                    }
                ]
            },
        }
        self.assertEqual(
            compute_prediction_semantic_hash(left),
            compute_prediction_semantic_hash({**right, "generated_at": "other"}),
        )
        self.assertEqual(
            compute_prediction_semantic_hash(with_ts),
            compute_prediction_semantic_hash(
                {"race_id": "R", "evaluation": {"runners": [{"horse_number": 1, "win_prob": 0.4, "model_rank": 1, "mark": "honmei"}]}}
            ),
        )
        with_heads = {
            "race_id": "R",
            "evaluation": {
                "runners": [
                    {"horse_number": 1, "win_prob": 0.4, "model_rank": 1, "mark": "honmei", "top2_prob": 0.6, "top3_prob": 0.7}
                ]
            },
        }
        self.assertIn("top2_prob", prediction_semantic_payload(with_heads)["runners"]["1"])
        self.assertNotEqual(compute_prediction_semantic_hash(with_ts), compute_prediction_semantic_hash(with_heads))
        dup = {
            "race_id": "R",
            "evaluation": {
                "runners": [
                    {"horse_number": 1, "win_prob": 0.4, "model_rank": 1, "mark": "honmei"},
                    {"horse_number": 1, "win_prob": 0.2, "model_rank": 2, "mark": "taikou"},
                ]
            },
        }
        with self.assertRaises(ValueError):
            compute_prediction_semantic_hash(dup)
        with self.assertRaises(ValueError):
            canonical_json({"x": math.nan})
        with self.assertRaises(ValueError):
            canonical_json({"x": math.inf})


class FeatureAsofTest(unittest.TestCase):
    def test_future_observed_at_dropped_no_clamp(self):
        from app.predictions.snapshot import collect_prediction_time_features

        captured = "2026-08-01T03:00:00+00:00"
        future = "2026-08-01T04:00:00+00:00"
        snap = collect_prediction_time_features(
            captured_at=captured,
            race_obs={"distance": 1600, "observed_at": future},
            runner_obs=[
                {
                    "horse_number": 1,
                    "popularity": 2,
                    "observed_at": future,
                    "history_status": "UNKNOWN",
                }
            ],
        )
        self.assertEqual(snap["race"]["distance"]["missing_reason"], "anti_leak_rejected")
        self.assertIsNone(snap["race"]["distance"]["value"])
        self.assertEqual(snap["runners"]["1"]["popularity"]["missing_reason"], "anti_leak_rejected")
        self.assertFalse(snap["asof_clamped"])
        self.assertGreaterEqual(snap["anti_leak_violations"], 1)

    def test_same_time_kept(self):
        from app.predictions.snapshot import collect_prediction_time_features

        captured = "2026-08-01T03:00:00+00:00"
        snap = collect_prediction_time_features(
            captured_at=captured,
            race_obs={"distance": 1600, "observed_at": captured},
            runner_obs=[{"horse_number": 1, "popularity": 2, "observed_at": captured}],
        )
        self.assertEqual(snap["race"]["distance"]["value"], 1600)
        self.assertIsNone(snap["race"]["distance"]["missing_reason"])


class CorpusTests(unittest.TestCase):
    def test_source_exclusion_and_race_level_split(self):
        with isolated_env():
            from app.data.db import connect, migrate
            from app.predictions.corpus import (
                assign_race_level_split,
                iter_eligible_joined,
                predictions_share_race_split,
                training_rows,
            )
            from app.predictions.provenance import stamp_persist_provenance
            from app.predictions.snapshot import attach_prediction_time_features_fail_open

            migrate()
            created = "2026-08-01T02:00:00+00:00"
            finalized = "2026-08-01T04:00:00+00:00"
            race_obs, runner_obs = _complete_obs(created)
            eligible_bundle = attach_prediction_time_features_fail_open(
                _bundle(),
                prediction_created_at=created,
                race_obs=race_obs,
                runner_obs=runner_obs,
            )
            self.assertEqual(eligible_bundle["prediction_time_features"]["capture_status"], "complete")
            eligible_bundle = stamp_persist_provenance(
                eligible_bundle,
                persist_source="site_prediction_run",
                engine_source="real_ai",
                fallback_reason=None,
                engine_build_fingerprint="f" * 64,
                fingerprint_status="determined",
            )
            self.assertTrue(eligible_bundle["persist_provenance"]["training_eligible"])
            partial_bundle = attach_prediction_time_features_fail_open(
                _bundle(),
                prediction_created_at=created,
                race_obs={"distance": 1600, "observed_at": created},
                runner_obs=[{"horse_number": 1, "popularity": 1, "observed_at": created}],
            )
            partial_bundle = stamp_persist_provenance(
                partial_bundle,
                persist_source="site_prediction_run",
                engine_source="real_ai",
                fallback_reason=None,
                engine_build_fingerprint="f" * 64,
                fingerprint_status="determined",
            )
            self.assertFalse(partial_bundle["persist_provenance"]["training_eligible"])
            undetermined_bundle = stamp_persist_provenance(
                attach_prediction_time_features_fail_open(
                    _bundle(),
                    prediction_created_at=created,
                    race_obs=race_obs,
                    runner_obs=runner_obs,
                ),
                persist_source="site_prediction_run",
                engine_source="real_ai",
                fallback_reason=None,
                engine_build_fingerprint="f" * 64,
                fingerprint_status="undetermined",
            )
            self.assertFalse(undetermined_bundle["persist_provenance"]["training_eligible"])
            conn = connect()
            try:
                def insert(race_id, persist_source, engine_source, bundle, fallback=None):
                    conn.execute(
                        """
                        INSERT INTO predictions(
                          race_id, engine_source, fallback_reason, model_version,
                          bundle_json, created_at, persist_source
                        ) VALUES (?,?,?,?,?,?,?)
                        """,
                        (
                            race_id,
                            engine_source,
                            fallback,
                            "core-delegated",
                            json.dumps(bundle, ensure_ascii=False),
                            created,
                            persist_source,
                        ),
                    )

                insert("R1", "site_prediction_run", "real_ai", eligible_bundle)
                insert("R1", "site_prediction_run", "real_ai", eligible_bundle)
                insert("R2", "conversation_chat", "real_ai", eligible_bundle)
                insert("R3", "challenge_cache", "real_ai", eligible_bundle)
                insert("R4", "ra_cache", "real_ai", eligible_bundle)
                insert("R5", "site_prediction_run", "mock_fallback", eligible_bundle, "market_feature_missing")
                insert("R7", None, "real_ai", eligible_bundle)
                insert("R8", "site_prediction_run", "real_ai", partial_bundle)
                insert("R9", "site_prediction_run", "real_ai", undetermined_bundle)
                conn.execute(
                    """
                    INSERT INTO race_results(
                      race_id, race_date, field_size, winner_horse_number,
                      result_json, source, finalized_at
                    ) VALUES
                      ('R1','2026-08-01',2,1,'{"finish_order":[1,2]}','official',?),
                      ('R2','2026-08-01',2,1,'{"finish_order":[1,2]}','official',?),
                      ('R3','2026-08-01',2,1,'{"finish_order":[1,2]}','official',?),
                      ('R4','2026-08-01',2,1,'{"finish_order":[1,2]}','official',?),
                      ('R5','2026-08-01',2,1,'{"finish_order":[1,2]}','official',?),
                      ('R6','2026-08-02',2,1,'{"finish_order":[1]}','official',?),
                      ('R7','2026-08-01',2,1,'{"finish_order":[1,2]}','official',?),
                      ('R8','2026-08-01',2,1,'{"finish_order":[1,2]}','official',?),
                      ('R9','2026-08-01',2,1,'{"finish_order":[1,2]}','official',?)
                    """,
                    (finalized, finalized, finalized, finalized, finalized, finalized, finalized, finalized, finalized),
                )
                conn.execute(
                    """
                    INSERT INTO predictions(
                      race_id, engine_source, bundle_json, created_at, persist_source
                    ) VALUES ('R6','real_ai',?,?, 'site_prediction_run')
                    """,
                    (json.dumps(eligible_bundle, ensure_ascii=False), created),
                )
                conn.commit()
            finally:
                conn.close()

            from app.predictions import corpus as corpus_mod

            self.assertNotIn("latest_prediction_for_race", corpus_mod.JOIN_SQL)
            eligible = iter_eligible_joined()
            race_ids = {row["race_id"] for row in eligible}
            self.assertEqual(race_ids, {"R1", "R6"})
            self.assertNotIn("R7", race_ids)
            self.assertNotIn("R8", race_ids)
            self.assertNotIn("R9", race_ids)
            self.assertEqual(sum(1 for row in eligible if row["race_id"] == "R1"), 2)
            excluded_sources = {row["persist_source"] for row in eligible}
            self.assertNotIn("conversation_chat", excluded_sources)
            self.assertNotIn("challenge_cache", excluded_sources)
            self.assertNotIn("ra_cache", excluded_sources)
            train = training_rows(eligible)
            self.assertTrue(all(r["race_id"] == "R1" for r in train))
            self.assertTrue(all(r["finish_scope"] == "FULL_FIELD" for r in train))
            split = assign_race_level_split(
                [(r["race_id"], r["race_date"]) for r in eligible],
                train_until="2026-08-01",
                val_until="2026-08-01",
            )
            self.assertEqual(split["R1"], "train")
            self.assertEqual(split["R6"], "test")
            self.assertTrue(predictions_share_race_split(eligible, split))


class RegressionTests(unittest.TestCase):
    def test_existing_save_source_unchanged(self):
        from app.data.repository import PredictionRepository

        src = inspect.getsource(PredictionRepository.save)
        self.assertNotIn("idempotency_key", src)
        self.assertNotIn("ON CONFLICT", src)
        self.assertIn("INSERT INTO predictions(", src)

    def test_get_zero_write_and_response_shape(self):
        with running_server() as base:
            before = _count_predictions()
            status, body = http_json(f"{base}/v1/predictions/20260719_hanshin_11")
            self.assertEqual(status, 200)
            self.assertTrue(body.get("ok"))
            self.assertEqual(body["data"].get("race_id"), "20260719_hanshin_11")
            self.assertNotIn("prediction_id", body["data"])
            self.assertNotIn("replayed", body)
            self.assertNotIn("prediction_time_features", body["data"])
            after = _count_predictions()
            self.assertEqual(before, after)
            status2, body2 = http_json(f"{base}/v1/predictions")
            self.assertEqual(status2, 200)
            self.assertTrue(body2.get("ok"))
            self.assertEqual(_count_predictions(), after)

    def test_conversation_still_always_inserts(self):
        with isolated_env():
            from app.conversation.service import ConversationService
            from app.data.db import connect, migrate

            migrate()
            svc = ConversationService()
            r1 = svc.chat({"message": "20260719_hanshin_11を予想して", "session_id": "s-reg-1"})
            r2 = svc.chat({"message": "20260719_hanshin_11を予想して", "session_id": "s-reg-1"})
            self.assertIn("reply", r1)
            self.assertIn("reply", r2)
            conn = connect()
            try:
                rows = conn.execute(
                    "SELECT persist_source, idempotency_key FROM predictions ORDER BY id"
                ).fetchall()
                self.assertGreaterEqual(len(rows), 2)
                self.assertTrue(all(r["persist_source"] is None for r in rows))
                self.assertTrue(all(r["idempotency_key"] is None for r in rows))
            finally:
                conn.close()


_RUN_HDR = {"X-Prediction-Run-Key": "test-run-key"}


class PostPredictionRunsTest(unittest.TestCase):
    def test_sequential_and_concurrent_http_replay(self):
        from tests.ops.helpers import import_sample_data
        from tests.predictions.fake_platform import ensure_fake_ai_platform

        with running_server(engine="real", prediction_runs=True) as base:
            ensure_fake_ai_platform()
            import_sample_data()
            body = {"race_id": "2026-07-19-04-11"}
            s1, p1 = http_json(f"{base}/v1/prediction-runs", method="POST", body=body, headers=_RUN_HDR)
            self.assertEqual(s1, 200, p1)
            self.assertTrue(p1.get("ok"))
            data1 = p1["data"]
            self.assertFalse(data1["replayed"])
            self.assertEqual(data1["persist_source"], "site_prediction_run")
            self.assertIn("prediction_id", data1)
            self.assertIn("idempotency_key", data1)
            self.assertNotIn("prediction_id", data1["bundle"])
            s2, p2 = http_json(f"{base}/v1/prediction-runs", method="POST", body=body, headers=_RUN_HDR)
            self.assertEqual(s2, 200, p2)
            self.assertTrue(p2["data"]["replayed"])
            self.assertEqual(p2["data"]["prediction_id"], data1["prediction_id"])
            after_seq = _count_predictions()

            def post_once() -> tuple[int, dict]:
                return http_json(f"{base}/v1/prediction-runs", method="POST", body=body, headers=_RUN_HDR)

            with ThreadPoolExecutor(max_workers=6) as pool:
                posted = list(pool.map(lambda _: post_once(), range(6)))
            self.assertTrue(all(status == 200 for status, _ in posted))
            self.assertTrue(all(payload["data"]["replayed"] for _, payload in posted))
            self.assertEqual(_count_predictions(), after_seq)
            bad_s, bad = http_json(
                f"{base}/v1/prediction-runs",
                method="POST",
                body={"race_id": "2026-07-19-04-11", "bundle": {"x": 1}},
                headers=_RUN_HDR,
            )
            self.assertEqual(bad_s, 400)
            self.assertEqual(bad.get("error", {}).get("code"), "CLIENT_BUNDLE_REJECTED")


def _mp_save(payload: tuple[str, str, str]) -> tuple[int, bool]:
    db_path, key, sem = payload
    os.environ["EXPECT_AI_DB_PATH"] = db_path
    os.environ["EXPECT_AI_ALLOW_MIGRATION_022"] = "1"
    from app.data.db import migrate
    from app.data.repository import PredictionRepository

    migrate()
    repo = PredictionRepository()
    bundle = {
        "schema_version": "single-prediction-bundle/2.0",
        "race_id": "2026-08-01-01-01",
        "evaluation": {
            "runners": [
                {"horse_number": 1, "win_prob": 0.4, "model_rank": 1, "mark": "honmei"},
                {"horse_number": 2, "win_prob": 0.3, "model_rank": 2, "mark": "taikou"},
            ]
        },
    }
    result = repo.save_idempotent(
        race_id="R",
        bundle=bundle,
        engine_source="real_ai",
        idempotency_key=key,
        persist_source="site_prediction_run",
        input_snapshot_hash="d" * 64,
        prediction_semantic_hash=sem,
        model_version="core-delegated",
    )
    return result.prediction_id, result.replayed


class ReviewContractTests(unittest.TestCase):
    def test_schema_not_ready_fail_closed(self):
        with running_server(allow_migration_019=False, prediction_runs=True) as base:
            from app.data.db import prediction_run_schema_ready

            self.assertFalse(prediction_run_schema_ready())
            before = _count_predictions()
            status, body = http_json(
                f"{base}/v1/prediction-runs",
                method="POST",
                body={"race_id": "20260719_hanshin_11"},
                headers=_RUN_HDR,
            )
            self.assertEqual(status, 503, body)
            self.assertEqual(body.get("error", {}).get("code"), "PREDICTION_RUN_SCHEMA_NOT_READY")
            self.assertEqual(_count_predictions(), before)
            g_status, g_body = http_json(f"{base}/v1/predictions/20260719_hanshin_11")
            self.assertEqual(g_status, 200, g_body)
            c_status, c_body = http_json(
                f"{base}/v1/conversation/chat",
                method="POST",
                body={"message": "20260719_hanshin_11を予想して"},
            )
            self.assertEqual(c_status, 200, c_body)
            self.assertGreater(_count_predictions(), before)

    def test_public_post_guards(self):
        from app.predictions.guards import public_post_exposure, reset_prediction_run_rate_limit

        reset_prediction_run_rate_limit()
        os.environ.pop("PREDICTION_RUNS_ENABLED", None)
        exposure = public_post_exposure()
        self.assertFalse(exposure["PRODUCTION_EXPOSURE_READY"])
        self.assertFalse(exposure["PREDICTION_RUNS_ENABLED"])
        self.assertTrue(exposure["allowlist_required"])
        self.assertTrue(exposure["auth_required"])
        self.assertTrue(exposure["rate_limit"])
        self.assertEqual(exposure["body_limit_bytes"], 4096)
        self.assertFalse(exposure["SITE_CORPUS_ACCUMULATION_ACTIVE"])
        with running_server() as base:
            off_s, off = http_json(
                f"{base}/v1/prediction-runs",
                method="POST",
                body={"race_id": "20260719_hanshin_11"},
            )
            self.assertEqual(off_s, 503)
            self.assertEqual(off.get("error", {}).get("code"), "PREDICTION_RUNS_DISABLED")
        with running_server(prediction_runs=True) as base:
            extra_s, extra = http_json(
                f"{base}/v1/prediction-runs",
                method="POST",
                body={"race_id": "20260719_hanshin_11", "note": "x"},
                headers=_RUN_HDR,
            )
            self.assertEqual(extra_s, 400)
            self.assertEqual(extra.get("error", {}).get("code"), "UNEXPECTED_BODY_KEYS")
            fmt_s, fmt = http_json(
                f"{base}/v1/prediction-runs",
                method="POST",
                body={"race_id": "not-a-race"},
                headers=_RUN_HDR,
            )
            self.assertEqual(fmt_s, 400)
            self.assertEqual(fmt.get("error", {}).get("code"), "INVALID_RACE_ID_FORMAT")
            miss_s, miss = http_json(
                f"{base}/v1/prediction-runs",
                method="POST",
                body={"race_id": "20991231_zzzz_1"},
                headers=_RUN_HDR,
            )
            self.assertEqual(miss_s, 404)
            self.assertEqual(miss.get("error", {}).get("code"), "RACE_NOT_FOUND")
            os.environ["PREDICTION_RUN_ALLOWED_DATES"] = "2099-01-01"
            try:
                date_s, date_body = http_json(
                    f"{base}/v1/prediction-runs",
                    method="POST",
                    body={"race_id": "20260719_hanshin_11"},
                    headers=_RUN_HDR,
                )
            finally:
                os.environ["PREDICTION_RUN_ALLOWED_DATES"] = "2026-07-19"
            self.assertEqual(date_s, 400)
            self.assertEqual(date_body.get("error", {}).get("code"), "RACE_DATE_NOT_ALLOWED")
            os.environ["PREDICTION_RUN_ALLOWED_DATES"] = ""
            try:
                al_s, al_body = http_json(
                    f"{base}/v1/prediction-runs",
                    method="POST",
                    body={"race_id": "20260719_hanshin_11"},
                    headers=_RUN_HDR,
                )
            finally:
                os.environ["PREDICTION_RUN_ALLOWED_DATES"] = "2026-07-19"
            self.assertEqual(al_s, 400)
            self.assertEqual(al_body.get("error", {}).get("code"), "PREDICTION_RUN_ALLOWLIST_REQUIRED")
            noauth_s, noauth = http_json(
                f"{base}/v1/prediction-runs",
                method="POST",
                body={"race_id": "20260719_hanshin_11"},
            )
            self.assertEqual(noauth_s, 401)
            self.assertEqual(noauth.get("error", {}).get("code"), "PREDICTION_RUN_AUTH_REQUIRED")
            huge = "x" * 5000
            big_s, big = http_json(
                f"{base}/v1/prediction-runs",
                method="POST",
                body={"race_id": huge},
                headers=_RUN_HDR,
            )
            self.assertEqual(big_s, 413)
            self.assertEqual(big.get("error", {}).get("code"), "PREDICTION_RUN_BODY_TOO_LARGE")
        with running_server(prediction_runs=True) as base:
            os.environ["PREDICTION_RUN_RATE_LIMIT"] = "1"
            from app.predictions.guards import reset_prediction_run_rate_limit

            reset_prediction_run_rate_limit()
            first_s, _ = http_json(
                f"{base}/v1/prediction-runs",
                method="POST",
                body={"race_id": "20260719_hanshin_11", "note": "x"},
                headers=_RUN_HDR,
            )
            self.assertEqual(first_s, 400)
            rate_s, rate = http_json(
                f"{base}/v1/prediction-runs",
                method="POST",
                body={"race_id": "20260719_hanshin_11", "note": "x"},
                headers=_RUN_HDR,
            )
            self.assertEqual(rate_s, 429)
            self.assertEqual(rate.get("error", {}).get("code"), "PREDICTION_RUN_RATE_LIMITED")

    def test_separate_process_concurrency(self):
        import multiprocessing

        with isolated_env():
            from app.data.db import db_path, migrate
            from app.predictions.snapshot import compute_prediction_semantic_hash

            migrate()
            win5 = str(Path(__file__).resolve().parents[2])
            os.environ["PYTHONPATH"] = win5 + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else "")
            sem = compute_prediction_semantic_hash(_bundle())
            ctx = multiprocessing.get_context("spawn")
            args = [(str(db_path()), "proc-key", sem)] * 4
            with ctx.Pool(4) as pool:
                results = pool.map(_mp_save, args)
            ids = {pid for pid, _ in results}
            self.assertEqual(len(ids), 1)
            self.assertEqual(sum(1 for _, replayed in results if not replayed), 1)
            self.assertEqual(_count_predictions(), 1)

    def test_fingerprint_has_code_and_contract_no_abspath(self):
        from tests.predictions.fake_platform import ensure_fake_ai_platform

        with isolated_env():
            ensure_fake_ai_platform()
            from app.predictions.provenance import resolve_engine_build_fingerprint, training_auto_adopt

            fp = resolve_engine_build_fingerprint()
            material = json.dumps(fp["material"], ensure_ascii=False)
            self.assertIn("prediction_contract_version", material)
            self.assertIn("feature_snapshot_schema_version", material)
            self.assertIn("core_facade_version", material)
            self.assertNotIn("/workspace", material)
            self.assertNotIn("/home/", material)
            self.assertNotIn("AI_API_KEY", material)
            if fp["fingerprint_status"] == "undetermined":
                self.assertFalse(
                    training_auto_adopt(
                        persist_source="site_prediction_run",
                        engine_source="real_ai",
                        fallback_reason=None,
                        snapshot={"capture_status": "complete", "training_coverage": "complete"},
                        fingerprint_status=fp["fingerprint_status"],
                    )
                )

    def test_feature_pin_same_object_no_reload(self):
        from tests.ops.helpers import import_sample_data
        from tests.predictions.fake_platform import ensure_fake_ai_platform

        with isolated_env(engine="real"):
            ensure_fake_ai_platform()
            from app.core.feature_loader_bridge import reset_unpinned_load_calls, unpinned_load_calls
            from app.data.db import migrate
            from app.predictions.feature_pin import pin_feature_load
            from app.predictions.runs import confirm_prediction_inputs
            from ai_platform.core.features import FeatureLoader

            migrate()
            import_sample_data()
            reset_unpinned_load_calls()
            confirmed = confirm_prediction_inputs("2026-07-19-04-11")
            self.assertIsNotNone(confirmed.feature_result)
            after_hash = unpinned_load_calls()
            self.assertEqual(after_hash, ["2026-07-19-04-11"])
            with pin_feature_load(confirmed.feature_result, core_race_id="2026-07-19-04-11"):
                again = FeatureLoader().load("2026-07-19-04-11")
                self.assertIs(again, confirmed.feature_result)
                FeatureLoader().classify_unavailable("2026-07-19-04-11")
            self.assertEqual(unpinned_load_calls(), after_hash)


class ReviewCounterexampleTests(unittest.TestCase):
    def test_input_hash_covers_full_feature_frame(self):
        import pandas as pd

        from app.predictions.snapshot import canonical_feature_load_object, compute_input_snapshot_hash

        class _Res:
            def __init__(self, frame, extra=None):
                self.frame = frame
                self.feature_source = "db"
                self.metadata = extra or {}

        a = _Res(pd.DataFrame([{"horse_number": 1, "popularity": 2, "secret_col": 9}]))
        b = _Res(pd.DataFrame([{"horse_number": 1, "popularity": 2, "secret_col": 8}]))
        ha = compute_input_snapshot_hash(
            canonical_feature_load_object(a, race_id="R", core_race_id="C")
        )
        hb = compute_input_snapshot_hash(
            canonical_feature_load_object(b, race_id="R", core_race_id="C")
        )
        self.assertNotEqual(ha, hb)
        hc = compute_input_snapshot_hash(
            canonical_feature_load_object(
                _Res(pd.DataFrame([{"horse_number": 1, "popularity": 2, "secret_col": 9}]), extra={"k": 1}),
                race_id="R",
                core_race_id="C",
            )
        )
        self.assertNotEqual(ha, hc)

    def test_feature_load_failure_503_no_reload(self):
        from tests.predictions.fake_platform import ensure_fake_ai_platform

        with running_server(engine="real", prediction_runs=True) as base:
            ensure_fake_ai_platform()
            from app.core.feature_loader_bridge import reset_unpinned_load_calls, unpinned_load_calls

            reset_unpinned_load_calls()
            before = _count_predictions()
            status, body = http_json(
                f"{base}/v1/prediction-runs",
                method="POST",
                body={"race_id": "20260719_hanshin_11"},
                headers=_RUN_HDR,
            )
            self.assertEqual(status, 503, body)
            self.assertEqual(body.get("error", {}).get("code"), "FEATURE_LOAD_FAILED")
            self.assertEqual(_count_predictions(), before)
            self.assertLessEqual(len(unpinned_load_calls()), 1)

    def test_captured_at_not_used_as_observed_at(self):
        from app.predictions.snapshot import observations_from_feature_frame
        from app.predictions.provenance import training_auto_adopt

        class _Res:
            def __init__(self):
                import pandas as pd

                self.frame = pd.DataFrame([{"horse_number": 1, "popularity": 2, "history_count_before_race": 0}])
                self.feature_source = "db"
                self.metadata = {}

        captured = "2026-08-01T03:00:00+00:00"
        race_obs, runners = observations_from_feature_frame(_Res(), {}, captured)
        self.assertNotEqual(race_obs.get("observed_at"), captured)
        self.assertIsNone(race_obs.get("observed_at"))
        self.assertNotEqual((runners.get("1") or {}).get("observed_at"), captured)
        from app.predictions.snapshot import collect_prediction_time_features

        snap = collect_prediction_time_features(
            captured_at=captured,
            race_obs=race_obs,
            runner_obs=runners,
        )
        self.assertEqual(snap["runners"]["1"]["popularity"]["missing_reason"], "observed_at_unknown")
        self.assertFalse(
            training_auto_adopt(
                persist_source="site_prediction_run",
                engine_source="real_ai",
                fallback_reason=None,
                snapshot=snap,
                fingerprint_status="determined",
            )
        )

    def test_history_count_zero_is_not_confirmed_zero(self):
        from app.predictions.snapshot import resolve_history_status, observations_from_feature_frame
        import pandas as pd

        self.assertEqual(resolve_history_status({"history_count_before_race": 0}), "UNKNOWN")
        self.assertEqual(
            resolve_history_status({"history_status": "CONFIRMED_ZERO", "history_count_before_race": 0}),
            "CONFIRMED_ZERO",
        )

        class _Res:
            frame = pd.DataFrame([{"horse_number": 1, "history_count_before_race": 0}])
            feature_source = "db"
            metadata = {}

        _, runners = observations_from_feature_frame(_Res(), {})
        self.assertEqual(runners["1"]["history_status"], "UNKNOWN")

    def test_full_field_requires_set_equality(self):
        from app.predictions.corpus import finish_scope

        self.assertEqual(finish_scope([1, 2], [1, 2]), "UNLABELABLE")
        self.assertEqual(finish_scope([1, 2], [1, 2], result_field_size=2), "FULL_FIELD")
        self.assertEqual(finish_scope([1, 2], [1, 2, 3], result_field_size=3), "PARTIAL_RESULT")
        self.assertEqual(finish_scope([1, 2, 3], [1, 2], result_field_size=3), "PARTIAL_RESULT")
        self.assertEqual(
            finish_scope([1, 2], [1, 2], expected_starters=[1, 2, 3], result_field_size=3),
            "PARTIAL_RESULT",
        )
        self.assertEqual(
            finish_scope([1, 2, 3], [1, 2, 3], expected_starters=[1, 2], result_field_size=2),
            "PARTIAL_RESULT",
        )

    def test_unknown_history_not_training_coverage(self):
        from app.predictions.snapshot import collect_prediction_time_features, RACE_SNAPSHOT_KEYS, RUNNER_SNAPSHOT_KEYS

        created = "2026-08-01T03:00:00+00:00"
        race = {"observed_at": created}
        for key in RACE_SNAPSHOT_KEYS:
            race[key] = 1 if key != "surface" else "turf"
        runner = {"horse_number": 1, "observed_at": created, "history_status": "UNKNOWN"}
        for key in RUNNER_SNAPSHOT_KEYS:
            if key in ("history_status", "history_count_before_race"):
                continue
            runner[key] = 1
        snap = collect_prediction_time_features(captured_at=created, race_obs=race, runner_obs={"1": runner})
        self.assertEqual(snap["capture_status"], "complete")
        self.assertNotEqual(snap["training_coverage"], "complete")
        from app.predictions.provenance import training_auto_adopt

        self.assertFalse(
            training_auto_adopt(
                persist_source="site_prediction_run",
                engine_source="real_ai",
                fallback_reason=None,
                snapshot=snap,
                fingerprint_status="determined",
            )
        )

    def test_022_partial_repair_contract(self):
        with isolated_env():
            from app.data.db import (
                connect,
                migrate,
                prediction_run_schema_ready,
                prediction_run_schema_status,
                repair_prediction_run_schema,
            )

            migrate()
            conn = connect()
            try:
                conn.execute("DROP INDEX IF EXISTS uq_predictions_idempotency_key_not_null")
                conn.commit()
                self.assertEqual(prediction_run_schema_status(conn), "partial")
                self.assertFalse(prediction_run_schema_ready(conn))
                applied = migrate(conn)
                self.assertIn("022_prediction_run_idempotency:repair", applied)
                self.assertEqual(prediction_run_schema_status(conn), "complete")
                conn.execute("DROP INDEX IF EXISTS uq_predictions_idempotency_key_not_null")
                conn.commit()
                self.assertEqual(repair_prediction_run_schema(conn), "complete")
                conn.commit()
                self.assertEqual(prediction_run_schema_status(conn), "complete")
                self.assertTrue(prediction_run_schema_ready(conn))
                second = migrate(conn)
                self.assertNotIn("022_prediction_run_idempotency:repair", second)
            finally:
                conn.close()

    def test_reload_forbidden_is_feature_load_failed(self):
        from app.predictions.feature_pin import FeatureLoadFailed, FeatureLoadReloadForbidden

        self.assertTrue(issubclass(FeatureLoadReloadForbidden, FeatureLoadFailed))
        with self.assertRaises(FeatureLoadFailed):
            raise FeatureLoadReloadForbidden("no reload")

    def test_full_field_needs_independent_official_starters(self):
        from app.predictions.corpus import (
            finish_scope,
            parse_official_expected_starters,
            parse_official_finish_order,
        )

        self.assertEqual(
            finish_scope([1, 2], [1, 2], result_field_size=18),
            "PARTIAL_RESULT",
        )
        self.assertEqual(
            finish_scope([1, 2], [1, 2], expected_starters=[1, 2], result_field_size=18),
            "PARTIAL_RESULT",
        )
        self.assertEqual(
            finish_scope([1], [1], finish_is_winner_fallback=True, result_field_size=1),
            "UNLABELABLE",
        )
        finish, kind = parse_official_finish_order({})
        self.assertEqual(finish, [])
        self.assertEqual(kind, "absent")
        self.assertIsNone(parse_official_expected_starters({"finish_order": [1, 2]}))
        self.assertEqual(
            parse_official_expected_starters({"official_starters": [1, 2, 3]}),
            [1, 2, 3],
        )
        self.assertEqual(
            finish_scope(
                [1, 2, 3],
                [1, 2, 3],
                expected_starters=[1, 2, 3],
                result_field_size=3,
            ),
            "FULL_FIELD",
        )

    def test_bundle_runners_fail_closed(self):
        from app.predictions.corpus import finish_scope, inspect_bundle_runners

        self.assertEqual(inspect_bundle_runners({"evaluation": {"runners": []}})[1], "runners_empty")
        self.assertEqual(inspect_bundle_runners({"evaluation": {"runners": {}}})[1], "runners_empty")
        mixed = {"evaluation": {"runners": [{"horse_number": 1}, "bad"]}}
        self.assertEqual(inspect_bundle_runners(mixed)[1], "runner_row_not_object")
        dup = {
            "evaluation": {
                "runners": [
                    {"horse_number": 1, "win_prob": 0.4},
                    {"horse_number": 1, "win_prob": 0.2},
                ]
            }
        }
        self.assertEqual(inspect_bundle_runners(dup)[1], "horse_number_duplicate")
        bad_num = {"evaluation": {"runners": [{"horse_number": "x"}]}}
        self.assertEqual(inspect_bundle_runners(bad_num)[1], "horse_number_invalid")
        keyed = {"evaluation": {"runners": {"1": {"horse_number": 2}}}}
        self.assertEqual(inspect_bundle_runners(keyed)[1], "horse_number_invalid")
        nums, reason = inspect_bundle_runners(mixed)
        self.assertIsNone(nums)
        self.assertEqual(finish_scope(nums, [1], result_field_size=1), "UNLABELABLE")
        self.assertEqual(reason, "runner_row_not_object")

    def test_pin_rejects_other_race_id(self):
        from tests.ops.helpers import import_sample_data
        from tests.predictions.fake_platform import ensure_fake_ai_platform

        with isolated_env(engine="real"):
            ensure_fake_ai_platform()
            from app.data.db import migrate
            from app.predictions.feature_pin import FeatureLoadReloadForbidden, pin_feature_load
            from app.predictions.runs import confirm_prediction_inputs
            from ai_platform.core.features import FeatureLoader

            migrate()
            import_sample_data()
            confirmed = confirm_prediction_inputs("2026-07-19-04-11")
            with pin_feature_load(confirmed.feature_result, core_race_id="2026-07-19-04-11"):
                self.assertIs(FeatureLoader().load("2026-07-19-04-11"), confirmed.feature_result)
                with self.assertRaises(FeatureLoadReloadForbidden):
                    FeatureLoader().load("2026-07-19-04-12")

    def test_022_wrong_index_is_error_not_silent_complete(self):
        with isolated_env():
            from app.data.db import (
                connect,
                migrate,
                prediction_run_schema_ready,
                prediction_run_schema_status,
                repair_prediction_run_schema,
            )

            migrate()
            conn = connect()
            try:
                conn.execute("DROP INDEX IF EXISTS uq_predictions_idempotency_key_not_null")
                conn.execute(
                    "CREATE INDEX uq_predictions_idempotency_key_not_null "
                    "ON predictions(persist_source)"
                )
                conn.commit()
                self.assertEqual(prediction_run_schema_status(conn), "error")
                self.assertFalse(prediction_run_schema_ready(conn))
                status = repair_prediction_run_schema(conn)
                conn.commit()
                self.assertEqual(status, "complete")
                self.assertTrue(prediction_run_schema_ready(conn))
                conn.execute("DROP INDEX IF EXISTS uq_predictions_idempotency_key_not_null")
                conn.execute(
                    "CREATE UNIQUE INDEX uq_predictions_idempotency_key_not_null "
                    "ON predictions(idempotency_key)"
                )
                conn.commit()
                self.assertEqual(prediction_run_schema_status(conn), "error")
                self.assertEqual(repair_prediction_run_schema(conn), "complete")
                conn.commit()
            finally:
                conn.close()

    def test_nan_is_not_hashed_as_none(self):
        import pandas as pd

        from app.predictions.snapshot import (
            NonFiniteFeatureValue,
            canonical_feature_load_object,
            compute_input_snapshot_hash,
        )

        class _Res:
            def __init__(self, frame):
                self.frame = frame
                self.feature_source = "db"
                self.metadata = {}

        none_hash = compute_input_snapshot_hash(
            canonical_feature_load_object(
                _Res(pd.DataFrame([{"horse_number": 1, "popularity": None}])),
                race_id="R",
                core_race_id="C",
            )
        )
        with self.assertRaises(NonFiniteFeatureValue):
            canonical_feature_load_object(
                _Res(pd.DataFrame([{"horse_number": 1, "popularity": math.nan}])),
                race_id="R",
                core_race_id="C",
            )
        with self.assertRaises(NonFiniteFeatureValue):
            canonical_feature_load_object(
                _Res(pd.DataFrame([{"horse_number": 1, "popularity": math.inf}])),
                race_id="R",
                core_race_id="C",
            )
        self.assertEqual(len(none_hash), 64)

    def test_content_length_cannot_bypass_limit(self):
        from app.predictions.guards import parse_prediction_run_content_length

        self.assertIsNone(parse_prediction_run_content_length(None))
        self.assertIsNone(parse_prediction_run_content_length(""))
        self.assertIsNone(parse_prediction_run_content_length("abc"))
        self.assertIsNone(parse_prediction_run_content_length("-1"))
        self.assertEqual(parse_prediction_run_content_length("12"), 12)
        huge = json.dumps({"race_id": "x" * 5000}, ensure_ascii=False).encode("utf-8")
        with running_server(prediction_runs=True) as base:
            parsed = urlparse(base)
            host, port = parsed.hostname, parsed.port
            before = _count_predictions()
            for extra_headers in (
                {"Content-Length": "-1"},
                {"Content-Length": "not-a-number"},
                {},
            ):
                status, body = _raw_post_prediction_run(
                    host,
                    port,
                    huge,
                    extra_headers=extra_headers,
                )
                self.assertEqual(status, 413, body)
                self.assertEqual(body.get("error", {}).get("code"), "PREDICTION_RUN_BODY_TOO_LARGE")
            self.assertEqual(_count_predictions(), before)

    def test_prediction_must_be_before_result_finalized(self):
        from app.predictions.corpus import (
            _row_from_join,
            prediction_result_chronology,
            training_rows,
        )

        self.assertEqual(
            prediction_result_chronology("2026-08-01T03:00:00+00:00", "2026-08-01T04:00:00+00:00"),
            "BEFORE",
        )
        self.assertEqual(
            prediction_result_chronology("2026-08-01T04:00:00+00:00", "2026-08-01T04:00:00+00:00"),
            "EQUAL",
        )
        self.assertEqual(
            prediction_result_chronology("2026-08-01T04:00:01+00:00", "2026-08-01T04:00:00+00:00"),
            "AFTER",
        )
        self.assertEqual(prediction_result_chronology(None, "2026-08-01T04:00:00+00:00"), "MISSING")
        self.assertEqual(prediction_result_chronology("2026-08-01T03:00:00+00:00", "not-a-time"), "INVALID")
        self.assertEqual(
            prediction_result_chronology("2026-08-01T02:59:59+00:00", "2026-08-01T12:00:00+09:00"),
            "BEFORE",
        )
        self.assertEqual(
            prediction_result_chronology("2026-08-01T03:00:00+00:00", "2026-08-01T12:00:00+09:00"),
            "EQUAL",
        )

        def raw(created, finalized, race_id="R-CHRONO"):
            return {
                "prediction_id": 1,
                "race_id": race_id,
                "persist_source": "site_prediction_run",
                "engine_source": "real_ai",
                "fallback_reason": None,
                "model_version": "core-delegated",
                "bundle_json": json.dumps(
                    {
                        "schema_version": "single-prediction-bundle/2.0",
                        "evaluation": {
                            "runners": [
                                {"horse_number": 1, "win_prob": 0.4, "model_rank": 1, "mark": "honmei"},
                                {"horse_number": 2, "win_prob": 0.3, "model_rank": 2, "mark": "taikou"},
                            ]
                        },
                    },
                    ensure_ascii=False,
                ),
                "created_at": created,
                "race_date": "2026-08-01",
                "result_field_size": 2,
                "result_json": '{"finish_order":[1,2]}',
                "finalized_at": finalized,
            }

        before = _row_from_join(raw("2026-08-01T03:00:00+00:00", "2026-08-01T04:00:00+00:00"))
        equal = _row_from_join(raw("2026-08-01T04:00:00+00:00", "2026-08-01T04:00:00+00:00"))
        after = _row_from_join(raw("2026-08-01T05:00:00+00:00", "2026-08-01T04:00:00+00:00"))
        missing = _row_from_join(raw(None, "2026-08-01T04:00:00+00:00"))
        after["finish_scope"] = "FULL_FIELD"
        before["training_eligible"] = True
        equal["training_eligible"] = True
        after["training_eligible"] = True
        missing["training_eligible"] = True
        self.assertEqual(before["chronology_status"], "BEFORE")
        self.assertTrue(before["chronology_ok"])
        self.assertEqual(equal["chronology_status"], "EQUAL")
        self.assertEqual(after["chronology_status"], "AFTER")
        self.assertEqual(missing["chronology_status"], "MISSING")
        learned = training_rows([before, equal, after, missing])
        self.assertEqual([r["chronology_status"] for r in learned], ["BEFORE"])
        after["finish_scope"] = "FULL_FIELD"
        after["chronology_status"] = "AFTER"
        self.assertEqual(training_rows([after]), [])

    def test_raeval84_race_holdout_not_in_train_or_val(self):
        import hashlib
        import tempfile

        from app.predictions.corpus import assign_race_level_split, holdout_eval_rows, training_rows
        from app.predictions.raeval84_holdout import (
            EXPECTED_COUNT,
            EXPECTED_RACE_ID_LIST_SHA256,
            HoldoutContractError,
            DEFAULT_HOLDOUT_PATH,
            load_raeval84_holdout,
        )

        holdout = load_raeval84_holdout()
        self.assertEqual(len(holdout), EXPECTED_COUNT)
        self.assertEqual(
            hashlib.sha256(DEFAULT_HOLDOUT_PATH.read_bytes()).hexdigest(),
            EXPECTED_RACE_ID_LIST_SHA256,
        )
        frozen_race = "2026-07-26-01-02"
        self.assertIn(frozen_race, holdout)
        normal = {
            "prediction_id": 1,
            "race_id": "R-NORMAL",
            "race_date": "2026-08-01",
            "finish_scope": "FULL_FIELD",
            "chronology_status": "BEFORE",
        }
        holdout_other_pid = {
            "prediction_id": 999999,
            "race_id": frozen_race,
            "race_date": "2026-07-26",
            "finish_scope": "FULL_FIELD",
            "chronology_status": "BEFORE",
        }
        holdout_second_run = {
            "prediction_id": 888888,
            "race_id": frozen_race,
            "race_date": "2026-07-26",
            "finish_scope": "FULL_FIELD",
            "chronology_status": "BEFORE",
        }
        learned = training_rows([normal, holdout_other_pid, holdout_second_run])
        self.assertEqual([r["race_id"] for r in learned], ["R-NORMAL"])
        kept = holdout_eval_rows([normal, holdout_other_pid, holdout_second_run])
        self.assertEqual({r["prediction_id"] for r in kept}, {999999, 888888})
        split = assign_race_level_split(
            [
                ("R-NORMAL", "2026-08-01"),
                (frozen_race, "2026-07-26"),
                (frozen_race, "2026-07-26"),
            ],
            train_until="2026-09-06",
            val_until="2026-09-06",
        )
        self.assertEqual(split["R-NORMAL"], "train")
        self.assertEqual(split[frozen_race], "holdout")
        from app.predictions.raeval84_holdout import holdout_metrics

        metrics = holdout_metrics(split)
        self.assertEqual(metrics["RAEVAL84_IN_TRAIN_OR_VAL_COUNT"], 0)
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "holdout.txt"
            bad.write_bytes(DEFAULT_HOLDOUT_PATH.read_bytes() + b"tamper\n")
            with self.assertRaises(HoldoutContractError):
                load_raeval84_holdout(bad)
            with self.assertRaises(HoldoutContractError):
                training_rows([normal], holdout_path=bad)
            short = Path(tmp) / "short.txt"
            lines = DEFAULT_HOLDOUT_PATH.read_text(encoding="utf-8").splitlines()[:83]
            payload = ("\n".join(lines) + "\n").encode("utf-8")
            short.write_bytes(payload)
            with self.assertRaises(HoldoutContractError):
                load_raeval84_holdout(short, expected_sha=hashlib.sha256(payload).hexdigest())
            long = Path(tmp) / "long.txt"
            extra = DEFAULT_HOLDOUT_PATH.read_text(encoding="utf-8").splitlines() + ["2099-01-01-01-01"]
            long_payload = ("\n".join(extra) + "\n").encode("utf-8")
            long.write_bytes(long_payload)
            with self.assertRaises(HoldoutContractError):
                load_raeval84_holdout(long, expected_sha=hashlib.sha256(long_payload).hexdigest())

    def test_rate_limit_lock_sweeps_expired_identities(self):
        from app.predictions import guards as g

        g.reset_prediction_run_rate_limit()
        os.environ["PREDICTION_RUN_RATE_WINDOW_SEC"] = "30"
        try:
            now = 1_000_000.0
            with g._rate_lock:
                g._rate_hits["old"] = [now - 120]
                g._rate_hits["keep"] = [now - 1]
                g._sweep_rate_hits(now, 30.0)
                self.assertNotIn("old", g._rate_hits)
                self.assertIn("keep", g._rate_hits)
        finally:
            os.environ.pop("PREDICTION_RUN_RATE_WINDOW_SEC", None)
            g.reset_prediction_run_rate_limit()


def _raw_post_prediction_run(
    host: str,
    port: int,
    body: bytes,
    *,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, dict]:
    headers = {
        "Host": "%s:%s" % (host, port),
        "Content-Type": "application/json; charset=utf-8",
        "X-Prediction-Run-Key": "test-run-key",
        "Connection": "close",
    }
    if extra_headers:
        headers.update(extra_headers)
    lines = ["POST /v1/prediction-runs HTTP/1.1"]
    lines.extend("%s: %s" % item for item in headers.items())
    raw = ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8") + body
    sock = socket.create_connection((host, int(port)), timeout=5)
    try:
        sock.sendall(raw)
        sock.settimeout(5)
        chunks: list[bytes] = []
        while True:
            try:
                piece = sock.recv(4096)
            except socket.timeout:
                break
            if not piece:
                break
            chunks.append(piece)
    finally:
        sock.close()
    data = b"".join(chunks)
    head, _, rest = data.partition(b"\r\n\r\n")
    status_line = head.split(b"\r\n", 1)[0].decode("latin1", "replace")
    parts = status_line.split()
    status = int(parts[1]) if len(parts) > 1 else 0
    try:
        payload = json.loads(rest.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {"raw": rest.decode("utf-8", "replace")}
    return status, payload


if __name__ == "__main__":
    unittest.main()
