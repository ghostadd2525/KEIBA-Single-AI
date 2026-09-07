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


# Stub-mirror sentinel — not a real password; blocks password login.
_STUB_MIRROR_PASSWORD_HASH = "!stub-auth-mirror!"


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

    def ensure_stub_mirror(
        self,
        user_id: str,
        *,
        display_name: str | None = None,
        role: str = "USER",
    ) -> dict[str, Any]:
        """Upsert minimal AI users (+ profile) for BFF stub identities.

        Version8.9.1: prevents user_progress FK failures when stub users
        are authenticated but not yet mirrored into AI SQLite.
        """
        uid = str(user_id or "").strip()
        if not uid:
            return {}
        now = _now()
        name = (display_name or uid).strip() or uid
        role_norm = str(role or "USER").strip() or "USER"
        prefs = json.dumps({"role": role_norm, "stub_mirror": True}, ensure_ascii=False)

        conn = connect()
        try:
            existing = conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (uid,)
            ).fetchone()
            if not existing:
                login_id = uid
                # Avoid UNIQUE(login_id) clash with a different user_id.
                clash = conn.execute(
                    "SELECT user_id FROM users WHERE login_id = ?", (login_id,)
                ).fetchone()
                if clash and str(clash["user_id"]) != uid:
                    login_id = f"stub:{uid}"
                try:
                    conn.execute(
                        """
                        INSERT INTO users(
                          user_id, login_id, password_hash, status, invite_id,
                          terms_version, terms_accepted_at, created_at, updated_at
                        ) VALUES (?,?,?,?,NULL,NULL,NULL,?,?)
                        """,
                        (uid, login_id, _STUB_MIRROR_PASSWORD_HASH, "active", now, now),
                    )
                except Exception:
                    # Concurrent insert or residual UNIQUE — fall through to profile upsert.
                    pass

            # profiles.display_name + preferences.role (no role column on users)
            prof = conn.execute(
                "SELECT user_id FROM profiles WHERE user_id = ?", (uid,)
            ).fetchone()
            if prof:
                conn.execute(
                    """
                    UPDATE profiles SET
                      display_name = COALESCE(?, display_name),
                      preferences_json = ?,
                      updated_at = ?
                    WHERE user_id = ?
                    """,
                    (name, prefs, now, uid),
                )
            else:
                # Only insert profile if parent user row exists (FK).
                parent = conn.execute(
                    "SELECT user_id FROM users WHERE user_id = ?", (uid,)
                ).fetchone()
                if parent:
                    conn.execute(
                        """
                        INSERT INTO profiles(
                          user_id, display_name, avatar_url, locale, preferences_json, updated_at
                        ) VALUES (?,?,?,?,?,?)
                        """,
                        (uid, name, "", "ja", prefs, now),
                    )
            conn.commit()
        finally:
            conn.close()
        return self.get_by_id(uid) or {"user_id": uid, "created_at": now}
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

