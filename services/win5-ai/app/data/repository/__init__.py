# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ..db import connect, migrate


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            conn.execute(
                """
                INSERT INTO entries(
                  race_id, horse_id, horse_number, horse_name,
                  jockey, odds, popularity
                ) VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(race_id, horse_number) DO UPDATE SET
                  horse_id=excluded.horse_id,
                  horse_name=excluded.horse_name,
                  jockey=excluded.jockey,
                  odds=excluded.odds,
                  popularity=excluded.popularity
                """,
                (
                    row["race_id"],
                    row.get("horse_id"),
                    row.get("horse_number"),
                    row.get("horse_name"),
                    row.get("jockey"),
                    row.get("odds"),
                    row.get("popularity"),
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
