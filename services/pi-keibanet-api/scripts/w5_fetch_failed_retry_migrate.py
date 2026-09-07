#!/usr/bin/env python3
"""Staging-only one-time migration for allowlisted W5 Timeout fetch_failed horses.

Uses the real W5 JSONL queue (load_queue / save_queue).
Default: dry-run. --apply writes only rows that still match all gates.
Second apply is a no-op once next_eligible_at is set.
Does not write W4 pedigree files.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.w5_maiden_history.acquisition import RETRYABLE_TIMEOUT_CODES
from pi_keibanet.w5_maiden_history.config import W5Config
from pi_keibanet.w5_maiden_history.queue import load_queue, save_queue

ALLOWED_HORSE_IDS = ("2021107235", "2021107273", "2021100988")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _eligible(rec: dict, *, max_attempts: int) -> str | None:
    status = rec.get("queue_status")
    if status == "complete":
        return "complete_protected"
    if status != "fetch_failed":
        return f"status_{status}"
    error_code = rec.get("error_code")
    if error_code not in RETRYABLE_TIMEOUT_CODES:
        return f"error_code_{error_code}"
    nxt = rec.get("next_eligible_at")
    if nxt is not None and str(nxt).strip() != "":
        return "next_eligible_already_set"
    if int(rec.get("attempt_count") or 0) >= max_attempts:
        return "attempt_cap"
    return None


def migrate(queue_path: Path, *, apply: bool) -> dict:
    if not queue_path.is_file():
        raise FileNotFoundError(f"queue not found: {queue_path}")
    rows = load_queue(queue_path)
    max_attempts = W5Config.from_env().max_attempts_per_horse

    now = _utc_now()
    cooldown = _int_env("W5_FETCH_FAILED_COOLDOWN_SEC", 3600)
    next_eligible = _iso(now + timedelta(seconds=cooldown))
    planned: list[dict] = []
    applied: list[str] = []
    skipped: list[dict] = []

    for horse_id in ALLOWED_HORSE_IDS:
        rec = rows.get(horse_id)
        if rec is None:
            skipped.append({"horse_id": horse_id, "reason": "missing"})
            continue
        reason = _eligible(rec, max_attempts=max_attempts)
        if reason is not None:
            skipped.append({"horse_id": horse_id, "reason": reason})
            continue
        before = {
            "horse_id": horse_id,
            "queue_status": rec.get("queue_status"),
            "error_code": rec.get("error_code"),
            "attempt_count": rec.get("attempt_count"),
            "next_eligible_at": rec.get("next_eligible_at"),
        }
        after = {
            **before,
            "next_eligible_at": next_eligible,
            "updated_at": _iso(now),
        }
        planned.append({"before": before, "after": after})
        if apply:
            rec["next_eligible_at"] = next_eligible
            rec["updated_at"] = _iso(now)
            rec["queue_status"] = "fetch_failed"
            applied.append(horse_id)

    if apply and applied:
        save_queue(queue_path, rows)

    return {
        "ok": True,
        "apply": apply,
        "queue_path": str(queue_path),
        "allowed_horse_ids": list(ALLOWED_HORSE_IDS),
        "planned_count": len(planned),
        "applied_count": len(applied),
        "applied_horse_ids": applied,
        "planned": planned,
        "skipped": skipped,
        "cooldown_seconds": cooldown,
        "max_attempts_per_horse": max_attempts,
        "env_names": [
            "W5_FETCH_FAILED_COOLDOWN_SEC",
            "W5_COOLDOWN_SECONDS",
            "W5_MAX_ATTEMPTS_PER_HORSE",
        ],
        "w4_pedigree_writes": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Staging-only W5 fetch_failed retry migration")
    parser.add_argument("--queue", required=True, help="Path to horse_history_queue.jsonl")
    parser.add_argument("--apply", action="store_true", help="Write allowlisted rows (staging only)")
    args = parser.parse_args()
    report = migrate(Path(args.queue), apply=args.apply)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