class UserRaceResultRepository:
    """Personal race P&L ledger (independent from Prediction Engine)."""

    def __init__(self) -> None:
        migrate()

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        item = dict(row)
        for key, out_key in (
            ("strategy_snapshot_json", "strategy_snapshot"),
            ("finish_order_json", "finish_order"),
            ("payouts_json", "payouts"),
            ("bet_results_json", "bet_results"),
            ("marks_result_json", "marks_result"),
            ("official_result_json", "official_result"),
        ):
            raw = item.pop(key, None)
            if raw:
                try:
                    item[out_key] = json.loads(raw)
                except json.JSONDecodeError:
                    item[out_key] = {}
            else:
                item[out_key] = {} if out_key != "finish_order" else []
        item["hit"] = bool(item.get("hit"))
        item["settled"] = bool(item.get("settled"))
        item["purchase_registered"] = bool(item.get("purchase_registered"))
        if item.get("selected_bet_types_json"):
            try:
                item["selected_bet_types"] = json.loads(item.pop("selected_bet_types_json"))
            except json.JSONDecodeError:
                item["selected_bet_types"] = []
                item.pop("selected_bet_types_json", None)
        else:
            item.pop("selected_bet_types_json", None)
            item["selected_bet_types"] = []
        if item.get("client_meta_json"):
            try:
                item["client_meta"] = json.loads(item.pop("client_meta_json"))
            except json.JSONDecodeError:
                item["client_meta"] = {}
                item.pop("client_meta_json", None)
        else:
            item.pop("client_meta_json", None)
            item["client_meta"] = {}
        return item

    def get(self, user_id: str, race_id: str) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT * FROM user_race_results WHERE user_id=? AND race_id=?",
                (user_id, race_id),
            ).fetchone()
            return self._row_to_dict(row) if row else None
        finally:
            conn.close()

    def list_for_month(self, user_id: str, month: str) -> list[dict[str, Any]]:
        """month: YYYY-MM"""
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM user_race_results
                WHERE user_id=? AND race_date IS NOT NULL AND substr(race_date, 1, 7)=?
                ORDER BY race_date DESC, race_id DESC
                """,
                (user_id, month),
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def list_purchased(self, user_id: str, *, limit: int = 500) -> list[dict[str, Any]]:
        """All purchase-registered races (newest first)."""
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM user_race_results
                WHERE user_id=? AND purchase_registered=1
                  AND race_date IS NOT NULL
                ORDER BY race_date DESC, race_id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def list_unsettled(self, user_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM user_race_results
                WHERE user_id=? AND settled=0
                ORDER BY race_date DESC, id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def list_unsettled_for_date(
        self, race_date: str, *, limit: int = 2000
    ) -> list[dict[str, Any]]:
        """Purchase-registered unsettled rows for a race_date (all users)."""
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM user_race_results
                WHERE race_date=? AND purchase_registered=1 AND settled=0
                ORDER BY user_id ASC, race_id ASC
                LIMIT ?
                """,
                (race_date, limit),
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def list_purchased_for_date(
        self, race_date: str, *, limit: int = 2000
    ) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM user_race_results
                WHERE race_date=? AND purchase_registered=1
                ORDER BY user_id ASC, race_id ASC
                LIMIT ?
                """,
                (race_date, limit),
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]
        finally:
            conn.close()

    def upsert_snapshot(
        self,
        user_id: str,
        *,
        race_id: str,
        race_date: str | None,
        race_label: str | None,
        prediction_version: str | None,
        strategy_snapshot: dict[str, Any],
        purchase_amount: int,
        purchase_registered: int = 0,
        unit_stake: int | None = None,
        selected_bet_types: list[str] | None = None,
        client_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = _now()
        conn = connect()
        try:
            existing = conn.execute(
                "SELECT settled FROM user_race_results WHERE user_id=? AND race_id=?",
                (user_id, race_id),
            ).fetchone()
            # Once settled, keep snapshot frozen (do not overwrite strategy).
            if existing and int(existing["settled"] or 0) == 1:
                row = conn.execute(
                    "SELECT * FROM user_race_results WHERE user_id=? AND race_id=?",
                    (user_id, race_id),
                ).fetchone()
                return self._row_to_dict(row)

            conn.execute(
                """
                INSERT INTO user_race_results(
                  user_id, race_id, race_date, race_label, prediction_version,
                  strategy_snapshot_json, purchase_amount, payout_amount, profit, hit,
                  settled, purchase_registered, unit_stake, selected_bet_types_json,
                  client_meta_json, registered_at, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,0,0,0,0,?,?,?,?,?,?,?)
                ON CONFLICT(user_id, race_id) DO UPDATE SET
                  race_date=COALESCE(excluded.race_date, user_race_results.race_date),
                  race_label=COALESCE(excluded.race_label, user_race_results.race_label),
                  prediction_version=COALESCE(excluded.prediction_version, user_race_results.prediction_version),
                  strategy_snapshot_json=excluded.strategy_snapshot_json,
                  purchase_amount=excluded.purchase_amount,
                  purchase_registered=excluded.purchase_registered,
                  unit_stake=excluded.unit_stake,
                  selected_bet_types_json=excluded.selected_bet_types_json,
                  client_meta_json=excluded.client_meta_json,
                  registered_at=CASE
                    WHEN excluded.purchase_registered=1 THEN excluded.registered_at
                    ELSE user_race_results.registered_at END,
                  updated_at=excluded.updated_at
                WHERE user_race_results.settled=0
                """,
                (
                    user_id,
                    race_id,
                    race_date,
                    race_label,
                    prediction_version,
                    json.dumps(strategy_snapshot or {}, ensure_ascii=False),
                    int(purchase_amount or 0),
                    int(purchase_registered or 0),
                    unit_stake,
                    json.dumps(selected_bet_types or [], ensure_ascii=False),
                    json.dumps(client_meta or {}, ensure_ascii=False),
                    now if purchase_registered else None,
                    now,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM user_race_results WHERE user_id=? AND race_id=?",
                (user_id, race_id),
            ).fetchone()
            return self._row_to_dict(row)
        finally:
            conn.close()

    def mark_points_awarded(self, user_id: str, race_id: str, points: int) -> None:
        conn = connect()
        try:
            conn.execute(
                """
                UPDATE user_race_results
                SET points_awarded=?, updated_at=?
                WHERE user_id=? AND race_id=?
                """,
                (int(points or 0), _now(), user_id, race_id),
            )
            conn.commit()
        finally:
            conn.close()

    def apply_settlement(
        self,
        user_id: str,
        race_id: str,
        *,
        purchase_amount: int,
        payout_amount: int,
        profit: int,
        hit: int,
        settled: int,
        finish_order: list[Any] | None,
        payouts: dict[str, Any] | None,
        bet_results: dict[str, Any] | None,
        marks_result: dict[str, Any] | None,
        official_result: dict[str, Any] | None,
        race_date: str | None = None,
        race_label: str | None = None,
    ) -> dict[str, Any]:
        now = _now()
        conn = connect()
        try:
            conn.execute(
                """
                UPDATE user_race_results SET
                  purchase_amount=?,
                  payout_amount=?,
                  profit=?,
                  hit=?,
                  settled=?,
                  finish_order_json=?,
                  payouts_json=?,
                  bet_results_json=?,
                  marks_result_json=?,
                  official_result_json=?,
                  race_date=COALESCE(?, race_date),
                  race_label=COALESCE(?, race_label),
                  updated_at=?,
                  settled_at=CASE WHEN ?=1 THEN ? ELSE settled_at END
                WHERE user_id=? AND race_id=?
                """,
                (
                    int(purchase_amount or 0),
                    int(payout_amount or 0),
                    int(profit or 0),
                    int(hit or 0),
                    int(settled or 0),
                    json.dumps(finish_order or [], ensure_ascii=False),
                    json.dumps(payouts or {}, ensure_ascii=False),
                    json.dumps(bet_results or {}, ensure_ascii=False),
                    json.dumps(marks_result or {}, ensure_ascii=False),
                    json.dumps(official_result or {}, ensure_ascii=False),
                    race_date,
                    race_label,
                    now,
                    int(settled or 0),
                    now,
                    user_id,
                    race_id,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM user_race_results WHERE user_id=? AND race_id=?",
                (user_id, race_id),
            ).fetchone()
            return self._row_to_dict(row) if row else {}
        finally:
            conn.close()

class UserProgressRepository:
    def __init__(self) -> None:
        migrate()

    def get(self, user_id: str) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT * FROM user_progress WHERE user_id=?",
                (user_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def ensure(self, user_id: str) -> dict[str, Any]:
        """Ensure progress row; never raise IntegrityError to callers (V8.9.1)."""
        uid = str(user_id or "").strip()
        now = _now()
        default = {
            "user_id": uid or "unknown",
            "cumulative_points": 0,
            "cumulative_profit": 0,
            "level": 1,
            "updated_at": now,
        }
        if not uid:
            return default

        existing = self.get(uid)
        if existing:
            return existing

        # Parent user must exist for FK(user_progress → users).
        try:
            UserRepository().ensure_stub_mirror(uid)
        except Exception:
            pass

        conn = connect()
        try:
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO user_progress(
                      user_id, cumulative_points, cumulative_profit, level, updated_at
                    ) VALUES (?,?,?,?,?)
                    """,
                    (uid, 0, 0, 1, now),
                )
                conn.commit()
            except Exception:
                # FK / concurrent / schema — return safe default, do not propagate.
                try:
                    conn.rollback()
                except Exception:
                    pass
                return default
        finally:
            conn.close()

        return self.get(uid) or default

    def add_profit_and_points(
        self, user_id: str, *, profit_delta: int, points_delta: int
    ) -> dict[str, Any]:
        from .progress import level_from_points

        self.ensure(user_id)
        now = _now()
        conn = connect()
        try:
            conn.execute(
                """
                UPDATE user_progress SET
                  cumulative_profit = cumulative_profit + ?,
                  cumulative_points = cumulative_points + ?,
                  updated_at = ?
                WHERE user_id = ?
                """,
                (int(profit_delta or 0), int(points_delta or 0), now, user_id),
            )
            row = conn.execute(
                "SELECT * FROM user_progress WHERE user_id=?",
                (user_id,),
            ).fetchone()
            if row:
                pts = int(row["cumulative_points"] or 0)
                lv = level_from_points(pts)
                conn.execute(
                    "UPDATE user_progress SET level=? WHERE user_id=?",
                    (lv, user_id),
                )
            conn.commit()
        finally:
            conn.close()
        return self.get(user_id) or {}


