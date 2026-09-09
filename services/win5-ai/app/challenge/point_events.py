# -*- coding: utf-8 -*-
"""Challenge V7.5 — authoritative point processing at lifecycle CONSUMED."""
from __future__ import annotations

from typing import Any

from ..data.db import connect, migrate
from ..user.progress import (
    CHALLENGE_POINT_AWARD,
    CHALLENGE_POINT_THRESHOLD_YEN,
    challenge_points_from_settled_profit,
    level_from_points,
    progress_payload,
)
from ..user.repository import UserProgressRepository, UserRaceResultRepository, _now
from .lifecycle import STATUS_CONSUMED, ChallengeLifecycleRepository

EVENT_TYPE_CONSUMED = "CHALLENGE_RESULT_CONSUMED"
POINT_RULE_VERSION = "challenge-point-v7.5"


class ChallengePointEventRepository:
    def __init__(self) -> None:
        migrate()

    def get_event(
        self, user_id: str, race_id: str, event_type: str = EVENT_TYPE_CONSUMED
    ) -> dict[str, Any] | None:
        conn = connect()
        try:
            row = conn.execute(
                """
                SELECT * FROM user_challenge_point_events
                WHERE user_id=? AND race_id=? AND event_type=?
                """,
                (user_id, race_id, event_type),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def insert_event_and_apply_points(
        self,
        user_id: str,
        race_id: str,
        *,
        event_type: str = EVENT_TYPE_CONSUMED,
        points_awarded: int,
    ) -> dict[str, Any]:
        """Atomic: INSERT OR IGNORE event + increment cumulative_points only on new insert."""
        uid = str(user_id or "").strip()
        rid = str(race_id or "").strip()
        pts = int(points_awarded or 0)
        if not uid or not rid:
            raise ValueError("user_id and race_id required")

        UserProgressRepository().ensure(uid)
        now = _now()
        conn = connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO user_challenge_point_events(
                  user_id, race_id, event_type, points_awarded, created_at
                ) VALUES (?,?,?,?,?)
                """,
                (uid, rid, event_type, pts, now),
            )
            inserted = int(cur.rowcount or 0) > 0
            if inserted and pts > 0:
                conn.execute(
                    """
                    UPDATE user_progress SET
                      cumulative_points = cumulative_points + ?,
                      updated_at = ?
                    WHERE user_id = ?
                    """,
                    (pts, now, uid),
                )
                row = conn.execute(
                    "SELECT cumulative_points FROM user_progress WHERE user_id=?",
                    (uid,),
                ).fetchone()
                if row:
                    lv = level_from_points(int(row["cumulative_points"] or 0))
                    conn.execute(
                        "UPDATE user_progress SET level=? WHERE user_id=?",
                        (lv, uid),
                    )
            elif inserted:
                conn.execute(
                    "UPDATE user_progress SET updated_at=? WHERE user_id=?",
                    (now, uid),
                )
            conn.commit()
            event = conn.execute(
                """
                SELECT * FROM user_challenge_point_events
                WHERE user_id=? AND race_id=? AND event_type=?
                """,
                (uid, rid, event_type),
            ).fetchone()
            return {
                "inserted": inserted,
                "points_awarded": pts if inserted else 0,
                "event": dict(event) if event else None,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def process_challenge_consumed_points(user_id: str, race_id: str) -> dict[str, Any]:
    """Single authoritative Challenge point processor (viewed + auto-consume paths)."""
    if str(race_id).startswith("ui-test-race-"):
        return {"ok": False, "skipped": True, "reason": "ui_test_isolated"}

    life_repo = ChallengeLifecycleRepository()
    lifecycle = life_repo.get(user_id, race_id)
    if not lifecycle:
        return {"ok": False, "reason": "no_challenge_lifecycle"}
    if lifecycle.get("status") != STATUS_CONSUMED:
        return {
            "ok": False,
            "reason": "not_consumed",
            "lifecycle_status": lifecycle.get("status"),
        }

    race_row = UserRaceResultRepository().get(user_id, race_id)
    if not race_row or not race_row.get("settled"):
        return {"ok": False, "reason": "race_not_settled"}

    profit = int(race_row.get("profit") or 0)
    points = challenge_points_from_settled_profit(profit)
    repo = ChallengePointEventRepository()
    applied = repo.insert_event_and_apply_points(
        user_id,
        race_id,
        event_type=EVENT_TYPE_CONSUMED,
        points_awarded=points,
    )
    progress = progress_payload(UserProgressRepository().ensure(user_id))
    return {
        "ok": True,
        "schema_version": POINT_RULE_VERSION,
        "event_type": EVENT_TYPE_CONSUMED,
        "profit_yen": profit,
        "threshold_yen": CHALLENGE_POINT_THRESHOLD_YEN,
        "max_award": CHALLENGE_POINT_AWARD,
        "points_calculated": points,
        "points_applied": int(applied.get("points_awarded") or 0),
        "event_inserted": bool(applied.get("inserted")),
        "event": applied.get("event"),
        "progress": progress,
    }
