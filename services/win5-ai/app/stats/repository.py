# -*- coding: utf-8 -*-
"""Stats persistence — minimal Production repository."""
from __future__ import annotations

import json
from typing import Any

from ..data import db as app_db


class StatsRepository:
    def start_run(self, trigger_source: str) -> int:
        conn = app_db.connect()
        try:
            cur = conn.execute(
                """
                INSERT INTO self_evaluation_runs(race_date, trigger_source, status, created_at)
                VALUES (NULL, ?, 'running', datetime('now'))
                """,
                (trigger_source,),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        races_imported: int = 0,
        races_evaluated: int = 0,
        meta: dict[str, Any] | None = None,
    ) -> None:
        conn = app_db.connect()
        try:
            conn.execute(
                """
                UPDATE self_evaluation_runs SET
                  status=?, races_evaluated=?, meta_json=?, finished_at=datetime('now')
                WHERE id=?
                """,
                (
                    status,
                    races_evaluated,
                    json.dumps(meta or {}, ensure_ascii=False),
                    run_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def upsert_race_result(self, row: dict[str, Any]) -> None:
        conn = app_db.connect()
        try:
            conn.execute(
                """
                INSERT INTO race_results(
                  race_id, race_date, venue, meeting_id, surface, distance, going,
                  winner_horse_number, field_size, result_json, source, finalized_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?, datetime('now'))
                ON CONFLICT(race_id) DO UPDATE SET
                  race_date=excluded.race_date,
                  venue=excluded.venue,
                  winner_horse_number=excluded.winner_horse_number,
                  result_json=excluded.result_json,
                  finalized_at=datetime('now')
                """,
                (
                    row.get("race_id"),
                    row.get("race_date"),
                    row.get("venue"),
                    row.get("meeting_id"),
                    row.get("surface"),
                    row.get("distance"),
                    row.get("going"),
                    row.get("winner_horse_number"),
                    row.get("field_size"),
                    json.dumps(row.get("result_json") or {}, ensure_ascii=False),
                    row.get("source") or "import",
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def list_race_results(self, *, race_date: str | None = None) -> list[dict[str, Any]]:
        conn = app_db.connect()
        try:
            if race_date:
                rows = conn.execute(
                    "SELECT * FROM race_results WHERE race_date = ? ORDER BY race_id",
                    (race_date,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM race_results ORDER BY race_date, race_id"
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def latest_prediction_for_race(self, race_id: str) -> dict[str, Any] | None:
        conn = app_db.connect()
        try:
            row = conn.execute(
                """
                SELECT * FROM predictions WHERE race_id = ?
                ORDER BY created_at DESC, id DESC LIMIT 1
                """,
                (race_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def save_race_evaluation(self, run_id: int, row: dict[str, Any]) -> None:
        conn = app_db.connect()
        try:
            conn.execute(
                """
                INSERT INTO race_evaluations(
                  run_id, race_id, prediction_id, race_date, venue,
                  hit_at_1, hit_at_3, hit_at_5, miss_category,
                  engine_source, model_version, evaluated_at, meta_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    run_id,
                    row.get("race_id"),
                    row.get("prediction_id"),
                    row.get("race_date"),
                    row.get("venue"),
                    1 if row.get("hit_at_1") else 0,
                    1 if row.get("hit_at_3") else 0,
                    1 if row.get("hit_at_5") else 0,
                    row.get("miss_category"),
                    row.get("engine_source"),
                    row.get("model_version"),
                    row.get("evaluated_at"),
                    json.dumps({"feature_source": row.get("feature_source")}, ensure_ascii=False),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def replace_aggregates(self, run_id: int, aggregates: list[dict[str, Any]]) -> None:
        # Aggregates stored in self_evaluation meta for now
        return None

    def upsert_timeseries(self, row: dict[str, Any]) -> None:
        return None

    def latest_run(self) -> dict[str, Any] | None:
        conn = app_db.connect()
        try:
            row = conn.execute(
                "SELECT * FROM self_evaluation_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
