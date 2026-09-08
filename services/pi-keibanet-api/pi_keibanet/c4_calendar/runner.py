# -*- coding: utf-8 -*-
"""C4 Shadow runner — bounded PAGE-A1 calendar recovery (Research only)."""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from ..netkeiba.client import NetkeibaClient, NetkeibaFetchError, RaceListFetchResult
from ..netkeiba.parse import parse_list_races_from_race_list, parse_meetings_from_race_list
from ..page_a1_store import persist_page_a1_after_fetch
from ..w2_haron.p1_lock import read_p1_lock
from .config import C4Config
from .domain_halt import clear_domain_halt, write_domain_halt
from .queue import (
    load_known_dates,
    load_queue,
    merge_seed,
    queue_stats,
    save_queue,
    seed_queue,
    select_work,
)
from .source_health import (
    allows_mainline_fetch,
    ensure_boot_health,
    prepare_run_health,
    reconcile_target_isolated_degraded,
    record_block,
    record_soft_failure,
    record_success,
    save_health,
)
from .target_policy import classify_empty_day_result, mark_terminal_if_exhausted

LogFn = Callable[[str], None]
FetchFn = Callable[[str], RaceListFetchResult]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utc_now()).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except ValueError:
        return None


@dataclass
class RunReport:
    started_at: str = ""
    finished_at: str = ""
    enabled: bool = True
    paused_p1: bool = False
    yielded_w2: bool = False
    stopped_block: bool = False
    stopped_budget: bool = False
    dry_run: bool = False
    seeded_n: int = 0
    queue_n: int = 0
    processed_dates: list[str] = field(default_factory=list)
    http_request_count: int = 0
    race_day_complete: int = 0
    non_race_day_confirmed: int = 0
    partial: int = 0
    partial_terminal: int = 0
    blocked: int = 0
    fetch_failed: int = 0
    malformed: int = 0
    source_health_state: str = ""
    queue_stats: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    prediction_consumer: bool = False
    feature_consumer: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _row_time_eligible(row: dict[str, Any], *, now: datetime) -> bool:
    nxt = _parse_iso(row.get("next_eligible_at"))
    return nxt is None or now >= nxt


def _is_block_status(status: int | None) -> bool:
    return status in (400, 403, 429)


def ensure_queue(cfg: C4Config) -> dict[str, dict[str, Any]]:
    known = load_known_dates(cfg.known_dates_path)
    seeded = seed_queue(
        universe_start=cfg.universe_start,
        universe_as_of=cfg.universe_as_of,
        known_dates=known,
        state_root=cfg.race_refresh_state_root,
    )
    existing = load_queue(cfg.queue_path)
    rows = merge_seed(existing, seeded) if existing else seeded
    save_queue(cfg.queue_path, rows)
    return rows


