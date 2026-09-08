# -*- coding: utf-8 -*-
"""W4-C/D Shadow — Bounded D1/D2 acquisition (cache-first, dedupe).

Priority: P1 >>> W2 > C4 > W3-C > W4
Uses NetkeibaClient + dedicated SourceHealth (db horse pages).
Does NOT form Features / Prediction. Timer enable is Owner-gated separately.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from ..http_budget import BudgetDenied
from ..netkeiba.client import NetkeibaClient, NetkeibaFetchError
from ..w2_haron.p1_lock import p1_allows_w2, read_p1_lock
from ..w2_haron.source_health import (
    allows_mainline_fetch,
    ensure_boot_health,
    prepare_run_health,
    record_block,
    record_soft_failure,
    record_success,
    save_health,
)
from .config import W4Config
from .d1_parse import D1_URL
from .d2_parse import D2_URL
from .id_format import find_d1_html, find_d2_html
from .parse_apply import apply_d1_html, apply_d2_html, refresh_canonical_status
from .queue import load_queue, queue_stats, save_queue, write_run_report
from .raw_store import load_by_key

BLOCK_HTTP_STATUSES = frozenset({400, 403, 429})
LogFn = Callable[[str], None]


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


def _extract_http_status(exc: BaseException) -> int | None:
    if isinstance(exc, NetkeibaFetchError) and getattr(exc, "http_status", None) is not None:
        return int(exc.http_status)
    msg = str(exc)
    if "HTTP " in msg:
        try:
            part = msg.split("HTTP ", 1)[1].split(":", 1)[0].strip()
            return int(part)
        except ValueError:
            return None
    return None


@dataclass
class AcquireReport:
    started_at: str = ""
    finished_at: str = ""
    enabled: bool = True
    dry_run: bool = False
    fetch_enabled: bool = True
    http_request_count: int = 0
    paused_p1: bool = False
    yielded_w2: bool = False
    yielded_c4: bool = False
    yielded_w3c: bool = False
    stopped_block: bool = False
    stopped_budget: bool = False
    stopped_global_budget: bool = False
    global_budget_reason: str = ""
    stopped_runtime: bool = False
    stopped_consecutive: bool = False
    stop_reason: str | None = None
    p1_state: str | None = None
    source_health_state: str | None = None
    candidate_horses: int = 0
    horses_processed: int = 0
    d1_cache_hit: int = 0
    d2_cache_hit: int = 0
    d1_fetch_ok: int = 0
    d2_fetch_ok: int = 0
    d1_fetch_failed: int = 0
    d2_fetch_failed: int = 0
    d1_parse_complete: int = 0
    d2_parse_complete: int = 0
    d1_parse_partial: int = 0
    d2_parse_partial: int = 0
    d1_parse_failed: int = 0
    d2_parse_failed: int = 0
    blocked: int = 0
    duplicate_fetch_prevented: int = 0
    processed_horse_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    queue_stats: dict[str, Any] = field(default_factory=dict)
    profile_raw_rows: int = 0
    pedigree_raw_rows: int = 0
    total_queue: int = 0
    d1_pending: int = 0
    d2_pending: int = 0
    queue_path: str = ""
    run_report_path: str = ""
    shadow_only: bool = True
    feature_consumer: bool = False
    prediction_consumer: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def finalize_stop_reason(self) -> None:
        if self.stop_reason:
            return
        if not self.enabled:
            self.stop_reason = "disabled"
        elif self.paused_p1:
            self.stop_reason = "paused_p1"
        elif self.yielded_w2:
            self.stop_reason = "yielded_w2"
        elif self.yielded_c4:
            self.stop_reason = "yielded_c4"
        elif self.yielded_w3c:
            self.stop_reason = "yielded_w3c"
        elif self.stopped_block:
            self.stop_reason = "blocked_source_health"
        elif self.stopped_global_budget:
            self.stop_reason = "global_http_budget"
        elif self.stopped_runtime:
            self.stop_reason = "max_runtime"
        elif self.stopped_consecutive:
            self.stop_reason = "max_consecutive_failures"
        elif self.stopped_budget:
            self.stop_reason = "budget"
        else:
            self.stop_reason = "completed"


def select_pending_horses(
    rows: dict[str, dict[str, Any]],
    *,
    max_horses: int,
    fetch_d1: bool,
    fetch_d2: bool,
    now: datetime | None = None,
) -> list[str]:
    now = now or _utc_now()
    out: list[str] = []
    for hid, row in sorted(
        rows.items(),
        key=lambda kv: (
            str(kv[1].get("first_seen_at") or ""),
            kv[0],
        ),
    ):
        fmt = str(row.get("horse_id_format") or "")
        if fmt == "invalid":
            continue
        nxt = _parse_iso(row.get("next_eligible_at"))
        if nxt is not None and now < nxt:
            continue
        d1 = str(row.get("d1_status") or "pending")
        d2 = str(row.get("d2_status") or "pending")
        need_d1 = fetch_d1 and d1 in (
            "pending",
            "fetch_failed",
            "parse_failed",
            "cache_available",
        )
        need_d2 = fetch_d2 and d2 in (
            "pending",
            "fetch_failed",
            "parse_failed",
            "cache_available",
        )
        if not need_d1 and not need_d2:
            continue
        if d1 == "blocked" or d2 == "blocked":
            continue
        out.append(hid)
        if len(out) >= max_horses:
            break
    return out


def _persist_d1(cfg: W4Config, horse_id: str, html: str) -> Path:
    cfg.d1_cache_dir.mkdir(parents=True, exist_ok=True)
    path = cfg.d1_cache_dir / f"{horse_id}.html"
    path.write_text(html, encoding="utf-8", newline="\n")
    return path


def _persist_d2(cfg: W4Config, horse_id: str, html: str) -> Path:
    cfg.d2_cache_dir.mkdir(parents=True, exist_ok=True)
    path = cfg.d2_cache_dir / f"{horse_id}.html"
    path.write_text(html, encoding="utf-8", newline="\n")
    return path


def _tally_parse(report: AcquireReport, page: str, status: str) -> None:
    if page == "d1":
        if status == "complete":
            report.d1_parse_complete += 1
        elif status == "partial":
            report.d1_parse_partial += 1
        else:
            report.d1_parse_failed += 1
    else:
        if status == "complete":
            report.d2_parse_complete += 1
        elif status == "partial":
            report.d2_parse_partial += 1
        else:
            report.d2_parse_failed += 1


def run_w4cd_acquire(
    cfg: W4Config,
    *,
    client: NetkeibaClient | None = None,
    w2_busy: bool = False,
    c4_busy: bool = False,
    w3c_busy: bool = False,
    horse_ids: list[str] | None = None,
    logger: LogFn | None = None,
    now: datetime | None = None,
) -> AcquireReport:
    log = logger or (lambda _m: None)
    started = now or _utc_now()
    report = AcquireReport(
        started_at=_iso(started),
        enabled=cfg.w4cd_enabled,
        dry_run=cfg.w4cd_dry_run,
        fetch_enabled=cfg.w4cd_fetch_enabled and not cfg.w4cd_dry_run,
        queue_path=str(cfg.queue_path),
    )
    if not cfg.w4cd_enabled:
        report.finished_at = _iso()
        report.errors.append("W4CD_ENABLED=0")
        report.finalize_stop_reason()
        return report

    cfg.w4_root.mkdir(parents=True, exist_ok=True)
    cfg.runs_dir.mkdir(parents=True, exist_ok=True)
    cfg.raw_dir.mkdir(parents=True, exist_ok=True)
    cfg.d1_cache_dir.mkdir(parents=True, exist_ok=True)
    cfg.d2_cache_dir.mkdir(parents=True, exist_ok=True)

    lock_path = cfg.p1_lock_path or (cfg.data_root / "var" / "locks" / "p1_refresh.lock.json")
    health_path = cfg.db_horse_health_path or (
        cfg.w4_root / "source_health_netkeiba_db_horse.json"
    )

    rows = load_queue(cfg.queue_path)
    report.total_queue = len(rows)
    report.d1_pending = sum(1 for r in rows.values() if r.get("d1_status") == "pending")
    report.d2_pending = sum(1 for r in rows.values() if r.get("d2_status") == "pending")

    p1 = read_p1_lock(lock_path, now=started)
    report.p1_state = p1.state
    if p1.state != "IDLE":
        report.paused_p1 = True
        report.queue_stats = queue_stats(rows)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        log(f"[w4cd] pause: P1 state={p1.state}")
        return report

    if w2_busy:
        report.yielded_w2 = True
        report.queue_stats = queue_stats(rows)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        log("[w4cd] yield: W2 busy")
        return report
    if c4_busy:
        report.yielded_c4 = True
        report.queue_stats = queue_stats(rows)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        log("[w4cd] yield: C4 busy")
        return report
    if w3c_busy:
        report.yielded_w3c = True
        report.queue_stats = queue_stats(rows)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        log("[w4cd] yield: W3-C busy")
        return report

    health = ensure_boot_health(health_path)
    health.source = "netkeiba_db_horse"
    health = prepare_run_health(health, now=started)
    save_health(health_path, health)
    report.source_health_state = health.state
    if not allows_mainline_fetch(health):
        report.stopped_block = True
        report.stop_reason = f"source_health_{health.state}"
        report.queue_stats = queue_stats(rows)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        log(f"[w4cd] stop: SourceHealth={health.state}")
        return report

    if horse_ids:
        candidates = [h for h in horse_ids if h in rows][: cfg.max_horses_per_run]
    else:
        candidates = select_pending_horses(
            rows,
            max_horses=cfg.max_horses_per_run,
            fetch_d1=cfg.fetch_d1,
            fetch_d2=cfg.fetch_d2,
            now=started,
        )
    report.candidate_horses = len(candidates)
    if not candidates:
        report.queue_stats = queue_stats(rows)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        log("[w4cd] no pending eligible")
        return report

    net = client or NetkeibaClient(min_interval_sec=cfg.min_interval_sec, component="w4")
    consecutive_failures = 0
    run_t0 = time.monotonic()

    for hid in candidates:
        if time.monotonic() - run_t0 >= cfg.max_runtime_sec:
            report.stopped_runtime = True
            break
        if not p1_allows_w2(lock_path):
            report.paused_p1 = True
            break
        if report.http_request_count >= cfg.max_requests_per_run:
            report.stopped_budget = True
            break

        row = rows[hid]
        report.horses_processed += 1
        report.processed_horse_ids.append(hid)
        row["last_attempt_at"] = _iso()
        row["attempt_count"] = int(row.get("attempt_count") or 0) + 1

        pages: list[tuple[str, bool]] = []
        d1_st = str(row.get("d1_status") or "pending")
        d2_st = str(row.get("d2_status") or "pending")
        if cfg.fetch_d1 and d1_st in ("pending", "fetch_failed", "parse_failed", "cache_available"):
            pages.append(("d1", True))
        if cfg.fetch_d2 and d2_st in ("pending", "fetch_failed", "parse_failed", "cache_available"):
            pages.append(("d2", True))

        blocked_this_horse = False
        for page, _ in pages:
            if blocked_this_horse:
                break
            if time.monotonic() - run_t0 >= cfg.max_runtime_sec:
                report.stopped_runtime = True
                break
            if report.http_request_count >= cfg.max_requests_per_run:
                report.stopped_budget = True
                break

            if page == "d1":
                cached = find_d1_html(hid, cfg.d1_cache_roots)
                if cached is None and row.get("d1_cache_path"):
                    p = Path(str(row["d1_cache_path"]))
                    if p.is_file():
                        cached = p
            else:
                cached = find_d2_html(hid, cfg.d2_cache_roots)
                if cached is None and row.get("d2_cache_path"):
                    p = Path(str(row["d2_cache_path"]))
                    if p.is_file():
                        cached = p

            if cached is not None:
                report.duplicate_fetch_prevented += 1
                try:
                    if page == "d1":
                        applied = apply_d1_html(
                            cfg, horse_id=hid, queue_row=row, html_path=cached
                        )
                        report.d1_cache_hit += 1
                    else:
                        applied = apply_d2_html(
                            cfg, horse_id=hid, queue_row=row, html_path=cached
                        )
                        report.d2_cache_hit += 1
                    _tally_parse(report, page, applied["status"])
                    refresh_canonical_status(row)
                    rows[hid] = row
                    save_queue(cfg.queue_path, rows)
                except OSError as exc:
                    report.errors.append(f"cache_read_failed:{page}:{hid}:{exc}")
                continue

            if not report.fetch_enabled:
                report.stopped_budget = True
                log("[w4cd] dry-run / fetch disabled — stop before HTTP")
                blocked_this_horse = True
                break

            url = (D1_URL if page == "d1" else D2_URL).format(horse_id=hid)
            try:
                html = net.fetch(url, label=f"w4_{page}_{hid}", accept="text/html,application/xhtml+xml")
                report.http_request_count += 1
            except BudgetDenied as exc:
                report.stopped_global_budget = True
                report.global_budget_reason = exc.reason
                report.errors.append(f"global_budget_denied:{exc.reason}")
                log(f"[w4cd] global budget denied reason={exc.reason}")
                blocked_this_horse = True
                break
            except NetkeibaFetchError as exc:
                report.http_request_count += 1
                status = _extract_http_status(exc)
                if status in BLOCK_HTTP_STATUSES:
                    cooldown_iso = _iso(
                        _utc_now() + timedelta(seconds=cfg.cooldown_seconds)
                    )
                    row[f"{page}_status"] = "blocked"
                    row["fetch_status"] = "blocked"
                    row["error_code"] = f"HTTP_{status}"
                    row["error_reason"] = str(exc)[:300]
                    row["next_eligible_at"] = cooldown_iso
                    row["updated_at"] = _iso()
                    health = record_block(
                        health,
                        http_status=status,
                        cooldown_sec=cfg.cooldown_seconds,
                        reason=f"HTTP_{status}_HARD_STOP",
                    )
                    save_health(health_path, health)
                    report.source_health_state = health.state
                    report.blocked += 1
                    report.stopped_block = True
                    refresh_canonical_status(row)
                    rows[hid] = row
                    save_queue(cfg.queue_path, rows)
                    log(f"[w4cd] BLOCKED HTTP {status} horse={hid} page={page}")
                    blocked_this_horse = True
                    if cfg.stop_on_block:
                        break
                    continue
                next_at = _iso(
                    _utc_now() + timedelta(seconds=cfg.fetch_failed_cooldown_sec)
                )
                row[f"{page}_status"] = "fetch_failed"
                row["fetch_status"] = "fetch_failed"
                row["error_code"] = f"HTTP_{status}" if status else type(exc).__name__
                row["error_reason"] = str(exc)[:300]
                row["next_eligible_at"] = next_at
                row["updated_at"] = _iso()
                if page == "d1":
                    report.d1_fetch_failed += 1
                else:
                    report.d2_fetch_failed += 1
                health = record_soft_failure(
                    health,
                    http_status=status,
                    degraded_after=cfg.max_consecutive_failures,
                )
                if health.state == "RECOVERING":
                    health = record_block(
                        health,
                        http_status=status,
                        cooldown_sec=cfg.cooldown_seconds,
                        reason="RECOVERING_PROBE_FAIL",
                    )
                    report.stopped_block = True
                    save_health(health_path, health)
                    report.source_health_state = health.state
                    rows[hid] = row
                    save_queue(cfg.queue_path, rows)
                    blocked_this_horse = True
                    break
                save_health(health_path, health)
                report.source_health_state = health.state
                consecutive_failures += 1
                refresh_canonical_status(row)
                rows[hid] = row
                save_queue(cfg.queue_path, rows)
                if consecutive_failures >= cfg.max_consecutive_failures:
                    report.stopped_consecutive = True
                    blocked_this_horse = True
                    break
                continue
            except Exception as exc:  # noqa: BLE001
                report.http_request_count += 1
                next_at = _iso(
                    _utc_now() + timedelta(seconds=cfg.fetch_failed_cooldown_sec)
                )
                row[f"{page}_status"] = "fetch_failed"
                row["error_code"] = type(exc).__name__
                row["error_reason"] = str(exc)[:300]
                row["next_eligible_at"] = next_at
                if page == "d1":
                    report.d1_fetch_failed += 1
                else:
                    report.d2_fetch_failed += 1
                consecutive_failures += 1
                report.errors.append(f"{page}:{hid}:{type(exc).__name__}")
                rows[hid] = row
                save_queue(cfg.queue_path, rows)
                if consecutive_failures >= cfg.max_consecutive_failures:
                    report.stopped_consecutive = True
                    break
                continue

            # success
            if page == "d1":
                html_path = _persist_d1(cfg, hid, html)
                applied = apply_d1_html(
                    cfg, horse_id=hid, queue_row=row, html_path=html_path, html=html
                )
                report.d1_fetch_ok += 1
            else:
                html_path = _persist_d2(cfg, hid, html)
                applied = apply_d2_html(
                    cfg, horse_id=hid, queue_row=row, html_path=html_path, html=html
                )
                report.d2_fetch_ok += 1
            _tally_parse(report, page, applied["status"])
            health = record_success(health)
            save_health(health_path, health)
            report.source_health_state = health.state
            consecutive_failures = 0
            row["error_code"] = None
            row["error_reason"] = None
            refresh_canonical_status(row)
            rows[hid] = row
            save_queue(cfg.queue_path, rows)

        if (
            report.stopped_block
            or report.stopped_consecutive
            or report.stopped_runtime
            or report.stopped_global_budget
        ):
            break
        if report.http_request_count >= cfg.max_requests_per_run:
            report.stopped_budget = True
            break
        if report.horses_processed >= cfg.max_horses_per_run:
            report.stopped_budget = True
            break

    report.queue_stats = queue_stats(rows)
    report.total_queue = len(rows)
    report.d1_pending = sum(1 for r in rows.values() if r.get("d1_status") == "pending")
    report.d2_pending = sum(1 for r in rows.values() if r.get("d2_status") == "pending")
    report.profile_raw_rows = len(load_by_key(cfg.profile_raw_path))
    report.pedigree_raw_rows = len(load_by_key(cfg.pedigree_raw_path))
    report.finished_at = _iso()
    report.finalize_stop_reason()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_path = cfg.runs_dir / f"w4cd_acquire_{stamp}.json"
    write_run_report(run_path, report.to_dict())
    report.run_report_path = str(run_path)
    return report
