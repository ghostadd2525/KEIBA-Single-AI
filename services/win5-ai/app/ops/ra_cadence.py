# -*- coding: utf-8 -*-
"""
Version7.1 ResultAutomation cadence helpers.

Prediction Engine / Candidate Evaluation / AI ロジックは変更しない。
開催中は短間隔、終了後は長間隔 or skip。未確定レースがある日だけ本処理。
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ..data import db as app_db
from . import state_machine as sm
from .result_automation import archive_root

JST = ZoneInfo("Asia/Tokyo")

# 開催中ポーリング（systemd timer は 5 分。runner 側で最終判定）
ACTIVE_MIN_INTERVAL_SEC = int(os.environ.get("EXPECT_RA_ACTIVE_INTERVAL_SEC") or 120)
# 開催終了後 / 全日確定後
IDLE_MIN_INTERVAL_SEC = int(os.environ.get("EXPECT_RA_IDLE_INTERVAL_SEC") or 1800)
STATE_FILE = Path(
    os.environ.get("EXPECT_RA_CADENCE_STATE")
    or str(Path("/opt/expect-ai/shared/ra-cadence-v71.json"))
)


def _now() -> datetime:
    return datetime.now(JST)


def _read_state() -> dict[str, Any]:
    try:
        if STATE_FILE.is_file():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _write_state(doc: dict[str, Any]) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(STATE_FILE)
    except OSError:
        pass


def count_unsettled_races(race_date: str) -> dict[str, int]:
    """
    未確定 = predictions にあるが race_results に無い race_id。
    Netkeiba 未確定分は provider が空を返すため、ここが 0 なら idle 候補。
    """
    app_db.migrate()
    conn = app_db.connect()
    try:
        pred_ids = {
            str(r["race_id"])
            for r in conn.execute(
                """
                SELECT DISTINCT race_id FROM predictions
                WHERE race_id LIKE ?
                """,
                (race_date + "%",),
            ).fetchall()
        }
        # also race_id form YYYY-MM-DD-...
        pred_ids |= {
            str(r["race_id"])
            for r in conn.execute(
                """
                SELECT DISTINCT race_id FROM predictions
                WHERE substr(race_id, 1, 10)=?
                """,
                (race_date,),
            ).fetchall()
        }
        result_ids = {
            str(r["race_id"])
            for r in conn.execute(
                "SELECT DISTINCT race_id FROM race_results WHERE race_date=?",
                (race_date,),
            ).fetchall()
        }
        unsettled = sorted(pred_ids - result_ids)
        return {
            "predictions": len(pred_ids),
            "results": len(result_ids),
            "unsettled": len(unsettled),
            "unsettled_race_ids": unsettled[:50],
        }
    finally:
        conn.close()


def has_terminal_success(race_date: str) -> bool:
    conn = app_db.connect()
    try:
        row = conn.execute(
            """
            SELECT id FROM result_automation_runs
            WHERE race_date=? AND status IN (?,?)
            ORDER BY id DESC LIMIT 1
            """,
            (race_date, sm.COMPLETED, sm.DEGRADED),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def archive_exists(race_date: str) -> bool:
    return (archive_root() / f"{race_date}.json").is_file()


def decide_today_run(race_date: str, *, is_race_day: bool) -> dict[str, Any]:
    """
    Returns { run: bool, reason, cadence, unsettled, skip_until }.
    """
    unsettled = count_unsettled_races(race_date)
    state = _read_state()
    last_iso = (state.get("last_run") or {}).get(race_date)
    last_dt = None
    if last_iso:
        try:
            last_dt = datetime.fromisoformat(str(last_iso))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=JST)
        except ValueError:
            last_dt = None
    elapsed = None
    if last_dt is not None:
        elapsed = (_now() - last_dt.astimezone(JST)).total_seconds()

    meeting_done = (
        unsettled["unsettled"] == 0
        and unsettled["results"] > 0
        and has_terminal_success(race_date)
        and archive_exists(race_date)
    )

    if not is_race_day and unsettled["unsettled"] == 0 and has_terminal_success(race_date):
        return {
            "run": False,
            "reason": "not_race_day_and_settled",
            "cadence": "stop",
            "unsettled": unsettled,
            "elapsed_sec": elapsed,
        }

    if meeting_done:
        # 開催終了後: 30 分間隔のみ（または実質停止に近い間引き）
        if elapsed is not None and elapsed < IDLE_MIN_INTERVAL_SEC:
            return {
                "run": False,
                "reason": "idle_interval_not_elapsed",
                "cadence": "idle_30m",
                "unsettled": unsettled,
                "elapsed_sec": elapsed,
                "min_interval_sec": IDLE_MIN_INTERVAL_SEC,
            }
        # 全日確定済みなら軽量スキップ（force catch-up は morning モードへ）
        return {
            "run": False,
            "reason": "meeting_complete_archived",
            "cadence": "stop",
            "unsettled": unsettled,
            "elapsed_sec": elapsed,
        }

    # 開催中 / 未確定あり: 5 分間隔
    if elapsed is not None and elapsed < ACTIVE_MIN_INTERVAL_SEC - 15:
        return {
            "run": False,
            "reason": "active_interval_not_elapsed",
            "cadence": "active_5m",
            "unsettled": unsettled,
            "elapsed_sec": elapsed,
            "min_interval_sec": ACTIVE_MIN_INTERVAL_SEC,
        }

    return {
        "run": True,
        "reason": "unsettled_or_in_progress",
        "cadence": "active_5m",
        "unsettled": unsettled,
        "elapsed_sec": elapsed,
        "min_interval_sec": ACTIVE_MIN_INTERVAL_SEC,
    }


def mark_ran(race_date: str, meta: dict[str, Any] | None = None) -> None:
    state = _read_state()
    last = state.get("last_run") if isinstance(state.get("last_run"), dict) else {}
    last[race_date] = _now().isoformat()
    state["last_run"] = last
    if meta:
        state["last_meta"] = meta
    state["updated_at"] = _now().isoformat()
    _write_state(state)


def collect_v71_ops_metrics(race_date: str | None = None) -> dict[str, Any]:
    """Ops Dashboard Version7.1 指標（PE/CE 非変更）。"""
    app_db.migrate()
    day = race_date or _now().date().isoformat()
    unsettled = count_unsettled_races(day)
    conn = app_db.connect()
    try:
        # Prediction readiness from latest bundles per race (today)
        rows = conn.execute(
            """
            SELECT p.race_id, p.engine_source, p.bundle_json, p.created_at
            FROM predictions p
            INNER JOIN (
              SELECT race_id, MAX(id) AS mid FROM predictions
              WHERE substr(race_id, 1, 10)=? OR race_id LIKE ?
              GROUP BY race_id
            ) t ON p.id = t.mid
            """,
            (day, day + "%"),
        ).fetchall()
        ready = processing = pending = 0
        for r in rows:
            src = str(r["engine_source"] or "")
            raw = r["bundle_json"] or "{}"
            runners = []
            try:
                doc = json.loads(raw)
                ev = doc.get("evaluation") or {}
                runners = ev.get("runners") or doc.get("runners") or []
            except json.JSONDecodeError:
                runners = []
            if src == "pi_catalog_projection" or not runners:
                pending += 1
            elif runners:
                ready += 1
            else:
                processing += 1

        # RA durations
        ra_rows = conn.execute(
            """
            SELECT started_at, finished_at, status FROM result_automation_runs
            WHERE race_date=? AND finished_at IS NOT NULL
            ORDER BY id DESC LIMIT 20
            """,
            (day,),
        ).fetchall()
        durations = []
        for rr in ra_rows:
            try:
                a = datetime.fromisoformat(str(rr["started_at"]).replace("Z", "+00:00"))
                b = datetime.fromisoformat(str(rr["finished_at"]).replace("Z", "+00:00"))
                durations.append(max(0, (b - a).total_seconds()))
            except ValueError:
                continue
        avg_ra = round(sum(durations) / len(durations), 1) if durations else None

        active = conn.execute(
            f"""
            SELECT COUNT(*) AS n FROM result_automation_runs
            WHERE status IN ({",".join("?" * len(sm.ACTIVE))})
            """,
            tuple(sm.ACTIVE),
        ).fetchone()
        archive_q = 0
        if unsettled["results"] > 0 and not archive_exists(day):
            archive_q = 1

        archive_count = 0
        try:
            root = archive_root()
            if root.is_dir():
                archive_count = len(list(root.glob("*.json")))
        except OSError:
            archive_count = 0

        challenge_last = None
        try:
            row = conn.execute(
                "SELECT MAX(evaluated_at) AS m FROM race_evaluations WHERE race_date=?",
                (day,),
            ).fetchone()
            challenge_last = row["m"] if row else None
        except Exception:
            challenge_last = None

        return {
            "schema_version": "expect-v73-ops-metrics/1.0",
            "race_date": day,
            "prediction_ready": ready,
            "prediction_processing": processing,
            "prediction_pending": pending,
            "avg_result_automation_sec": avg_ra,
            "result_automation_pending": int((active["n"] if active else 0) or 0),
            "race_results_waiting": unsettled["unsettled"],
            "result_automation_queue": int((active["n"] if active else 0) or 0),
            "archive_queue": archive_q,
            "archive_count": archive_count,
            "challenge_last_evaluated_at": challenge_last,
            "unsettled": unsettled,
            "cadence": decide_today_run(day, is_race_day=True),
            "note": {
                "avg_prediction_fetch_ms": "client ExpectRealtimeSync.getSnapshot()",
                "avg_pending_to_ready_ms": "client ExpectRealtimeSync.getSnapshot()",
                "cache_hit_rate": "client ExpectRealtimeSync.getSnapshot()",
                "retry_success_rate": "client ExpectRealtimeSync.getSnapshot()",
                "pi_cache": "PI GET /v1/ops/cache-metrics (merged by BFF)",
            },
        }
    finally:
        conn.close()
