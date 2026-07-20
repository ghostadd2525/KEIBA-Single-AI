# -*- coding: utf-8 -*-
"""Supply platform repositories — ETL runs, import history, validation."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ..db import connect, migrate


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupplyRepository:
    def __init__(self) -> None:
        migrate()

    def create_run(self, race_date: str, source_type: str) -> int:
        conn = connect()
        try:
            cur = conn.execute(
                """
                INSERT INTO etl_runs(race_date, status, source_type, started_at)
                VALUES (?, 'running', ?, ?)
                """,
                (race_date, source_type, _now()),
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
        stopped_at_step: str | None = None,
        error_reason: str | None = None,
        missing_data: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        conn = connect()
        try:
            conn.execute(
                """
                UPDATE etl_runs SET
                  status = ?,
                  stopped_at_step = ?,
                  error_reason = ?,
                  missing_data_json = ?,
                  result_json = ?,
                  finished_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    stopped_at_step,
                    error_reason,
                    json.dumps(missing_data or {}, ensure_ascii=False),
                    json.dumps(result or {}, ensure_ascii=False),
                    _now(),
                    run_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def add_step(
        self,
        run_id: int,
        step: str,
        status: str,
        detail: dict[str, Any] | None = None,
        *,
        finished: bool = True,
    ) -> None:
        conn = connect()
        try:
            now = _now()
            conn.execute(
                """
                INSERT INTO etl_steps(run_id, step, status, detail_json, started_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    step,
                    status,
                    json.dumps(detail or {}, ensure_ascii=False),
                    now,
                    now if finished else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def add_import_history(
        self,
        *,
        run_id: int,
        race_date: str,
        source_type: str,
        races_count: int,
        features_count: int,
        entries_count: int = 0,
        horses_count: int = 0,
        skipped_count: int = 0,
        detail: dict[str, Any] | None = None,
    ) -> None:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO import_history(
                  run_id, race_date, source_type,
                  races_count, features_count, entries_count, horses_count,
                  skipped_count, detail_json, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    run_id,
                    race_date,
                    source_type,
                    races_count,
                    features_count,
                    entries_count,
                    horses_count,
                    skipped_count,
                    json.dumps(detail or {}, ensure_ascii=False),
                    _now(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def save_validation(
        self,
        *,
        run_id: int | None,
        race_date: str,
        coverage: dict[str, Any],
        items: list[dict[str, Any]],
        by_reason: dict[str, int],
    ) -> int:
        conn = connect()
        try:
            cur = conn.execute(
                """
                INSERT INTO validation_runs(
                  run_id, race_date, race_total, real_ai, mock, coverage,
                  missing_features, missing_races, by_reason_json, items_json, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    run_id,
                    race_date,
                    coverage.get("race_total", 0),
                    coverage.get("real_ai", 0),
                    coverage.get("mock", 0),
                    coverage.get("coverage", 0),
                    coverage.get("missing_features", 0),
                    coverage.get("missing_races", 0),
                    json.dumps(by_reason, ensure_ascii=False),
                    json.dumps(items, ensure_ascii=False),
                    _now(),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def latest_run(self, race_date: str | None = None) -> dict[str, Any] | None:
        conn = connect()
        try:
            if race_date:
                row = conn.execute(
                    "SELECT * FROM etl_runs WHERE race_date = ? ORDER BY id DESC LIMIT 1",
                    (race_date,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM etl_runs ORDER BY id DESC LIMIT 1"
                ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT * FROM etl_runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def steps_for_run(self, run_id: int) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT * FROM etl_steps WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["detail"] = json.loads(d.pop("detail_json") or "{}")
                out.append(d)
            return out
        finally:
            conn.close()

    def list_import_history(self, limit: int = 20) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT * FROM import_history ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["detail"] = json.loads(d.pop("detail_json") or "{}")
                out.append(d)
            return out
        finally:
            conn.close()

    def latest_validation(self, race_date: str | None = None) -> dict[str, Any] | None:
        conn = connect()
        try:
            if race_date:
                row = conn.execute(
                    "SELECT * FROM validation_runs WHERE race_date = ? ORDER BY id DESC LIMIT 1",
                    (race_date,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM validation_runs ORDER BY id DESC LIMIT 1"
                ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["by_reason"] = json.loads(d.pop("by_reason_json") or "{}")
            d["items"] = json.loads(d.pop("items_json") or "[]")
            return d
        finally:
            conn.close()

    def list_validations(self, limit: int = 10) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT * FROM validation_runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["by_reason"] = json.loads(d.pop("by_reason_json") or "{}")
                d.pop("items_json", None)
                out.append(d)
            return out
        finally:
            conn.close()
