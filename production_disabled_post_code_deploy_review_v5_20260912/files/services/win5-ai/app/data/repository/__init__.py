# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from ..db import connect, db_path, migrate


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect_idempotent() -> sqlite3.Connection:
    """Hot-path connection for concurrent save_idempotent().

    Keeps sqlite timeout, IMMEDIATE isolation, and busy_timeout so
    same-key writers serialize on one transaction. Does not change
    journal_mode on every connect: rewriting the journal from multiple
    processes races with ``sqlite3.OperationalError: database is locked``.
    WAL, when wanted, is initialized once in ``app.data.db.migrate()``
    via ``ensure_wal_journal()``. OperationalError is not swallowed.
    """
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0, isolation_level="IMMEDIATE")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def _prediction_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    raw = item.get("bundle_json")
    try:
        item["bundle"] = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        item["bundle"] = {}
    return item


class RaceRepository:
    def __init__(self) -> None:
        migrate()

    def upsert(self, row: dict[str, Any]) -> None:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO races(
                  race_id, core_race_id, public_race_id, venue_code,
                  date, venue, race_no, meeting_id, surface, distance,
                  class_label, grade, field_size, post_time, status, source,
                  extra_json, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(race_id) DO UPDATE SET
                  core_race_id=excluded.core_race_id,
                  public_race_id=excluded.public_race_id,
                  venue_code=excluded.venue_code,
                  date=excluded.date,
                  venue=excluded.venue,
                  race_no=excluded.race_no,
                  meeting_id=excluded.meeting_id,
                  surface=excluded.surface,
                  distance=excluded.distance,
                  class_label=excluded.class_label,
                  grade=excluded.grade,
                  field_size=excluded.field_size,
                  post_time=excluded.post_time,
                  status=excluded.status,
                  source=excluded.source,
                  extra_json=excluded.extra_json,
                  updated_at=excluded.updated_at
                """,
                (
                    row["race_id"],
                    row.get("core_race_id"),
                    row.get("public_race_id"),
                    row.get("venue_code"),
                    row.get("date"),
                    row.get("venue"),
                    int(row.get("race_no") or 0),
                    row.get("meeting_id"),
                    row.get("surface"),
                    row.get("distance"),
                    row.get("class_label") or row.get("race_name"),
                    row.get("grade") or row.get("badge"),
                    row.get("field_size") or row.get("horse_count"),
                    row.get("post_time"),
                    row.get("status"),
                    row.get("source"),
                    json.dumps(row.get("extra") or {}, ensure_ascii=False),
                    _now(),
                    _now(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get(self, race_id: str) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT * FROM races WHERE race_id = ?", (race_id,)
            ).fetchone()
            if row:
                return dict(row)
            row = conn.execute(
                "SELECT * FROM races WHERE core_race_id = ?", (race_id,)
            ).fetchone()
            if row:
                return dict(row)
            row = conn.execute(
                "SELECT * FROM races WHERE public_race_id = ?", (race_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list(
        self,
        *,
        date: str | None = None,
        venue: str | None = None,
        race_no: int | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        conn = connect()
        try:
            sql = "SELECT * FROM races WHERE 1=1"
            params: list[Any] = []
            if date:
                sql += " AND date = ?"
                params.append(date)
            if venue:
                sql += " AND venue = ?"
                params.append(venue)
            if race_no is not None:
                sql += " AND race_no = ?"
                params.append(int(race_no))
            sql += " ORDER BY date, venue, race_no LIMIT ?"
            params.append(limit)
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    def as_catalog(self) -> dict[str, Any]:
        races = self.list(limit=500)
        venues = sorted({r["venue"] for r in races if r.get("venue")})
        dates = sorted({r["date"] for r in races if r.get("date")})
        return {
            "date": dates[-1] if dates else "",
            "venues": venues,
            "races": [
                {
                    "race_id": r["race_id"],
                    "core_race_id": r.get("core_race_id"),
                    "public_race_id": r.get("public_race_id"),
                    "date": r["date"],
                    "venue": r["venue"],
                    "race_no": r["race_no"],
                    "post_time": r.get("post_time"),
                    "class_label": r.get("class_label"),
                    "badge": r.get("grade"),
                    "surface": r.get("surface"),
                    "distance": r.get("distance"),
                    "field_size": r.get("field_size"),
                    "status": r.get("status") or "scheduled",
                }
                for r in races
            ],
        }


class FeatureRepository:
    def __init__(self) -> None:
        migrate()

    def upsert_row(
        self,
        *,
        race_id: str,
        horse_number: int | None,
        payload: dict[str, Any],
        feature_set: str = "runners_pace_market",
        source_file: str | None = None,
        horse_id: str | None = None,
    ) -> None:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO features(race_id, horse_number, horse_id, feature_set, payload_json, source_file, created_at)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(race_id, horse_number, feature_set) DO UPDATE SET
                  payload_json=excluded.payload_json,
                  source_file=excluded.source_file,
                  horse_id=excluded.horse_id
                """,
                (
                    race_id,
                    horse_number,
                    horse_id,
                    feature_set,
                    json.dumps(payload, ensure_ascii=False),
                    source_file,
                    _now(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def list_for_race(self, race_id: str, feature_set: str = "runners_pace_market") -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT * FROM features WHERE race_id = ? AND feature_set = ?",
                (race_id, feature_set),
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["payload"] = json.loads(d.pop("payload_json") or "{}")
                out.append(d)
            return out
        finally:
            conn.close()


class HorseRepository:
    def __init__(self) -> None:
        migrate()

    def upsert(self, row: dict[str, Any]) -> None:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO horses(horse_id, horse_name, created_at, updated_at)
                VALUES (?,?,?,?)
                ON CONFLICT(horse_id) DO UPDATE SET
                  horse_name=excluded.horse_name,
                  updated_at=excluded.updated_at
                """,
                (
                    row["horse_id"],
                    row.get("horse_name") or "",
                    _now(),
                    _now(),
                ),
            )
            conn.commit()
        finally:
            conn.close()


class EntryRepository:
    def __init__(self) -> None:
        migrate()

    def upsert(self, row: dict[str, Any]) -> None:
        conn = connect()
        try:
            extra = row.get("extra")
            if extra is None and row.get("weight") is not None:
                extra = {"weight": row.get("weight")}
            extra_json = json.dumps(extra, ensure_ascii=False) if extra is not None else None
            conn.execute(
                """
                INSERT INTO entries(
                  race_id, horse_id, horse_number, horse_name,
                  frame_number, jockey, odds, popularity, extra_json
                ) VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(race_id, horse_number) DO UPDATE SET
                  horse_id=excluded.horse_id,
                  horse_name=excluded.horse_name,
                  frame_number=excluded.frame_number,
                  jockey=excluded.jockey,
                  odds=excluded.odds,
                  popularity=excluded.popularity,
                  extra_json=COALESCE(excluded.extra_json, entries.extra_json)
                """,
                (
                    row["race_id"],
                    row.get("horse_id"),
                    row.get("horse_number"),
                    row.get("horse_name"),
                    row.get("frame_number") if row.get("frame_number") is not None else row.get("frame"),
                    row.get("jockey"),
                    row.get("odds"),
                    row.get("popularity"),
                    extra_json,
                ),
            )
            conn.commit()
        finally:
            conn.close()


class PredictionRepository:
    def __init__(self) -> None:
        migrate()

    def save(
        self,
        *,
        race_id: str,
        bundle: dict[str, Any],
        engine_source: str,
        fallback_reason: str | None = None,
        core_race_id: str | None = None,
        model_version: str | None = None,
    ) -> None:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO predictions(
                  race_id, core_race_id, engine_source, fallback_reason,
                  model_version, bundle_json, created_at
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (
                    race_id,
                    core_race_id,
                    engine_source,
                    fallback_reason,
                    model_version,
                    json.dumps(bundle, ensure_ascii=False),
                    _now(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def lookup_by_idempotency_key(self, key: str) -> dict[str, Any] | None:
        if not key:
            return None
        conn = connect()
        try:
            row = conn.execute(
                """
                SELECT id, race_id, core_race_id, engine_source, fallback_reason,
                       model_version, bundle_json, created_at, idempotency_key,
                       persist_source, input_snapshot_hash, prediction_semantic_hash
                FROM predictions
                WHERE idempotency_key = ?
                ORDER BY id ASC
                LIMIT 1
                """,
                (key,),
            ).fetchone()
            if not row:
                return None
            return _prediction_row(row)
        finally:
            conn.close()

    def save_idempotent(
        self,
        *,
        race_id: str,
        bundle: dict[str, Any],
        engine_source: str,
        idempotency_key: str,
        persist_source: str,
        input_snapshot_hash: str,
        prediction_semantic_hash: str,
        fallback_reason: str | None = None,
        core_race_id: str | None = None,
        model_version: str | None = None,
    ) -> "IdempotentSaveResult":
        """POST-only. save() は変更しない。UNIQUE 競合時は SELECT して semantic 比較。"""
        from ...predictions.provenance import IdempotencyConflictError, IdempotentSaveResult

        stored = dict(bundle)
        stored.pop("prediction_id", None)
        payload = json.dumps(stored, ensure_ascii=False)
        conn = _connect_idempotent()
        try:
            conn.execute(
                """
                INSERT INTO predictions(
                  race_id, core_race_id, engine_source, fallback_reason, model_version,
                  bundle_json, created_at, idempotency_key, persist_source,
                  input_snapshot_hash, prediction_semantic_hash
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(idempotency_key) WHERE idempotency_key IS NOT NULL
                DO NOTHING
                """,
                (
                    race_id,
                    core_race_id,
                    engine_source,
                    fallback_reason,
                    model_version,
                    payload,
                    _now(),
                    idempotency_key,
                    persist_source,
                    input_snapshot_hash,
                    prediction_semantic_hash,
                ),
            )
            changes = conn.execute("SELECT changes()").fetchone()[0]
            if int(changes) == 1:
                rowid = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
                conn.commit()
                return IdempotentSaveResult(
                    prediction_id=rowid,
                    replayed=False,
                    persist_source=persist_source,
                    idempotency_key=idempotency_key,
                    prediction_semantic_hash=prediction_semantic_hash,
                    bundle=stored,
                )
            existing = conn.execute(
                """
                SELECT id, prediction_semantic_hash, bundle_json, persist_source
                FROM predictions
                WHERE idempotency_key = ?
                ORDER BY id ASC
                LIMIT 1
                """,
                (idempotency_key,),
            ).fetchone()
            if existing is None:
                raise RuntimeError("idempotency_conflict_row_missing")
            existing_semantic = str(existing["prediction_semantic_hash"] or "")
            if existing_semantic != prediction_semantic_hash:
                raise IdempotencyConflictError(
                    "same idempotency_key stored a different semantic prediction",
                    prediction_id=int(existing["id"]),
                    idempotency_key=idempotency_key,
                )
            try:
                existing_bundle = json.loads(existing["bundle_json"] or "{}")
            except json.JSONDecodeError:
                existing_bundle = stored
            conn.commit()
            return IdempotentSaveResult(
                prediction_id=int(existing["id"]),
                replayed=True,
                persist_source=str(existing["persist_source"] or persist_source),
                idempotency_key=idempotency_key,
                prediction_semantic_hash=existing_semantic,
                bundle=existing_bundle if isinstance(existing_bundle, dict) else stored,
            )
        finally:
            conn.close()


class LogRepository:
    def __init__(self) -> None:
        migrate()

    def write(
        self,
        *,
        level: str,
        category: str,
        message: str,
        race_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO logs(level, category, message, race_id, payload_json, created_at)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    level,
                    category,
                    message,
                    race_id,
                    json.dumps(payload or {}, ensure_ascii=False),
                    _now(),
                ),
            )
            conn.commit()
        finally:
            conn.close()


class ConversationRepository:
    def __init__(self) -> None:
        migrate()

    def append(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        intent: str | None = None,
        race_id: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO conversation_history(
                  session_id, role, content, intent, race_id, meta_json, created_at
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (
                    session_id,
                    role,
                    content,
                    intent,
                    race_id,
                    json.dumps(meta or {}, ensure_ascii=False),
                    _now(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def list_session(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM conversation_history
                WHERE session_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
            return [dict(r) for r in reversed(rows)]
        finally:
            conn.close()
