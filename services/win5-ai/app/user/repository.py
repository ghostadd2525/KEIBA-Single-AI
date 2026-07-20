# -*- coding: utf-8 -*-
"""User Domain repositories — independent from Prediction Core."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from ..data.db import connect, migrate


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires(hours: int = 24) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


class UserRepository:
    def __init__(self) -> None:
        migrate()

    def create(
        self,
        *,
        login_id: str,
        password_hash: str,
        invite_id: str | None = None,
        terms_version: str | None = None,
    ) -> dict[str, Any]:
        user_id = str(uuid.uuid4())
        now = _now()
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO users(
                  user_id, login_id, password_hash, status, invite_id,
                  terms_version, terms_accepted_at, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    user_id,
                    login_id,
                    password_hash,
                    "active",
                    invite_id,
                    terms_version,
                    now if terms_version else None,
                    now,
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_by_id(user_id) or {}

    def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_by_login_id(self, login_id: str) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE login_id = ?", (login_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update(self, user_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
        allowed = {"status", "terms_version", "terms_accepted_at"}
        sets = []
        params: list[Any] = []
        for key, value in fields.items():
            if key in allowed:
                sets.append(f"{key} = ?")
                params.append(value)
        if not sets:
            return self.get_by_id(user_id)
        sets.append("updated_at = ?")
        params.append(_now())
        params.append(user_id)
        conn = connect()
        try:
            conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE user_id = ?", params)
            conn.commit()
        finally:
            conn.close()
        return self.get_by_id(user_id)

    def list_users(self, *, limit: int = 100) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT user_id, login_id, status, created_at, updated_at FROM users ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


class ProfileRepository:
    def __init__(self) -> None:
        migrate()

    def upsert(self, user_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        conn = connect()
        try:
            existing = conn.execute(
                "SELECT user_id FROM profiles WHERE user_id = ?", (user_id,)
            ).fetchone()
            now = _now()
            prefs = fields.get("preferences")
            prefs_json = json.dumps(prefs, ensure_ascii=False) if prefs is not None else None
            if existing:
                conn.execute(
                    """
                    UPDATE profiles SET
                      display_name = COALESCE(?, display_name),
                      avatar_url = COALESCE(?, avatar_url),
                      locale = COALESCE(?, locale),
                      preferences_json = COALESCE(?, preferences_json),
                      updated_at = ?
                    WHERE user_id = ?
                    """,
                    (
                        fields.get("display_name"),
                        fields.get("avatar_url"),
                        fields.get("locale"),
                        prefs_json,
                        now,
                        user_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO profiles(user_id, display_name, avatar_url, locale, preferences_json, updated_at)
                    VALUES (?,?,?,?,?,?)
                    """,
                    (
                        user_id,
                        fields.get("display_name"),
                        fields.get("avatar_url"),
                        fields.get("locale") or "ja",
                        prefs_json,
                        now,
                    ),
                )
            conn.commit()
        finally:
            conn.close()
        return self.get(user_id) or {"user_id": user_id}

    def get(self, user_id: str) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
            if not row:
                return None
            data = dict(row)
            if data.get("preferences_json"):
                try:
                    data["preferences"] = json.loads(data["preferences_json"])
                except json.JSONDecodeError:
                    data["preferences"] = {}
            return data
        finally:
            conn.close()