def run_c4_shadow(
    cfg: C4Config,
    *,
    client: NetkeibaClient | None = None,
    fetch_fn: FetchFn | None = None,
    w2_busy: bool = False,
    logger: LogFn | None = None,
    now: datetime | None = None,
) -> RunReport:
    log = logger or print
    started = now or _utc_now()
    report = RunReport(
        started_at=_iso(started),
        enabled=cfg.enabled,
        dry_run=cfg.dry_run,
    )
    if not cfg.enabled:
        report.finished_at = _iso()
        report.errors.append("c4_disabled")
        return report

    cfg.c4_root.mkdir(parents=True, exist_ok=True)
    cfg.runs_dir.mkdir(parents=True, exist_ok=True)

    health = ensure_boot_health(cfg.health_path)
    health = prepare_run_health(health, now=started)
    save_health(cfg.health_path, health)
    report.source_health_state = health.state

    rows = ensure_queue(cfg)
    report.seeded_n = len(rows)
    report.queue_n = len(rows)
    report.queue_stats = queue_stats(rows)

    p1 = read_p1_lock(cfg.lock_path, now=started)
    if p1.state in ("ACTIVE", "STARTING"):
        report.paused_p1 = True
        report.finished_at = _iso()
        report.http_request_count = 0
        log(f"[c4] paused: P1 state={p1.state} http=0")
        _write_run_report(cfg, report)
        return report

    if w2_busy:
        report.yielded_w2 = True
        report.finished_at = _iso()
        report.http_request_count = 0
        log("[c4] yield: W2 busy http=0")
        _write_run_report(cfg, report)
        return report

    if not allows_mainline_fetch(health):
        report.stopped_block = health.state == "BLOCKED"
        report.finished_at = _iso()
        report.errors.append(f"source_health_{health.state}")
        _write_run_report(cfg, report)
        return report

    work = select_work(
        rows,
        max_dates=cfg.max_dates_per_run,
        now_iso_eligible=lambda r: _row_time_eligible(r, now=started),
        max_attempts=cfg.max_attempts_per_date,
    )

    # If no retryable targets remain and DEGRADED was target-only (HTTP 200), reconcile.
    if not work:
        health2 = reconcile_target_isolated_degraded(health)
        if health2 is not health or health2.reason != health.reason:
            health = health2
            save_health(cfg.health_path, health)
            report.source_health_state = health.state
            report.finished_at = _iso()
            report.http_request_count = 0
            report.queue_stats = queue_stats(rows)
            log(
                f"[c4] no retryable work; source_health={health.state} "
                f"reason={health.reason} http=0"
            )
            _write_run_report(cfg, report)
            return report


    net = client or NetkeibaClient(min_interval_sec=cfg.min_interval_sec)
    do_fetch: FetchFn = fetch_fn or (lambda d: net.fetch_race_list_result(d))

    consecutive_failures = 0
    requests_used = 0
    t0 = time.monotonic()

    for row in work:
        # Re-check P1 before every HTTP
        p1 = read_p1_lock(cfg.lock_path)
        if p1.state in ("ACTIVE", "STARTING"):
            report.paused_p1 = True
            log(f"[c4] pause mid-run: P1={p1.state}")
            break
        if w2_busy:
            report.yielded_w2 = True
            break
        if not allows_mainline_fetch(health):
            report.stopped_block = True
            break
        if requests_used >= cfg.max_requests_per_run:
            report.stopped_budget = True
            break
        if (time.monotonic() - t0) >= cfg.max_runtime_sec:
            report.stopped_budget = True
            break

        kaisai_date = str(row["kaisai_date"])
        if cfg.dry_run or not cfg.fetch_enabled:
            log(f"[c4] dry-run skip fetch {kaisai_date}")
            continue

        row["attempt_count"] = int(row.get("attempt_count") or 0) + 1
        row["last_attempt_at"] = _iso()
        row["source_health_at_attempt"] = health.state
        report.processed_dates.append(kaisai_date)

        try:
            fr = do_fetch(kaisai_date)
            # count HTTP parts (sub+sp) as requests
            n_req = max(1, len(fr.parts) or 1)
            requests_used += n_req
            report.http_request_count += n_req

            try:
                meetings = parse_meetings_from_race_list(fr.merged_html)
                listed = parse_list_races_from_race_list(fr.merged_html)
                parse_ok = True
                parse_error = None
            except Exception as exc:
                meetings, listed = [], []
                parse_ok = False
                parse_error = f"{type(exc).__name__}: {exc}"

            if not parse_ok:
                row["state"] = "malformed"
                row["day_kind"] = "UNKNOWN"
                row["error_metadata"] = {"parse_error": parse_error}
                report.malformed += 1
                consecutive_failures += 1
                # Parse hard-fail may indicate source degradation.
                health = record_soft_failure(
                    health,
                    http_status=None,
                    degraded_after=cfg.max_consecutive_failures,
                )
                # still try RAW persist
                persist_page_a1_after_fetch(
                    state_root=cfg.race_refresh_state_root,
                    kaisai_date=kaisai_date,
                    fetch_result=fr,
                    meetings=[],
                    listed=[],
                    parse_ok=False,
                    parse_error=parse_error,
                    lifecycle_force="FINAL",
                    logger=log,
                )
                row = mark_terminal_if_exhausted(
                    row, max_attempts=cfg.max_attempts_per_date
                )
                if row.get("state") == "partial_terminal":
                    report.partial_terminal += 1
            else:
                pr = persist_page_a1_after_fetch(
                    state_root=cfg.race_refresh_state_root,
                    kaisai_date=kaisai_date,
                    fetch_result=fr,
                    meetings=meetings,
                    listed=listed,
                    parse_ok=True,
                    lifecycle_force="FINAL",
                    logger=log,
                )
                row["raw_snapshot_ref"] = pr.index_path
                outcome = classify_empty_day_result(
                    http_ok=True,
                    parse_ok=True,
                    completeness_state=pr.completeness_state,
                    day_kind=pr.day_kind,
                    listed_race_count=int(getattr(pr, "listed_race_count", 0) or 0),
                    attempt_count=int(row.get("attempt_count") or 0),
                    max_attempts=cfg.max_attempts_per_date,
                )
                row["state"] = outcome.state
                row["day_kind"] = pr.day_kind or "UNKNOWN"
                if outcome.state == "race_day_complete":
                    report.race_day_complete += 1
                    consecutive_failures = 0
                    health = record_success(health)
                    clear_domain_halt(cfg.domain_halt_path)
                elif outcome.state == "non_race_day_confirmed":
                    report.non_race_day_confirmed += 1
                    consecutive_failures = 0
                    health = record_success(health)
                    clear_domain_halt(cfg.domain_halt_path)
                elif outcome.state == "partial_terminal":
                    report.partial_terminal += 1
                    meta = dict(row.get("error_metadata") or {})
                    meta["terminal_reason"] = outcome.reason
                    meta["resolved"] = False
                    row["error_metadata"] = meta
                    # Target-specific incomplete: do NOT degrade SourceHealth.
                else:
                    report.partial += 1
                    # Target-specific uncertain empty: no global soft_failure.

        except NetkeibaFetchError as exc:
            status = getattr(exc, "http_status", None)
            n_req = 1
            requests_used += n_req
            report.http_request_count += n_req
            row["error_metadata"] = {"error": str(exc), "http_status": status}
            if _is_block_status(status):
                row["state"] = "blocked"
                report.blocked += 1
                health = record_block(
                    health,
                    http_status=status,
                    cooldown_sec=cfg.cooldown_seconds,
                    reason=f"HTTP_{status}_HARD_STOP",
                )
                write_domain_halt(
                    cfg.domain_halt_path,
                    reason=f"page_a1_http_{status}",
                    http_status=status,
                )
                save_health(cfg.health_path, health)
                rows[kaisai_date] = row
                report.stopped_block = True
                report.source_health_state = health.state
                if cfg.stop_on_block:
                    log(f"[c4] BLOCKED stop date={kaisai_date} status={status}")
                    break
            else:
                row["state"] = "fetch_failed"
                report.fetch_failed += 1
                consecutive_failures += 1
                health = record_soft_failure(
                    health, http_status=status, degraded_after=cfg.max_consecutive_failures
                )
                row["next_eligible_at"] = _iso(
                    _utc_now() + timedelta(seconds=cfg.fetch_failed_cooldown_sec)
                )
                row = mark_terminal_if_exhausted(
                    row, max_attempts=cfg.max_attempts_per_date
                )
                if row.get("state") == "partial_terminal":
                    report.partial_terminal += 1
                    row["next_eligible_at"] = None

        rows[kaisai_date] = row
        save_queue(cfg.queue_path, rows)
        save_health(cfg.health_path, health)
        report.source_health_state = health.state

        if consecutive_failures >= cfg.max_consecutive_failures:
            report.stopped_budget = True
            report.errors.append("max_consecutive_failures")
            break

    save_queue(cfg.queue_path, rows)
    save_health(cfg.health_path, health)
    report.queue_stats = queue_stats(rows)
    report.finished_at = _iso()
    _write_run_report(cfg, report)
    log(
        "[c4] done "
        f"http={report.http_request_count} "
        f"race={report.race_day_complete} empty={report.non_race_day_confirmed} "
        f"block={report.stopped_block} p1={report.paused_p1}"
    )
    return report


def _write_run_report(cfg: C4Config, report: RunReport) -> None:
    cfg.runs_dir.mkdir(parents=True, exist_ok=True)
    ts = report.started_at.replace(":", "").replace("-", "")
    path = cfg.runs_dir / f"c4_run_{ts}.json"
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    latest = cfg.runs_dir / "c4_run_latest.json"
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
