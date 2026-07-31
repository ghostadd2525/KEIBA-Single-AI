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
                  surface=COALESCE(excluded.surface, race_results.surface),
                  distance=COALESCE(excluded.distance, race_results.distance),
                  going=COALESCE(excluded.going, race_results.going),
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
                    json.dumps(
                        {
                            "feature_source": row.get("feature_source"),
                            "surface": row.get("surface"),
                            "distance": row.get("distance"),
                            "going": row.get("going"),
                        },
                        ensure_ascii=False,
                    ),
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

    @staticmethod
    def _pct(num: float, den: int) -> float:
        if den <= 0:
            return 0.0
        return round(num / den, 4)

    def _aggregate_rows(self, rows: list[dict[str, Any]], *, dimension: str, key: str) -> dict[str, Any]:
        n = len(rows)
        h1 = sum(1 for g in rows if g.get("hit_at_1"))
        h3 = sum(1 for g in rows if g.get("hit_at_3"))
        h5 = sum(1 for g in rows if g.get("hit_at_5"))
        dates = sorted({str(g.get("race_date") or "") for g in rows if g.get("race_date")})
        updated = None
        for g in rows:
            ts = g.get("evaluated_at")
            if ts and (updated is None or str(ts) > str(updated)):
                updated = ts
        return {
            "dimension": dimension,
            "dimension_key": key,
            "period_start": dates[0] if dates else None,
            "period_end": dates[-1] if dates else None,
            "races_evaluated": n,
            "prediction_count": n,
            "hit_at_1": self._pct(h1, n),
            "hit_at_3": self._pct(h3, n),
            "hit_at_5": self._pct(h5, n),
            "roi": None,
            "updated_at": updated,
        }

    def get_overall_aggregate(self, run_id: int) -> dict[str, Any] | None:
        """V8.9.1: live all-time aggregate from race_evaluations (run_id unused for source)."""
        _ = run_id
        rows = self.list_evaluations_with_results()
        if not rows:
            return None
        return self._aggregate_rows(rows, dimension="overall", key="all")

    def get_aggregates(self, run_id: int, dimension: str) -> list[dict[str, Any]]:
        """V8.9.1: live dimension buckets from race_evaluations."""
        _ = run_id
        rows = self.list_evaluations_with_results()
        if not rows:
            return []
        dim = str(dimension or "month")
        buckets: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            if dim == "month":
                key = str(row.get("race_date") or "")[:7] or "unknown"
            elif dim == "venue":
                key = str(row.get("venue") or "unknown")
            else:
                key = str(row.get(dim) or "unknown")
            buckets.setdefault(key, []).append(row)
        return [
            self._aggregate_rows(group, dimension=dim, key=key)
            for key, group in sorted(buckets.items())
        ]

    def list_evaluations_with_results(self) -> list[dict[str, Any]]:
        """All-time AI evaluations joined with results. One row per race_id (latest)."""
        conn = app_db.connect()
        try:
            rows = conn.execute(
                """
                SELECT
                  e.hit_at_1, e.hit_at_3, e.hit_at_5, e.race_id, e.race_date, e.venue,
                  COALESCE(r.surface, json_extract(e.meta_json, '$.surface')) AS surface,
                  COALESCE(r.distance, CAST(json_extract(e.meta_json, '$.distance') AS INTEGER)) AS distance,
                  COALESCE(r.going, json_extract(e.meta_json, '$.going')) AS going,
                  e.evaluated_at, e.id
                FROM race_evaluations e
                LEFT JOIN race_results r ON r.race_id = e.race_id
                ORDER BY e.evaluated_at DESC, e.id DESC
                """
            ).fetchall()
            out: list[dict[str, Any]] = []
            seen: set[str] = set()
            for row in rows:
                item = dict(row)
                rid = str(item.get("race_id") or "")
                if not rid or rid in seen:
                    continue
                seen.add(rid)
                item["hit_at_1"] = bool(item.get("hit_at_1"))
                item["hit_at_3"] = bool(item.get("hit_at_3"))
                item["hit_at_5"] = bool(item.get("hit_at_5"))
                out.append(item)
            return out
        finally:
            conn.close()
