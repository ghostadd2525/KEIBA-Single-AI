# -*- coding: utf-8 -*-
"""
OPS-Hardening — orphan ACTIVE recovery + result_automation health snapshot.

Prediction Core は触らない。run 行の安全な FAILED 化と監視用ステータスのみ。
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ..data import db as app_db
from . import state_machine as sm
from .result_automation import improvement_root

DEFAULT_STALE_MINUTES = 60
LOOKBACK_DAYS = 2


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(raw: str | None) -> datetime | None:
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def stale_minutes() -> int:
    raw = (os.environ.get("EXPECT_RA_ACTIVE_STALE_MINUTES") or "").strip()
    if not raw:
        return DEFAULT_STALE_MINUTES
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_STALE_MINUTES


def fail_orphan_active_runs(
    *,
    reason: str = "orphan_active_on_startup",
    older_than_seconds: int = 0,
) -> list[dict[str, Any]]:
    """
    ACTIVE のまま残った run を安全に FAILED へ遷移する。

    older_than_seconds=0: 起動時はすべて orphan 扱い（runner 再入場時）。
    Monitor 用に経過時間フィルタしたい場合は正の秒数を渡す。
    """
    app_db.migrate()
    conn = app_db.connect()
    failed: list[dict[str, Any]] = []
    cutoff = _now_utc() - timedelta(seconds=max(0, older_than_seconds))
    try:
        rows = conn.execute(
            f"""
            SELECT id, race_date, status, trigger, parent_run_id, attempt, started_at
            FROM result_automation_runs
            WHERE status IN ({",".join("?" * len(sm.ACTIVE))})
            ORDER BY id ASC
            """,
            tuple(sm.ACTIVE),
        ).fetchall()
        for row in rows:
            started = _parse_iso(row["started_at"])
            if older_than_seconds > 0 and started and started > cutoff:
                continue
            run_id = int(row["id"])
            current = str(row["status"])
            if not sm.can_transition(current, sm.FAILED):
                continue
            err = {
                "reason": reason,
                "previous_status": current,
                "recovered_at": _now_utc().isoformat(),
                "message": "ACTIVE run marked FAILED for safe retry (parent_run_id preserved)",
            }
            conn.execute(
                """
                UPDATE result_automation_runs
                SET status=?, error_json=?, finished_at=?
                WHERE id=? AND status=?
                """,
                (sm.FAILED, json.dumps(err, ensure_ascii=False), _now_utc().isoformat(), run_id, current),
            )
            failed.append(
                {
                    "run_id": run_id,
                    "race_date": row["race_date"],
                    "previous_status": current,
                    "parent_run_id": row["parent_run_id"],
                    "trigger": row["trigger"],
                    "attempt": row["attempt"],
                }
            )
        conn.commit()
    finally:
        conn.close()
    return failed


def _latest_runs_by_date(conn: Any, since_date: str) -> list[Any]:
    return conn.execute(
        """
        SELECT r.*
        FROM result_automation_runs r
        INNER JOIN (
          SELECT race_date, MAX(id) AS max_id
          FROM result_automation_runs
          WHERE race_date >= ?
          GROUP BY race_date
        ) t ON r.id = t.max_id
        ORDER BY r.race_date DESC
        """,
        (since_date,),
    ).fetchall()


def _manifest_paths(race_date: str) -> dict[str, Path]:
    base = improvement_root() / "manifest" / race_date
    return {
        "run": base / "run.json",
        "summary": base / "summary.json",
        "index": base / "index.json",
    }


def collect_result_automation_health() -> dict[str, Any]:
    """
    Monitor / Health 用スナップショット。

    監視:
    - ACTIVE が stale_minutes 以上継続
    - 最新 run が FAILED
    - 最新 run が DEGRADED
    - 最新成功日の manifest / summary 未生成
    """
    app_db.migrate()
    threshold = stale_minutes()
    since = (_now_utc() - timedelta(days=LOOKBACK_DAYS)).date().isoformat()
    issues: list[str] = []
    detail: dict[str, Any] = {
        "stale_minutes": threshold,
        "lookback_days": LOOKBACK_DAYS,
        "stale_active": [],
        "failed_latest": [],
        "degraded_latest": [],
        "manifest_missing": [],
        "summary_missing": [],
    }

    conn = app_db.connect()
    try:
        active_rows = conn.execute(
            f"""
            SELECT id, race_date, status, started_at, parent_run_id
            FROM result_automation_runs
            WHERE status IN ({",".join("?" * len(sm.ACTIVE))})
            ORDER BY id DESC
            """,
            tuple(sm.ACTIVE),
        ).fetchall()
        now = _now_utc()
        for row in active_rows:
            started = _parse_iso(row["started_at"]) or now
            age_min = (now - started).total_seconds() / 60.0
            if age_min >= threshold:
                item = {
                    "run_id": int(row["id"]),
                    "race_date": row["race_date"],
                    "status": row["status"],
                    "age_minutes": round(age_min, 1),
                    "parent_run_id": row["parent_run_id"],
                }
                detail["stale_active"].append(item)
                issues.append(
                    f"stale_active run_id={item['run_id']} age_min={item['age_minutes']}"
                )

        for row in _latest_runs_by_date(conn, since):
            status = str(row["status"])
            race_date = str(row["race_date"])
            entry = {
                "run_id": int(row["id"]),
                "race_date": race_date,
                "status": status,
                "parent_run_id": row["parent_run_id"],
            }
            if status == sm.FAILED:
                detail["failed_latest"].append(entry)
                issues.append(f"failed_latest race_date={race_date} run_id={entry['run_id']}")
            elif status == sm.DEGRADED:
                detail["degraded_latest"].append(entry)
                issues.append(f"degraded_latest race_date={race_date} run_id={entry['run_id']}")

            if status in (sm.COMPLETED, sm.DEGRADED):
                paths = _manifest_paths(race_date)
                if not paths["run"].is_file():
                    detail["manifest_missing"].append(
                        {"race_date": race_date, "path": str(paths["run"]), "kind": "run.json"}
                    )
                    issues.append(f"manifest_missing race_date={race_date}")
                if not paths["summary"].is_file():
                    detail["summary_missing"].append(
                        {"race_date": race_date, "path": str(paths["summary"])}
                    )
                    issues.append(f"summary_missing race_date={race_date}")
    finally:
        conn.close()

    has_failed = bool(detail["failed_latest"]) or bool(detail["stale_active"])
    has_degraded = bool(detail["degraded_latest"])
    has_manifest_gap = bool(detail["manifest_missing"]) or bool(detail["summary_missing"])

    if has_failed or has_manifest_gap:
        status = "unhealthy"
        ok = False
    elif has_degraded:
        status = "degraded"
        ok = False
    else:
        status = "ok"
        ok = True

    return {
        "ok": ok,
        "status": status,
        "service": "result_automation",
        "issues": issues,
        "detail": detail,
        "checked_at": _now_utc().isoformat(),
    }
