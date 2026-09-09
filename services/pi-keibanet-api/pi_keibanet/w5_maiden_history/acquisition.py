# -*- coding: utf-8 -*-
"""W5 bounded historical maiden horse-history acquisition.

Priority: P1 >>> W2 > C4 > W3-C > W4 > W5
Reuses pi_keibanet.netkeiba.horse_history (P1 RAW contract).
Dedicated SourceHealth — does not write P1 files.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from ..http_budget import BudgetDenied
from ..netkeiba.client import NetkeibaClient, NetkeibaFetchError
from ..netkeiba.horse_history import build_history_rows, fetch_horse_history
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
from .config import W5Config
from .queue import load_queue, queue_stats, save_queue, write_run_report
from .store import load_by_horse, upsert_horse_history

PERMANENT_HTTP_STATUSES = frozenset({400, 401, 403, 404})
RETRYABLE_TIMEOUT_CODES = frozenset({"TimeoutError", "ReadTimeout", "ConnectTimeout"})
LogFn = Callable[[str], None]


def _is_retryable_http_status(status: int) -> bool:
    if status == 429:
        return True
    return 500 <= status <= 599


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
            return int(msg.split("HTTP ", 1)[1].split(":", 1)[0].strip())
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
    yielded_w4: bool = False
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
    cache_hit: int = 0
    fetch_ok: int = 0
    fetch_failed: int = 0
    parse_failed: int = 0
    complete: int = 0
    blocked: int = 0
    history_rows_written: int = 0
    history_race_id_valid: int = 0
    confirmed_first_starter_candidates: int = 0
    processed_horse_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    queue_stats: dict[str, int] = field(default_factory=dict)
    queue_total: int = 0
    pending: int = 0
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
        elif self.yielded_w4:
            self.stop_reason = "yielded_w4"
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


def _is_retryable_fetch_failed(
    row: dict[str, Any],
    *,
    now: datetime,
    max_attempts: int,
) -> bool:
    if str(row.get("queue_status") or "") != "fetch_failed":
        return False
    if int(row.get("attempt_count") or 0) >= max_attempts:
        return False
    nxt = _parse_iso(row.get("next_eligible_at"))
    if nxt is None or now < nxt:
        return False
    code = str(row.get("error_code") or "")
    if code in RETRYABLE_TIMEOUT_CODES:
        return True
    if code.startswith("HTTP_"):
        try:
            status = int(code.split("_", 1)[1])
        except ValueError:
            return False
        return _is_retryable_http_status(status)
    return False


PARSE_FAILED_RETRY_CODES = frozenset({"NO_HISTORY_RACE_ID"})


def _is_retryable_parse_failed(
    row: dict[str, Any],
    *,
    max_attempts: int,
) -> bool:
    """Limited retry: parse_failed + NO_HISTORY_RACE_ID only, when flag is on."""
    if str(row.get("queue_status") or "") != "parse_failed":
        return False
    if int(row.get("attempt_count") or 0) >= max_attempts:
        return False
    code = str(row.get("error_code") or "")
    return code in PARSE_FAILED_RETRY_CODES


def _is_pending_eligible(row: dict[str, Any], *, now: datetime) -> bool:
    if str(row.get("queue_status") or "") != "pending":
        return False
    nxt = _parse_iso(row.get("next_eligible_at"))
    return nxt is None or now >= nxt


def select_pending(
    rows: dict[str, dict[str, Any]],
    *,
    max_horses: int,
    now: datetime | None = None,
) -> list[str]:
    now = now or _utc_now()
    out: list[str] = []
    for hid, row in sorted(rows.items(), key=lambda kv: (str(kv[1].get("created_at") or ""), kv[0])):
        if not _is_pending_eligible(row, now=now):
            continue
        out.append(hid)
        if len(out) >= max_horses:
            break
    return out


def select_eligible(
    rows: dict[str, dict[str, Any]],
    *,
    max_horses: int,
    now: datetime | None = None,
    retry_fetch_failed: bool = False,
    max_attempts: int = 3,
) -> list[str]:
    """Select pending, retryable fetch_failed, and limited parse_failed.

    parse_failed is retried only when retry_fetch_failed is on and
    error_code is NO_HISTORY_RACE_ID. Never complete. Never rewrite queue.
    """
    now = now or _utc_now()
    out: list[str] = []
    for hid, row in sorted(rows.items(), key=lambda kv: (str(kv[1].get("created_at") or ""), kv[0])):
        status = str(row.get("queue_status") or "")
        if status == "complete":
            continue
        if _is_pending_eligible(row, now=now):
            out.append(hid)
        elif retry_fetch_failed and _is_retryable_fetch_failed(
            row, now=now, max_attempts=max_attempts
        ):
            out.append(hid)
        elif retry_fetch_failed and _is_retryable_parse_failed(
            row, max_attempts=max_attempts
        ):
            out.append(hid)
        if len(out) >= max_horses:
            break
    return out


def _cache_paths(cfg: W5Config, horse_id: str) -> list[Path]:
    return [
        cfg.cache_dir / f"{horse_id}.json",
        cfg.cache_dir / f"{horse_id}.html",
    ]


def _load_cached_rows(cfg: W5Config, horse_id: str) -> tuple[list[dict[str, Any]] | None, Path | None]:
    for p in _cache_paths(cfg, horse_id):
        if not p.is_file():
            continue
        if p.suffix == ".json":
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict) and isinstance(data.get("rows"), list):
                rows = data["rows"]
            else:
                continue
            # Stale cache without W1 history_race_id is not reusable.
            valid = sum(
                1
                for r in rows
                if str(r.get("history_race_id") or "").isdigit()
                and len(str(r.get("history_race_id"))) == 12
            )
            if rows and valid == 0:
                continue
            return rows, p
        # HTML cache: re-parse via shared parser path
        if p.suffix == ".html":
            from ..netkeiba.horse_history import _enrich_history_row, parse_history_table_html

            html = p.read_text(encoding="utf-8", errors="replace")
            rows = [_enrich_history_row(r) for r in parse_history_table_html(html)]
            valid = sum(
                1
                for r in rows
                if str(r.get("history_race_id") or "").isdigit()
                and len(str(r.get("history_race_id"))) == 12
            )
            if rows and valid == 0:
                continue
            if rows:
                return rows, p
    return None, None


def run_w5_acquire(
    cfg: W5Config,
    *,
    client: NetkeibaClient | None = None,
    w2_busy: bool | Callable[[], bool] = False,
    c4_busy: bool | Callable[[], bool] = False,
    w3c_busy: bool | Callable[[], bool] = False,
    w4_busy: bool | Callable[[], bool] = False,
    horse_ids: list[str] | None = None,
    logger: LogFn | None = None,
    now: datetime | None = None,
) -> AcquireReport:
    log = logger or (lambda _m: None)

    def _flag(v: bool | Callable[[], bool]) -> bool:
        return bool(v() if callable(v) else v)

    started = now or _utc_now()
    report = AcquireReport(
        started_at=_iso(started),
        enabled=cfg.enabled,
        dry_run=cfg.dry_run,
        fetch_enabled=cfg.fetch_enabled and not cfg.dry_run,
    )
    if not cfg.enabled:
        report.finished_at = _iso()
        report.errors.append("W5_ENABLED=0")
        report.finalize_stop_reason()
        return report

    cfg.w5_root.mkdir(parents=True, exist_ok=True)
    cfg.runs_dir.mkdir(parents=True, exist_ok=True)
    cfg.cache_dir.mkdir(parents=True, exist_ok=True)
    cfg.raw_path.parent.mkdir(parents=True, exist_ok=True)

    lock_path = cfg.p1_lock_path or (cfg.data_root / "var" / "locks" / "p1_refresh.lock.json")
    health_path = cfg.health_path or (
        cfg.w5_root / "source_health_netkeiba_horse_history.json"
    )

    rows = load_queue(cfg.queue_path)
    report.queue_total = len(rows)
    report.pending = sum(1 for r in rows.values() if r.get("queue_status") == "pending")

    p1 = read_p1_lock(lock_path, now=started)
    report.p1_state = p1.state
    if p1.state != "IDLE":
        report.paused_p1 = True
        report.queue_stats = queue_stats(rows)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        return report

    if _flag(w2_busy):
        report.yielded_w2 = True
        report.queue_stats = queue_stats(rows)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        return report
    if _flag(c4_busy):
        report.yielded_c4 = True
        report.queue_stats = queue_stats(rows)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        return report
    if _flag(w3c_busy):
        report.yielded_w3c = True
        report.queue_stats = queue_stats(rows)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        return report
    if _flag(w4_busy):
        report.yielded_w4 = True
        report.queue_stats = queue_stats(rows)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        return report

    health = ensure_boot_health(health_path)
    health.source = "netkeiba_horse_history_research"
    health = prepare_run_health(health, now=started)
    save_health(health_path, health)
    report.source_health_state = health.state
    if not allows_mainline_fetch(health):
        report.stopped_block = True
        report.stop_reason = f"source_health_{health.state}"
        report.queue_stats = queue_stats(rows)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        return report

    if horse_ids:
        candidates = []
        for hid in horse_ids:
            if hid not in rows:
                continue
            row = rows[hid]
            if str(row.get("queue_status") or "") == "complete":
                continue
            if _is_pending_eligible(row, now=started) or (
                cfg.retry_fetch_failed
                and (
                    _is_retryable_fetch_failed(
                        row, now=started, max_attempts=cfg.max_attempts_per_horse
                    )
                    or _is_retryable_parse_failed(
                        row, max_attempts=cfg.max_attempts_per_horse
                    )
                )
            ):
                candidates.append(hid)
            if len(candidates) >= cfg.max_horses_per_run:
                break
    else:
        candidates = select_eligible(
            rows,
            max_horses=cfg.max_horses_per_run,
            now=started,
            retry_fetch_failed=cfg.retry_fetch_failed,
            max_attempts=cfg.max_attempts_per_horse,
        )
    report.candidate_horses = len(candidates)
    if not candidates:
        report.queue_stats = queue_stats(rows)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        return report

    net = client or NetkeibaClient(min_interval_sec=cfg.min_interval_sec, component="w5")
    consecutive = 0
    t0 = time.monotonic()

    for hid in candidates:
        if time.monotonic() - t0 >= cfg.max_runtime_sec:
            report.stopped_runtime = True
            break
        if not p1_allows_w2(lock_path):
            report.paused_p1 = True
            break
        # Yield to higher-priority jobs between horses (after current request finishes).
        if _flag(w2_busy):
            report.yielded_w2 = True
            break
        if _flag(c4_busy):
            report.yielded_c4 = True
            break
        if _flag(w3c_busy):
            report.yielded_w3c = True
            break
        if _flag(w4_busy):
            report.yielded_w4 = True
            break
        if report.http_request_count >= cfg.max_requests_per_run:
            report.stopped_budget = True
            break

        row = rows[hid]
        report.horses_processed += 1
        report.processed_horse_ids.append(hid)
        row["last_attempt_at"] = _iso()
        row["attempt_count"] = int(row.get("attempt_count") or 0) + 1

        cached_rows, cache_path = _load_cached_rows(cfg, hid)
        parsed: list[dict[str, Any]] | None = cached_rows
        used_cache = cached_rows is not None

        if used_cache:
            report.cache_hit += 1
        elif not report.fetch_enabled:
            report.stopped_budget = True
            log("[w5] dry-run / fetch disabled before HTTP")
            break
        else:
            try:
                parsed = fetch_horse_history(net, hid)
                # fetch_horse_history may do 1–2 HTTP calls; count conservatively as requests used
                report.http_request_count += 1
                report.fetch_ok += 1
                # persist ajax/sp-ish payload as JSON rows for cache-first
                cfg.cache_dir.mkdir(parents=True, exist_ok=True)
                cache_path = cfg.cache_dir / f"{hid}.json"
                cache_path.write_text(
                    json.dumps({"horse_id": hid, "rows": parsed}, ensure_ascii=False),
                    encoding="utf-8",
                )
                health = record_success(health)
                save_health(health_path, health)
                report.source_health_state = health.state
                consecutive = 0
            except BudgetDenied as exc:
                report.stopped_global_budget = True
                report.global_budget_reason = exc.reason
                report.errors.append(f"global_budget_denied:{exc.reason}")
                log(f"[w5] global budget denied reason={exc.reason}")
                break
            except NetkeibaFetchError as exc:
                report.http_request_count += 1
                status = _extract_http_status(exc)
                if status in PERMANENT_HTTP_STATUSES:
                    row["queue_status"] = "blocked"
                    row["error_code"] = f"HTTP_{status}"
                    row["error_reason"] = str(exc)[:300]
                    row["next_eligible_at"] = _iso(
                        _utc_now() + timedelta(seconds=cfg.cooldown_seconds)
                    )
                    health = record_block(
                        health,
                        http_status=status,
                        cooldown_sec=cfg.cooldown_seconds,
                        reason=f"HTTP_{status}_HARD_STOP",
                    )
                    health.source = "netkeiba_horse_history_research"
                    save_health(health_path, health)
                    report.source_health_state = health.state
                    report.blocked += 1
                    report.stopped_block = True
                    rows[hid] = row
                    save_queue(cfg.queue_path, rows)
                    if cfg.stop_on_block:
                        break
                    continue
                row["queue_status"] = "fetch_failed"
                row["error_code"] = f"HTTP_{status}" if status else type(exc).__name__
                row["error_reason"] = str(exc)[:300]
                row["next_eligible_at"] = _iso(
                    _utc_now() + timedelta(seconds=cfg.fetch_failed_cooldown_sec)
                )
                health = record_soft_failure(
                    health,
                    http_status=status,
                    degraded_after=cfg.max_consecutive_failures,
                )
                health.source = "netkeiba_horse_history_research"
                save_health(health_path, health)
                report.source_health_state = health.state
                report.fetch_failed += 1
                consecutive += 1
                rows[hid] = row
                save_queue(cfg.queue_path, rows)
                if consecutive >= cfg.max_consecutive_failures:
                    report.stopped_consecutive = True
                    break
                continue
            except Exception as exc:  # noqa: BLE001
                report.http_request_count += 1
                row["queue_status"] = "fetch_failed"
                row["error_code"] = type(exc).__name__
                row["error_reason"] = str(exc)[:300]
                row["next_eligible_at"] = _iso(
                    _utc_now() + timedelta(seconds=cfg.fetch_failed_cooldown_sec)
                )
                report.fetch_failed += 1
                consecutive += 1
                report.errors.append(f"{hid}:{type(exc).__name__}")
                rows[hid] = row
                save_queue(cfg.queue_path, rows)
                if consecutive >= cfg.max_consecutive_failures:
                    report.stopped_consecutive = True
                    break
                continue

        if parsed is None:
            row["queue_status"] = "parse_failed"
            report.parse_failed += 1
            rows[hid] = row
            save_queue(cfg.queue_path, rows)
            continue

        # Attach minimal runner context for OUT_COLUMNS compatibility
        runner_ctx = {
            "horse_id": hid,
            "horse_url": f"https://db.netkeiba.com/horse/{hid}/",
            "race_id": (row.get("first_seen_race_id") or ""),
        }
        history_rows = build_history_rows(runner_ctx, parsed)
        valid = sum(
            1
            for r in history_rows
            if str(r.get("history_race_id") or "").isdigit()
            and len(str(r.get("history_race_id"))) == 12
        )
        if not history_rows:
            # Successful fetch with zero rows can be first-starter candidate after cutoff check
            row["queue_status"] = "complete"
            row["history_row_count"] = 0
            row["history_race_id_valid_count"] = 0
            row["error_code"] = None
            row["error_reason"] = None
            upsert_horse_history(
                cfg.raw_path,
                horse_id=hid,
                history_rows=[],
                source="w5_fetch_empty_history",
                cache_path=str(cache_path) if cache_path else None,
            )
            report.complete += 1
            report.confirmed_first_starter_candidates += 1
            rows[hid] = row
            save_queue(cfg.queue_path, rows)
            continue

        if valid == 0 and history_rows:
            row["queue_status"] = "parse_failed"
            row["error_code"] = "NO_HISTORY_RACE_ID"
            row["error_reason"] = "history_rows_present_but_no_12digit_history_race_id"
            report.parse_failed += 1
            rows[hid] = row
            save_queue(cfg.queue_path, rows)
            continue

        stored = upsert_horse_history(
            cfg.raw_path,
            horse_id=hid,
            history_rows=history_rows,
            source="w5_fetch" if not used_cache else "w5_cache_hit",
            cache_path=str(cache_path) if cache_path else None,
        )
        row["queue_status"] = "complete"
        row["history_row_count"] = int(stored.get("history_row_count") or 0)
        row["history_race_id_valid_count"] = int(stored.get("history_race_id_valid_count") or 0)
        row["cache_path"] = str(cache_path) if cache_path else None
        row["error_code"] = None
        row["error_reason"] = None
        row["updated_at"] = _iso()
        report.complete += 1
        report.history_rows_written += int(stored.get("history_row_count") or 0)
        report.history_race_id_valid += int(stored.get("history_race_id_valid_count") or 0)
        rows[hid] = row
        save_queue(cfg.queue_path, rows)

        if report.http_request_count >= cfg.max_requests_per_run:
            report.stopped_budget = True
            break
        if report.horses_processed >= cfg.max_horses_per_run:
            report.stopped_budget = True
            break

    report.queue_stats = queue_stats(rows)
    report.queue_total = len(rows)
    report.pending = sum(1 for r in rows.values() if r.get("queue_status") == "pending")
    report.finished_at = _iso()
    report.finalize_stop_reason()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = cfg.runs_dir / f"w5_acquire_{stamp}.json"
    write_run_report(path, report.to_dict())
    report.run_report_path = str(path)
    return report