class SessionRepository:
    def __init__(self) -> None:
        migrate()

    def create(
        self,
        *,
        session_id: str,
        user_id: str,
        token_hash: str,
        expires_in: int = 86400,
        user_agent: str | None = None,
    ) -> None:
        now = _now()
        exp = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO user_sessions(session_id, user_id, token_hash, expires_at, created_at, last_seen_at, user_agent)
                VALUES (?,?,?,?,?,?,?)
                """,
                (session_id, user_id, token_hash, exp, now, now, user_agent),
            )
            conn.commit()
        finally:
            conn.close()

    def get_by_token_hash(self, token_hash: str) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute(
                """
                SELECT * FROM user_sessions
                WHERE token_hash = ? AND expires_at > ?
                """,
                (token_hash, _now()),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def touch(self, session_id: str) -> None:
        conn = connect()
        try:
            conn.execute(
                "UPDATE user_sessions SET last_seen_at = ? WHERE session_id = ?",
                (_now(), session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def revoke(self, session_id: str) -> None:
        conn = connect()
        try:
            conn.execute("DELETE FROM user_sessions WHERE session_id = ?", (session_id,))
            conn.commit()
        finally:
            conn.close()

    def list_for_user(self, user_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT session_id, expires_at, created_at, last_seen_at, user_agent
                FROM user_sessions WHERE user_id = ?
                ORDER BY last_seen_at DESC LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


class FavoriteRepository:
    MAX_FAVORITES = 3

    def __init__(self) -> None:
        migrate()

    def list_for_user(self, user_id: str) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM favorites WHERE user_id = ?
                ORDER BY added_at DESC LIMIT ?
                """,
                (user_id, self.MAX_FAVORITES),
            ).fetchall()
            out: list[dict[str, Any]] = []
            for row in rows:
                item = dict(row)
                if item.get("meta_json"):
                    try:
                        item["meta"] = json.loads(item["meta_json"])
                    except json.JSONDecodeError:
                        item["meta"] = {}
                out.append(item)
            return out
        finally:
            conn.close()

    def upsert(self, user_id: str, item: dict[str, Any]) -> list[dict[str, Any]]:
        race_id = str(item.get("race_id") or "").strip()
        if not race_id:
            raise ValueError("race_id required")
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO favorites(
                  user_id, race_id, place, name, badge, post_time, date_label, meta_json, added_at
                ) VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(user_id, race_id) DO UPDATE SET
                  place=excluded.place,
                  name=excluded.name,
                  badge=excluded.badge,
                  post_time=excluded.post_time,
                  date_label=excluded.date_label,
                  meta_json=excluded.meta_json,
                  added_at=excluded.added_at
                """,
                (
                    user_id,
                    race_id,
                    item.get("place"),
                    item.get("name"),
                    item.get("badge"),
                    item.get("post_time"),
                    item.get("date_label"),
                    json.dumps(item.get("meta") or {}, ensure_ascii=False),
                    _now(),
                ),
            )
            conn.commit()
            rows = conn.execute(
                "SELECT id FROM favorites WHERE user_id = ? ORDER BY added_at DESC",
                (user_id,),
            ).fetchall()
            if len(rows) > self.MAX_FAVORITES:
                drop_ids = [r["id"] for r in rows[self.MAX_FAVORITES :]]
                for fid in drop_ids:
                    conn.execute("DELETE FROM favorites WHERE id = ?", (fid,))
                conn.commit()
        finally:
            conn.close()
        return self.list_for_user(user_id)

    def remove(self, user_id: str, race_id: str) -> list[dict[str, Any]]:
        conn = connect()
        try:
            conn.execute(
                "DELETE FROM favorites WHERE user_id = ? AND race_id = ?",
                (user_id, race_id),
            )
            conn.commit()
        finally:
            conn.close()
        return self.list_for_user(user_id)


class PredictionHistoryRepository:
    def __init__(self) -> None:
        migrate()

    def record(
        self,
        *,
        user_id: str,
        race_id: str,
        engine_source: str | None = None,
        feature_source: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO prediction_history(
                  user_id, race_id, engine_source, feature_source, viewed_at, meta_json
                ) VALUES (?,?,?,?,?,?)
                """,
                (
                    user_id,
                    race_id,
                    engine_source,
                    feature_source,
                    _now(),
                    json.dumps(meta or {}, ensure_ascii=False),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def list_for_user(self, user_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM prediction_history
                WHERE user_id = ?
                ORDER BY viewed_at DESC LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


class ChatRepository:
    def __init__(self) -> None:
        migrate()

    def ensure_session(
        self,
        *,
        session_id: str,
        user_id: str | None,
        race_id: str | None = None,
        title: str | None = None,
    ) -> None:
        now = _now()
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO chat_sessions(session_id, user_id, title, race_id, created_at, updated_at)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(session_id) DO UPDATE SET
                  user_id=COALESCE(excluded.user_id, chat_sessions.user_id),
                  race_id=COALESCE(excluded.race_id, chat_sessions.race_id),
                  title=COALESCE(excluded.title, chat_sessions.title),
                  updated_at=excluded.updated_at
                """,
                (session_id, user_id, title, race_id, now, now),
            )
            conn.commit()
        finally:
            conn.close()

    def append_message(
        self,
        *,
        session_id: str,
        user_id: str | None,
        role: str,
        content: str,
        intent: str | None = None,
        race_id: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        now = _now()
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO chat_messages(
                  session_id, user_id, role, content, intent, race_id, meta_json, created_at
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    session_id,
                    user_id,
                    role,
                    content,
                    intent,
                    race_id,
                    json.dumps(meta or {}, ensure_ascii=False),
                    now,
                ),
            )
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?",
                (now, session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def list_sessions(self, user_id: str, *, limit: int = 30) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT session_id, title, race_id, created_at, updated_at
                FROM chat_sessions WHERE user_id = ?
                ORDER BY updated_at DESC LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def list_messages(self, session_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT id, session_id, role, content, intent, race_id, created_at
                FROM chat_messages WHERE session_id = ?
                ORDER BY id ASC LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


class NotificationRepository:
    def __init__(self) -> None:
        migrate()

    def create(
        self,
        *,
        user_id: str,
        kind: str,
        title: str,
        body: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        conn = connect()
        try:
            cur = conn.execute(
                """
                INSERT INTO notifications(user_id, kind, title, body, payload_json, created_at)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    user_id,
                    kind,
                    title,
                    body,
                    json.dumps(payload or {}, ensure_ascii=False),
                    _now(),
                ),
            )
            conn.commit()
            nid = cur.lastrowid
        finally:
            conn.close()
        return self.get(int(nid)) or {}

    def get(self, notification_id: int) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT * FROM notifications WHERE id = ?", (notification_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_for_user(self, user_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM notifications WHERE user_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def mark_read(self, user_id: str, notification_id: int) -> None:
        conn = connect()
        try:
            conn.execute(
                """
                UPDATE notifications SET read_at = ?
                WHERE id = ? AND user_id = ?
                """,
                (_now(), notification_id, user_id),
            )
            conn.commit()
        finally:
            conn.close()


class SubscriptionRepository:
    def __init__(self) -> None:
        migrate()

    def get_active(self, user_id: str) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute(
                """
                SELECT * FROM subscriptions
                WHERE user_id = ? AND status = 'active'
                ORDER BY started_at DESC LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def upsert(
        self,
        *,
        user_id: str,
        plan_id: str,
        status: str = "active",
        expires_at: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = _now()
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO subscriptions(user_id, plan_id, status, started_at, expires_at, meta_json)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    user_id,
                    plan_id,
                    status,
                    now,
                    expires_at,
                    json.dumps(meta or {}, ensure_ascii=False),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get_active(user_id) or {}
