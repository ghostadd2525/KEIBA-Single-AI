# -*- coding: utf-8 -*-
"""Challenge Result Lifecycle V6 — UX state machine (NOT financial settlement).

States: ACTIVE → READY → CONSUMED
Financial authority remains user_race_results + settle_race_result.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from ..data.db import connect, migrate
from ..user.repository import NotificationRepository, UserRaceResultRepository, _now

STATUS_ACTIVE = "ACTIVE"
STATUS_READY = "READY"
STATUS_CONSUMED = "CONSUMED"

NOTIF_KIND = "CHALLENGE_RESULT_READY"
AUTO_CONSUME_MINUTES = 5
SCHEMA = "expect-challenge-lifecycle/1.0"


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    raw = str(ts).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class ChallengeLifecycleRepository:
    def __init__(self) -> None:
        migrate()

    def get(self, user_id: str, race_id: str) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute(
                """
                SELECT * FROM user_challenge_lifecycle
                WHERE user_id=? AND race_id=?
                """,
                (user_id, race_id),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def ensure_active(self, user_id: str, race_id: str) -> dict[str, Any]:
        """Idempotent ACTIVE row for (user_id, race_id). Does not downgrade READY/CONSUMED."""
        now = _now()
        conn = connect()
        try:
            conn.execute(
                """
                INSERT INTO user_challenge_lifecycle(
                  user_id, race_id, status, created_at, updated_at
                ) VALUES (?,?,?,?,?)
                ON CONFLICT(user_id, race_id) DO NOTHING
                """,
                (user_id, race_id, STATUS_ACTIVE, now, now),
            )
            conn.commit()
            row = conn.execute(
                """
                SELECT * FROM user_challenge_lifecycle
                WHERE user_id=? AND race_id=?
                """,
                (user_id, race_id),
            ).fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()

    def promote_ready(self, user_id: str, race_id: str) -> dict[str, Any]:
        """ACTIVE → READY exactly once. Returns row + transitioned flag."""
        now = _now()
        self.ensure_active(user_id, race_id)
        conn = connect()
        try:
            cur = conn.execute(
                """
                UPDATE user_challenge_lifecycle
                SET status=?,
                    result_ready_at=COALESCE(result_ready_at, ?),
                    updated_at=?
                WHERE user_id=? AND race_id=? AND status=?
                """,
                (STATUS_READY, now, now, user_id, race_id, STATUS_ACTIVE),
            )
            transitioned = cur.rowcount > 0
            conn.commit()
            row = conn.execute(
                """
                SELECT * FROM user_challenge_lifecycle
                WHERE user_id=? AND race_id=?
                """,
                (user_id, race_id),
            ).fetchone()
            out = dict(row) if row else {}
            out["_transitioned_to_ready"] = transitioned
            return out
        finally:
            conn.close()

    def consume_viewed(self, user_id: str, race_id: str) -> dict[str, Any]:
        """READY → CONSUMED via reveal. Exactly-once with conditional UPDATE."""
        now = _now()
        conn = connect()
        try:
            cur = conn.execute(
                """
                UPDATE user_challenge_lifecycle
                SET status=?,
                    result_viewed_at=COALESCE(result_viewed_at, ?),
                    consumed_at=COALESCE(consumed_at, ?),
                    consume_reason=COALESCE(consume_reason, 'VIEWED'),
                    updated_at=?
                WHERE user_id=? AND race_id=? AND status=?
                """,
                (STATUS_CONSUMED, now, now, now, user_id, race_id, STATUS_READY),
            )
            transitioned = cur.rowcount > 0
            conn.commit()
            row = conn.execute(
                """
                SELECT * FROM user_challenge_lifecycle
                WHERE user_id=? AND race_id=?
                """,
                (user_id, race_id),
            ).fetchone()
            out = dict(row) if row else {}
            out["_transitioned_to_consumed"] = transitioned
            out["_already_consumed"] = (
                not transitioned and out.get("status") == STATUS_CONSUMED
            )
            return out
        finally:
            conn.close()

    def attach_notification_id(
        self, user_id: str, race_id: str, notification_id: int
    ) -> None:
        conn = connect()
        try:
            conn.execute(
                """
                UPDATE user_challenge_lifecycle
                SET notification_id=COALESCE(notification_id, ?), updated_at=?
                WHERE user_id=? AND race_id=?
                """,
                (int(notification_id), _now(), user_id, race_id),
            )
            conn.commit()
        finally:
            conn.close()

    def list_active_for_user(self, user_id: str) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM user_challenge_lifecycle
                WHERE user_id=? AND status IN (?, ?)
                ORDER BY COALESCE(result_ready_at, created_at) DESC, race_id ASC
                """,
                (user_id, STATUS_ACTIVE, STATUS_READY),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def list_due_auto_consume(
        self, *, before_iso: str, limit: int = 2000
    ) -> list[dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM user_challenge_lifecycle
                WHERE status=?
                  AND result_ready_at IS NOT NULL
                  AND result_ready_at <= ?
                ORDER BY result_ready_at ASC
                LIMIT ?
                """,
                (STATUS_READY, before_iso, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def consume_auto(self, user_id: str, race_id: str) -> dict[str, Any]:
        """READY → CONSUMED via +5min. Does not set result_viewed_at."""
        now = _now()
        conn = connect()
        try:
            cur = conn.execute(
                """
                UPDATE user_challenge_lifecycle
                SET status=?,
                    consumed_at=COALESCE(consumed_at, ?),
                    consume_reason=COALESCE(consume_reason, 'AUTO_5MIN'),
                    updated_at=?
                WHERE user_id=? AND race_id=? AND status=?
                """,
                (STATUS_CONSUMED, now, now, user_id, race_id, STATUS_READY),
            )
            transitioned = cur.rowcount > 0
            conn.commit()
            row = conn.execute(
                """
                SELECT * FROM user_challenge_lifecycle
                WHERE user_id=? AND race_id=?
                """,
                (user_id, race_id),
            ).fetchone()
            out = dict(row) if row else {}
            out["_transitioned_to_consumed"] = transitioned
            out["_already_consumed"] = (
                not transitioned and out.get("status") == STATUS_CONSUMED
            )
            return out
        finally:
            conn.close()

    def statuses_for_user_races(
        self, user_id: str, race_ids: list[str]
    ) -> dict[str, str]:
        if not race_ids:
            return {}
        conn = connect()
        try:
            placeholders = ",".join("?" for _ in race_ids)
            rows = conn.execute(
                f"""
                SELECT race_id, status FROM user_challenge_lifecycle
                WHERE user_id=? AND race_id IN ({placeholders})
                """,
                (user_id, *race_ids),
            ).fetchall()
            return {str(r["race_id"]): str(r["status"]) for r in rows}
        finally:
            conn.close()

    def find_ready_notification(
        self, user_id: str, race_id: str
    ) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute(
                """
                SELECT * FROM notifications
                WHERE user_id=? AND kind=?
                  AND json_extract(payload_json, '$.race_id') = ?
                LIMIT 1
                """,
                (user_id, NOTIF_KIND, race_id),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


class ChallengeLifecycleService:
    def __init__(self) -> None:
        self.repo = ChallengeLifecycleRepository()
        self.race_results = UserRaceResultRepository()
        self.notifications = NotificationRepository()

    def ensure_active_for_purchase(self, user_id: str, race_id: str) -> dict[str, Any]:
        if str(race_id).startswith("ui-test-race-"):
            return {"skipped": True, "reason": "ui_test_isolated"}
        return self.repo.ensure_active(user_id, race_id)

    def on_settled(self, user_id: str, race_id: str) -> dict[str, Any]:
        """Promote READY after financial settlement. Lifecycle failure must not raise to caller."""
        if str(race_id).startswith("ui-test-race-"):
            return {"skipped": True, "reason": "ui_test_isolated"}
        try:
            row = self.race_results.get(user_id, race_id)
            if not row or not row.get("purchase_registered") or not row.get("settled"):
                return {
                    "ok": False,
                    "reason": "not_settled",
                    "lifecycle": self.repo.get(user_id, race_id),
                }
            promoted = self.repo.promote_ready(user_id, race_id)
            notif = None
            notif_error = None
            if promoted.get("status") == STATUS_READY:
                try:
                    notif = self._ensure_notification(user_id, race_id)
                    if notif and notif.get("id") is not None:
                        self.repo.attach_notification_id(
                            user_id, race_id, int(notif["id"])
                        )
                        promoted = self.repo.get(user_id, race_id) or promoted
                except Exception as exc:  # noqa: BLE001 — isolate notif failure
                    notif_error = str(exc)
            return {
                "ok": True,
                "lifecycle": {
                    k: v for k, v in promoted.items() if not str(k).startswith("_")
                },
                "transitioned_to_ready": bool(promoted.get("_transitioned_to_ready")),
                "notification": notif,
                "notification_error": notif_error,
            }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def _ensure_notification(self, user_id: str, race_id: str) -> dict[str, Any]:
        existing = self.repo.find_ready_notification(user_id, race_id)
        if existing:
            return existing
        try:
            return self.notifications.create(
                user_id=user_id,
                kind=NOTIF_KIND,
                title="Challenge結果が確定しました",
                body=f"race_id={race_id}",
                payload={
                    "race_id": race_id,
                    "type": NOTIF_KIND,
                    "href": f"/saved?race_id={race_id}&from=challenge-result",
                },
            )
        except Exception:
            # Unique race: concurrent create
            existing = self.repo.find_ready_notification(user_id, race_id)
            if existing:
                return existing
            raise

    def _apply_consumed_points(self, user_id: str, race_id: str) -> dict[str, Any]:
        from .point_events import process_challenge_consumed_points

        try:
            return process_challenge_consumed_points(user_id, race_id)
        except Exception as exc:  # noqa: BLE001 — isolate point failure from lifecycle
            return {"ok": False, "error": str(exc)}

    def mark_viewed(
        self, user_id: str, race_id: str, *, reveal_completed: bool = True
    ) -> dict[str, Any]:
        if not reveal_completed:
            raise ValueError("reveal_completed must be true")
        if str(race_id).startswith("ui-test-race-"):
            raise ValueError("ui-test race cannot use production lifecycle")

        row = self.repo.get(user_id, race_id)
        if not row:
            raise LookupError("lifecycle not found")
        status = row.get("status")
        if status == STATUS_ACTIVE:
            raise ValueError("cannot mark viewed while ACTIVE (not READY)")
        if status == STATUS_CONSUMED:
            points = self._apply_consumed_points(user_id, race_id)
            return {
                "schema_version": SCHEMA,
                "lifecycle": row,
                "already_consumed": True,
                "transitioned": False,
                "points": points,
            }
        out = self.repo.consume_viewed(user_id, race_id)
        clean = {k: v for k, v in out.items() if not str(k).startswith("_")}
        points = self._apply_consumed_points(user_id, race_id)
        return {
            "schema_version": SCHEMA,
            "lifecycle": clean,
            "already_consumed": bool(out.get("_already_consumed")),
            "transitioned": bool(out.get("_transitioned_to_consumed")),
            "points": points,
        }

    def list_active(self, user_id: str) -> dict[str, Any]:
        items = self.repo.list_active_for_user(user_id)
        return {
            "schema_version": SCHEMA,
            "user_id": user_id,
            "items": items,
            "count": len(items),
        }

    def sweep_auto_consume(self, *, now: datetime | None = None) -> dict[str, Any]:
        now_dt = now or datetime.now(timezone.utc)
        threshold = (now_dt - timedelta(minutes=AUTO_CONSUME_MINUTES)).isoformat()
        due = self.repo.list_due_auto_consume(before_iso=threshold)
        consumed = 0
        already = 0
        errors: list[dict[str, str]] = []
        for row in due:
            uid = str(row.get("user_id") or "")
            rid = str(row.get("race_id") or "")
            if not uid or not rid:
                continue
            try:
                out = self.repo.consume_auto(uid, rid)
                if out.get("_transitioned_to_consumed"):
                    consumed += 1
                elif out.get("_already_consumed"):
                    already += 1
                if out.get("status") == STATUS_CONSUMED or out.get("_already_consumed"):
                    self._apply_consumed_points(uid, rid)
            except Exception as exc:  # noqa: BLE001
                errors.append({"user_id": uid, "race_id": rid, "error": str(exc)})
        return {
            "schema_version": SCHEMA,
            "threshold": threshold,
            "due": len(due),
            "consumed": consumed,
            "already_consumed": already,
            "errors": errors,
        }

    def list_notifications(self, user_id: str, *, limit: int = 50) -> dict[str, Any]:
        rows = self.notifications.list_for_user(user_id, limit=limit)
        # Prefer Challenge kinds first in payload but return all for future bell
        return {
            "schema_version": SCHEMA,
            "user_id": user_id,
            "items": rows,
            "count": len(rows),
        }

    def mark_notification_read(
        self, user_id: str, notification_id: int
    ) -> dict[str, Any]:
        row = self.notifications.get(int(notification_id))
        if not row or str(row.get("user_id")) != str(user_id):
            raise LookupError("notification not found")
        self.notifications.mark_read(user_id, int(notification_id))
        return {
            "schema_version": SCHEMA,
            "item": self.notifications.get(int(notification_id)),
        }

    def is_race_visible_in_challenge_aggregates(
        self, user_id: str, race_id: str, status_map: dict[str, str] | None = None
    ) -> bool:
        """Legacy (no lifecycle row) remains visible; ACTIVE/READY hidden; CONSUMED visible."""
        if status_map is not None:
            st = status_map.get(race_id)
        else:
            row = self.repo.get(user_id, race_id)
            st = row.get("status") if row else None
        if st is None:
            return True  # pre-V6 legacy
        return st == STATUS_CONSUMED


_lifecycle_service: ChallengeLifecycleService | None = None


def get_lifecycle_service() -> ChallengeLifecycleService:
    global _lifecycle_service
    if _lifecycle_service is None:
        _lifecycle_service = ChallengeLifecycleService()
    return _lifecycle_service


def reset_lifecycle_service_for_tests() -> None:
    global _lifecycle_service
    _lifecycle_service = None
