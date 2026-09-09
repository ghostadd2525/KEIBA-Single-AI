# -*- coding: utf-8 -*-
"""Forward-shadow evaluation sidecar (V110).

Independent of collector --loop. Does not mutate predictions / scores / site.
Does not overwrite existing v102/v105/v41 reports.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

PROD_RACE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}$")
REPORT_NAME = "v110-forward-shadow-eval.json"
WEEKLY_REPORT_NAME = "v110-forward-shadow-weekly.json"
SCHEMA_VERSION = "expect-forward-shadow-eval/1.0"
PROTECTED_REPORTS = frozenset(
    {
        "v102-evidence-analysis.json",
        "v104-evidence-ranking.json",
        "v105-shadow-resolver.json",
        "v41-world-decision-trace.json",
    }
)

AnalyzeFn = Callable[[], dict[str, Any]]
ResolverFn = Callable[[], dict[str, Any]]
WeeklyFn = Callable[[], dict[str, Any]]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def evidence_root() -> Path:
    env = (os.environ.get("RESEARCH_EVIDENCE_ROOT") or "").strip()
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "public").is_dir() and (parent / "services").is_dir():
            return parent / "evidence" / "research"
    return Path("evidence") / "research"


def report_dir() -> Path:
    return evidence_root() / "reports"


def state_dir() -> Path:
    return evidence_root() / "eval-automation"


def report_path() -> Path:
    return report_dir() / REPORT_NAME


def weekly_report_path() -> Path:
    return report_dir() / WEEKLY_REPORT_NAME


def watermark_path() -> Path:
    return state_dir() / "watermark.json"


def manifest_path() -> Path:
    return state_dir() / "manifest.json"


def lock_path() -> Path:
    return state_dir() / "eval.lock"


def db_path() -> Path:
    env = (os.environ.get("EXPECT_AI_DB_PATH") or "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "var" / "expect_ai.db"


def classify_race_id(race_id: str) -> str:
    rid = str(race_id or "")
    if rid.startswith("2099"):
        return "canary_2099"
    if "????" in rid:
        return "nonstandard"
    if not PROD_RACE_RE.match(rid):
        return "nonstandard"
    return "production"


def extract_runners(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    ev = bundle.get("evaluation")
    if isinstance(ev, dict):
        rs = ev.get("runners")
        if isinstance(rs, list) and rs:
            return list(rs)

    def _walk(obj: Any, depth: int = 0):
        if depth > 5:
            return None
        if isinstance(obj, dict):
            rs = obj.get("runners")
            if (
                isinstance(rs, list)
                and rs
                and isinstance(rs[0], dict)
                and "model_rank" in rs[0]
            ):
                return list(rs)
            for v in obj.values():
                found = _walk(v, depth + 1)
                if found is not None:
                    return found
        return None

    return _walk(bundle) or []


def unique_top_pick(runners: list[dict[str, Any]]) -> int | None:
    if not runners:
        return None
    ordered = sorted(
        runners,
        key=lambda r: (
            int(r.get("model_rank") or 999),
            -float(r.get("win_prob") or 0.0),
            int(r.get("horse_number") or 0),
        ),
    )
    try:
        return int(ordered[0]["horse_number"])
    except (KeyError, TypeError, ValueError):
        return None


def parse_bundle(text: Any) -> dict[str, Any]:
    if isinstance(text, dict):
        return text
    if not text:
        return {}
    try:
        data = json.loads(text)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


class Locked(Exception):
    """Another eval sidecar holds the flock."""


class ProtectedReportError(Exception):
    """Attempted write to an existing historical report name."""


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    if path.name in PROTECTED_REPORTS:
        raise ProtectedReportError(path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(str(tmp), 0o664)
    os.replace(str(tmp), str(path))


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


@contextmanager
def exclusive_lock(path: Path | None = None) -> Iterator[None]:
    target = path or lock_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(target), os.O_CREAT | os.O_RDWR, 0o664)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(fd)
        raise Locked("eval sidecar already running") from exc
    try:
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _connect_ro():
    import sqlite3

    path = db_path()
    uri = "file:%s?mode=ro" % path
    conn = sqlite3.connect(uri, uri=True, timeout=1.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    conn.execute("PRAGMA busy_timeout = 1000")
    return conn


def read_watermark_from_db() -> dict[str, Any]:
    conn = _connect_ro()
    try:
        snap_total = int(
            conn.execute("SELECT COUNT(*) FROM research_prediction_snapshots").fetchone()[0]
            or 0
        )
        if snap_total == 0:
            return {
                "max_prediction_id": None,
                "latest_captured_at": None,
                "input_snapshot_count": 0,
            }
        row = conn.execute(
            """
            SELECT MAX(prediction_id) AS max_pid, MAX(captured_at) AS latest_at
            FROM research_prediction_snapshots
            """
        ).fetchone()
        return {
            "max_prediction_id": int(row["max_pid"]) if row["max_pid"] is not None else None,
            "latest_captured_at": row["latest_at"],
            "input_snapshot_count": snap_total,
        }
    finally:
        conn.close()


def watermark_tuple(wm: dict[str, Any]) -> tuple[Any, Any, Any]:
    return (
        wm.get("max_prediction_id"),
        wm.get("latest_captured_at"),
        wm.get("input_snapshot_count"),
    )


def build_inventory() -> dict[str, Any]:
    conn = _connect_ro()
    try:
        rows = conn.execute(
            """
            SELECT s.prediction_id, s.race_id, s.capture_status, s.captured_at,
                   s.field_coverage, p.bundle_json, p.id AS pred_row_id
            FROM research_prediction_snapshots s
            LEFT JOIN predictions p ON p.id = s.prediction_id
            ORDER BY s.captured_at DESC, s.prediction_id DESC
            """
        ).fetchall()
    finally:
        conn.close()

    counts = {
        "total": len(rows),
        "complete": 0,
        "failed": 0,
        "partial": 0,
        "canary_2099": 0,
        "nonstandard": 0,
        "production": 0,
        "joined_bundle": 0,
        "schema_prediction_ok": 0,
        "orphan_snapshot": 0,
    }
    failed_ids: list[int] = []
    latest = None
    contains_302 = False
    contains_latest_race = False
    for r in rows:
        pid = int(r["prediction_id"])
        rid = str(r["race_id"] or "")
        status = str(r["capture_status"] or "")
        race_class = classify_race_id(rid)
        counts[status] = counts.get(status, 0) + 1
        if status == "complete":
            counts["complete"] += 0  # already via status key; keep explicit
        if race_class == "canary_2099":
            counts["canary_2099"] += 1
        elif race_class == "nonstandard":
            counts["nonstandard"] += 1
        else:
            counts["production"] += 1
        if r["pred_row_id"] is None:
            counts["orphan_snapshot"] += 1
        bundle = parse_bundle(r["bundle_json"])
        runners = extract_runners(bundle)
        joined = bool(runners)
        if joined:
            counts["joined_bundle"] += 1
            counts["schema_prediction_ok"] += 1
        if status == "failed":
            failed_ids.append(pid)
        if pid == 302:
            contains_302 = True
        if rid == "2026-09-06-01-12":
            contains_latest_race = True
        if latest is None:
            honmei = []
            for x in runners:
                if str(x.get("mark") or "").lower() == "honmei":
                    try:
                        honmei.append(int(x.get("horse_number")))
                    except (TypeError, ValueError):
                        pass
            latest = {
                "prediction_id": pid,
                "race_id": rid,
                "race_class": race_class,
                "capture_status": status,
                "captured_at": r["captured_at"],
                "joined": joined,
                "runner_count": len(runners),
                "honmei_horse_numbers": honmei,
                "unique_top_pick": unique_top_pick(runners),
                "schema_version": bundle.get("schema_version"),
                "orphan": r["pred_row_id"] is None,
            }

    latest_reaches = bool(
        latest
        and latest.get("joined")
        and latest.get("capture_status") == "complete"
        and latest.get("prediction_id") is not None
    )
    return {
        "counts": counts,
        "failed_prediction_ids": failed_ids[:20],
        "latest": latest,
        "contains_prediction_id_302": contains_302 or bool(latest and latest.get("prediction_id") == 302),
        "contains_race_2026_09_06_01_12": contains_latest_race
        or bool(latest and latest.get("race_id") == "2026-09-06-01-12"),
        "latest_snapshot_reaches_evaluation": latest_reaches,
    }


def default_analyze() -> dict[str, Any]:
    from app.research.analyzer import EvidenceAnalyzer

    return EvidenceAnalyzer().analyze()


def default_resolver() -> dict[str, Any]:
    from app.research.shadow_resolver import ShadowTieResolver

    return ShadowTieResolver().analyze()


def default_weekly() -> dict[str, Any]:
    from app.research.quality import aggregate_daily_metrics

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=6)
    daily: dict[str, Any] = {}
    cur = start
    while cur <= end:
        day = cur.date().isoformat()
        daily[day] = aggregate_daily_metrics(metric_date=day)
        cur += timedelta(days=1)
    return {
        "schema_version": "expect-forward-shadow-weekly/1.0",
        "period_start": start.date().isoformat(),
        "period_end": end.date().isoformat(),
        "daily_feature_count": {
            day: len(metrics) for day, metrics in daily.items()
        },
        "shadow_only": True,
        "production_mutation": False,
        "db_upsert": False,
    }


def _cli_summary(report: dict[str, Any] | None, err: str | None, duration: float) -> dict[str, Any]:
    if err:
        return {"ok": False, "error": err, "duration_sec": round(duration, 3)}
    corpus = report.get("corpus") if isinstance(report, dict) else None
    return {
        "ok": True,
        "duration_sec": round(duration, 3),
        "n_races": (corpus or {}).get("n_races"),
        "n_tie_races": (corpus or {}).get("n_tie_races"),
        "analyzed_at": (report or {}).get("analyzed_at") or (report or {}).get("generated_at"),
    }


def _run_cli(fn: Callable[[], dict[str, Any]] | None) -> dict[str, Any]:
    if fn is None:
        return {"ok": False, "skipped": True, "error": "cli_fn_unset"}
    t0 = time.time()
    try:
        report = fn()
        return _cli_summary(report, None, time.time() - t0)
    except Exception as exc:  # noqa: BLE001 — sidecar must not kill collector
        return _cli_summary(None, "%s:%s" % (type(exc).__name__, exc), time.time() - t0)


def run_once(
    *,
    weekly: bool = False,
    dry_run: bool = False,
    analyze_fn: AnalyzeFn | None = default_analyze,
    resolver_fn: ResolverFn | None = default_resolver,
    weekly_fn: WeeklyFn | None = default_weekly,
    skip_lock: bool = False,
) -> dict[str, Any]:
    """Run one evaluation pass. Never writes predictions or collector state."""
    t0 = time.time()
    ctx = exclusive_lock() if not skip_lock else _null_lock()
    try:
        with ctx:
            return _run_once_locked(
                weekly=weekly,
                dry_run=dry_run,
                analyze_fn=analyze_fn,
                resolver_fn=resolver_fn,
                weekly_fn=weekly_fn,
                t0=t0,
            )
    except Locked:
        return {
            "action": "skipped_locked",
            "ok": True,
            "shadow_only": True,
            "production_mutation": False,
            "http_calls": 0,
        }


@contextmanager
def _null_lock() -> Iterator[None]:
    yield


def _run_once_locked(
    *,
    weekly: bool,
    dry_run: bool,
    analyze_fn: AnalyzeFn | None,
    resolver_fn: ResolverFn | None,
    weekly_fn: WeeklyFn | None,
    t0: float,
) -> dict[str, Any]:
    current = read_watermark_from_db()
    current["generated_at"] = _now()
    prev = load_json(watermark_path()) or {}
    if int(current.get("input_snapshot_count") or 0) == 0:
        out = {
            "action": "noop_no_snapshots",
            "ok": True,
            "watermark": current,
            "shadow_only": True,
            "production_mutation": False,
            "http_calls": 0,
            "latest_snapshot_reaches_evaluation": False,
        }
        return out
    if watermark_tuple(prev) == watermark_tuple(current) and not weekly:
        return {
            "action": "noop_same_watermark",
            "ok": True,
            "watermark": current,
            "previous_generated_at": prev.get("generated_at"),
            "shadow_only": True,
            "production_mutation": False,
            "http_calls": 0,
            "latest_snapshot_reaches_evaluation": True,
            "report_path": str(report_path()) if report_path().is_file() else None,
        }
    if dry_run:
        return {
            "action": "dry_run_would_generate",
            "ok": True,
            "watermark": current,
            "shadow_only": True,
            "production_mutation": False,
            "http_calls": 0,
        }

    inventory = build_inventory()
    analyze_out = _run_cli(analyze_fn)
    resolver_out = _run_cli(resolver_fn)
    weekly_out = _run_cli(weekly_fn) if weekly else {"ok": True, "skipped": True}

    payload = {
        "schema_version": SCHEMA_VERSION,
        "report_name": REPORT_NAME,
        "shadow_only": True,
        "production_mutation": False,
        "http_calls": 0,
        "cli_order": [
            "inventory_t2_join_predictions",
            "--analyze-evidence (EvidenceAnalyzer.analyze)",
            "--shadow-resolver (ShadowTieResolver.analyze)",
            "--weekly-report (aggregate_daily_metrics, no DB upsert)" if weekly else "weekly_skipped",
        ],
        "generated_at": current["generated_at"],
        "watermark": {
            "max_prediction_id": current.get("max_prediction_id"),
            "latest_captured_at": current.get("latest_captured_at"),
            "input_snapshot_count": current.get("input_snapshot_count"),
            "generated_at": current["generated_at"],
        },
        "inventory": inventory,
        "cli_analyze_evidence": analyze_out,
        "cli_shadow_resolver": resolver_out,
        "cli_weekly_report": weekly_out,
        "latest_snapshot_reaches_evaluation": bool(
            inventory.get("latest_snapshot_reaches_evaluation")
        ),
        "contains_prediction_id_302": bool(inventory.get("contains_prediction_id_302")),
        "contains_race_2026_09_06_01_12": bool(inventory.get("contains_race_2026_09_06_01_12")),
        "duration_sec": round(time.time() - t0, 3),
        "recommended_timer_interval_sec": 3600,
        "recommended_timer": "hourly; do not use 120s",
    }

    dest = report_path()
    old = load_json(dest)
    try:
        atomic_write_json(dest, payload)
        atomic_write_json(watermark_path(), current)
        atomic_write_json(
            manifest_path(),
            {
                "schema_version": "expect-forward-shadow-eval-manifest/1.0",
                "report_name": REPORT_NAME,
                "report_path": str(dest),
                "watermark": current,
                "generated_at": current["generated_at"],
                "latest_snapshot_reaches_evaluation": payload["latest_snapshot_reaches_evaluation"],
                "shadow_only": True,
                "production_mutation": False,
            },
        )
        if weekly:
            atomic_write_json(
                weekly_report_path(),
                {
                    "schema_version": "expect-forward-shadow-weekly/1.0",
                    "generated_at": current["generated_at"],
                    "watermark": current,
                    "cli_weekly_report": weekly_out,
                    "shadow_only": True,
                    "production_mutation": False,
                    "db_upsert": False,
                },
            )
    except Exception:
        if old is not None:
            dest.write_text(json.dumps(old, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise

    payload["action"] = "generated"
    payload["ok"] = True
    payload["report_path"] = str(dest)
    return payload