class PurchaseAuditRepository:
    def __init__(self) -> None:
        migrate()

    def append(self, row: dict[str, Any]) -> None:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO user_purchase_audit(
                  user_id, race_id, event_type, purchase_amount, payout_amount,
                  profit, points_awarded, ai_strategy_json, user_bets_json,
                  ip_address, user_agent, meta_json, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    row.get("user_id"),
                    row.get("race_id"),
                    row.get("event_type") or "purchase",
                    row.get("purchase_amount"),
                    row.get("payout_amount"),
                    row.get("profit"),
                    int(row.get("points_awarded") or 0),
                    json.dumps(row.get("ai_strategy") or {}, ensure_ascii=False),
                    json.dumps(row.get("user_bets") or {}, ensure_ascii=False),
                    row.get("ip_address"),
                    row.get("user_agent"),
                    json.dumps(row.get("meta") or {}, ensure_ascii=False),
                    _now(),
                ),
            )
            conn.commit()
        finally:
            conn.close()


class AppSettingsRepository:
    def __init__(self) -> None:
        migrate()

    def get(self, key: str, default: Any = None) -> Any:
        conn = connect()
        try:
            row = conn.execute(
                "SELECT value_json FROM app_settings WHERE key=?",
                (key,),
            ).fetchone()
            if not row:
                return default
            raw = row["value_json"]
            try:
                return json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                return raw
        finally:
            conn.close()

    def set(self, key: str, value: Any) -> None:
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO app_settings(key, value_json, updated_at)
                VALUES (?,?,?)
                ON CONFLICT(key) DO UPDATE SET
                  value_json=excluded.value_json,
                  updated_at=excluded.updated_at
                """,
                (key, json.dumps(value, ensure_ascii=False), _now()),
            )
            conn.commit()
        finally:
            conn.close()
