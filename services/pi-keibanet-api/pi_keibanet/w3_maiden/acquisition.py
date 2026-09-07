# -*- coding: utf-8 -*-
"""W3-C — Shared netkeiba_page_c bounded acquisition for pending maiden races.

Priority: P1 >>> W2 > C4 > W3-C > W4
Reuses W2 SourceHealth + RESULT_URL + NetkeibaClient.
Reuses W3-B result parser after HTML is on disk.
Does NOT start W4 / Feature / Prediction.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

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
from .cache_probe import find_page_c_html
from .config import PAGE_C_RESULT_URL, W3AConfig
from .queue import is_valid_race_id, load_queue, queue_stats, save_queue, write_run_report
from .result_apply import apply_html_result_parse
from .result_store import load_runner_jsonl

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
    stopped_block: bool = False
    stopped_budget: bool = False
    stopped_runtime: bool = False
    stopped_consecutive: bool = False
    stop_reason: str | None = None
    p1_state: str | None = None
    source_health_state: str | None = None
    pending_input: int = 0
    candidate_count: int = 0
    cache_hit_no_http: int = 0
    requested: int = 0
    fetch_ok: int = 0
    fetch_failed: int = 0
    blocked: int = 0
    result_complete: int = 0
    partial: int = 0
    parse_failed: int = 0
    processed_race_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    queue_status_counts: dict[str, int] = field(default_factory=dict)
    # inventory snapshot
    total_queue: int = 0
    total_runners_parsed: int = 0
    unique_horse_ids: int = 0
    horse_id_missing: int = 0
    trainer_present: int = 0
    trainer_missing: int = 0
    body_weight_present: int = 0
    body_weight_missing: int = 0
    odds_present: int = 0
    odds_missing: int = 0
    w4_candidate_unique_horses: int = 0
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
        elif self.stopped_block:
            self.stop_reason = "blocked_source_health"
        elif self.stopped_runtime:
            self.stop_reason = "max_runtime"
        elif self.stopped_consecutive:
            self.stop_reason = "max_consecutive_failures"
        elif self.stopped_budget:
            self.stop_reason = "budget"
        else:
            self.stop_reason = "completed"


def select_pending_races(
    rows: dict[str, dict[str, Any]],
    *,
    max_races: int,
    max_attempts: int,
    now: datetime | None = None,
) -> list[str]:
    """Eligible: pending + valid race_id + next_eligible_at ok + attempts under cap."""
    now = now or _utc_now()
    out: list[str] = []
    for rid, row in sorted(
        rows.items(),
        key=lambda kv: (
            str(kv[1].get("kaisai_date") or ""),
            kv[0],
        ),
    ):
        if str(row.get("queue_status") or "") != "pending":
            continue
        if not is_valid_race_id(rid):
            continue
        attempts = int(row.get("attempt_count") or 0)
        if attempts >= max_attempts:
            continue
        nxt = _parse_iso(row.get("next_eligible_at"))
        if nxt is not None and now < nxt:
            continue
        out.append(rid)
        if len(out) >= max_races:
            break
    return out


def _persist_shared_html(cfg: W3AConfig, race_id: str, html: str) -> Path:
    """Write HTML to W3 page_c_cache and shared W2 raw (create-only if missing)."""
    cfg.page_c_cache_dir.mkdir(parents=True, exist_ok=True)
    w3_path = cfg.page_c_cache_dir / f"{race_id}.html"
    w3_path.write_text(html, encoding="utf-8")
    # Shared PAGE-C for W2/W3 dedupe — do not overwrite existing shared file
    cfg.w2_raw_root.mkdir(parents=True, exist_ok=True)
    shared = cfg.w2_raw_root / f"{race_id}.html"
    if not shared.is_file():
        shared.write_text(html, encoding="utf-8")
    return w3_path


def _inventory_from_store(cfg: W3AConfig, report: AcquireReport) -> None:
    runners = load_runner_jsonl(cfg.runner_raw_path)
    uniq: set[str] = set()
    missing = 0
    tr_ok = tr_miss = bw_ok = bw_miss = od_ok = od_miss = 0
    for (_rid, key), r in runners.items():
        hid = r.get("horse_id")
        if hid and not str(key).startswith("missing:"):
            uniq.add(str(hid))
            has_tr = bool(
                r.get("race_time_trainer_id") or r.get("race_time_trainer_name")
            )
            tr_ok += 1 if has_tr else 0
            tr_miss += 0 if has_tr else 1
            bw_ok += 1 if r.get("body_weight") is not None else 0
            bw_miss += 0 if r.get("body_weight") is not None else 1
            od_ok += 1 if r.get("odds") is not None else 0
            od_miss += 0 if r.get("odds") is not None else 1
        else:
            missing += 1
    report.total_runners_parsed = len(runners)
    report.unique_horse_ids = len(uniq)
    report.w4_candidate_unique_horses = len(uniq)
    report.horse_id_missing = missing
    report.trainer_present = tr_ok
    report.trainer_missing = tr_miss
    report.body_weight_present = bw_ok
    report.body_weight_missing = bw_miss
    report.odds_present = od_ok
    report.odds_missing = od_miss


def run_w3c_acquire(
    cfg: W3AConfig,
    *,
    client: NetkeibaClient | None = None,
    w2_busy: bool = False,
    c4_busy: bool = False,
    logger: LogFn | None = None,
    now: datetime | None = None,
) -> AcquireReport:
    log = logger or (lambda _m: None)
    started = now or _utc_now()
    report = AcquireReport(
        started_at=_iso(started),
        enabled=cfg.w3c_enabled,
        dry_run=cfg.w3c_dry_run,
        fetch_enabled=cfg.w3c_fetch_enabled and not cfg.w3c_dry_run,
        queue_path=str(cfg.queue_path),
    )
    if not cfg.w3c_enabled:
        report.finished_at = _iso()
        report.errors.append("W3C_ENABLED=0")
        report.finalize_stop_reason()
        return report

    cfg.w3_root.mkdir(parents=True, exist_ok=True)
    cfg.runs_dir.mkdir(parents=True, exist_ok=True)
    cfg.raw_dir.mkdir(parents=True, exist_ok=True)
    cfg.page_c_cache_dir.mkdir(parents=True, exist_ok=True)

    lock_path = cfg.p1_lock_path or (cfg.data_root / "var" / "locks" / "p1_refresh.lock.json")
    health_path = cfg.page_c_health_path or (
        cfg.data_root / "var" / "layer_b_haron" / "source_health_netkeiba_page_c.json"
    )

    rows = load_queue(cfg.queue_path)
    report.total_queue = len(rows)
    report.pending_input = sum(
        1 for r in rows.values() if str(r.get("queue_status") or "") == "pending"
    )

    # P1 gate
    p1 = read_p1_lock(lock_path, now=started)
    report.p1_state = p1.state
    if p1.state != "IDLE":
        report.paused_p1 = True
        report.queue_status_counts = queue_stats(rows)
        _inventory_from_store(cfg, report)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        log(f"[w3c] pause: P1 state={p1.state}")
        return report

    # W2 / C4 yield (higher priority)
    if w2_busy:
        report.yielded_w2 = True
        report.queue_status_counts = queue_stats(rows)
        _inventory_from_store(cfg, report)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        log("[w3c] yield: W2 busy")
        return report
    if c4_busy:
        report.yielded_c4 = True
        report.queue_status_counts = queue_stats(rows)
        _inventory_from_store(cfg, report)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        log("[w3c] yield: C4 busy")
        return report

    health = ensure_boot_health(health_path)
    health = prepare_run_health(health, now=started)
    save_health(health_path, health)
    report.source_health_state = health.state

    if not allows_mainline_fetch(health):
        report.stopped_block = True
        report.stop_reason = f"source_health_{health.state}"
        report.queue_status_counts = queue_stats(rows)
        _inventory_from_store(cfg, report)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        log(f"[w3c] stop: SourceHealth={health.state}")
        return report

    candidates = select_pending_races(
        rows,
        max_races=cfg.max_races_per_run,
        max_attempts=cfg.max_attempts_per_race,
        now=started,
    )
    report.candidate_count = len(candidates)
    if not candidates:
        report.queue_status_counts = queue_stats(rows)
        _inventory_from_store(cfg, report)
        report.finished_at = _iso()
        report.finalize_stop_reason()
        log("[w3c] no pending eligible")
        return report

    net = client or NetkeibaClient(min_interval_sec=cfg.min_interval_sec)
    consecutive_failures = 0
    run_t0 = time.monotonic()
    cache_roots = cfg.cache_roots()

    for rid in candidates:
        if time.monotonic() - run_t0 >= cfg.max_runtime_sec:
            report.stopped_runtime = True
            log("[w3c] stop: max runtime")
            break
        if not p1_allows_w2(lock_path):
            report.paused_p1 = True
            log("[w3c] pause: P1 became active")
            break
        if report.http_request_count >= cfg.max_requests_per_run:
            report.stopped_budget = True
            break

        row = rows[rid]
        if str(row.get("queue_status") or "") != "pending":
            continue  # V-W3C-1 / skip non-pending

        # Cache-first — never HTTP if HTML exists
        cached = find_page_c_html(rid, cache_roots)
        if cached is not None:
            try:
                applied = apply_html_result_parse(
                    cfg, race_id=rid, queue_row=row, html_path=cached
                )
                report.cache_hit_no_http += 1
                report.processed_race_ids.append(rid)
                st = applied["queue_status"]
                if st == "result_complete":
                    report.result_complete += 1
                elif st == "partial":
                    report.partial += 1
                else:
                    report.parse_failed += 1
                row["fetch_status"] = "cache_hit"
                row["source_health_at_attempt"] = health.state
                rows[rid] = row
                save_queue(cfg.queue_path, rows)
                continue
            except OSError as exc:
                report.errors.append(f"cache_read_failed:{rid}:{exc}")
                # fall through to fetch only if fetch enabled

        if not report.fetch_enabled:
            report.stopped_budget = True
            log("[w3c] dry-run / fetch disabled — stop before HTTP")
            break

        url = PAGE_C_RESULT_URL.format(race_id=rid)
        report.requested += 1
        report.processed_race_ids.append(rid)
        row["last_attempt_at"] = _iso()
        row["attempt_count"] = int(row.get("attempt_count") or 0) + 1
        row["source_health_at_attempt"] = health.state

        try:
            html = net.fetch(url, label=f"w3c_page_c_{rid}")
            report.http_request_count += 1
        except NetkeibaFetchError as exc:
            report.http_request_count += 1
            status = _extract_http_status(exc)
            if status in BLOCK_HTTP_STATUSES:
                cooldown_iso = _iso(
                    _utc_now() + timedelta(seconds=cfg.cooldown_seconds)
                )
                row["queue_status"] = "blocked"
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
                rows[rid] = row
                save_queue(cfg.queue_path, rows)
                log(f"[w3c] BLOCKED HTTP {status} race={rid}")
                if cfg.stop_on_block:
                    break
                continue
            next_at = _iso(
                _utc_now() + timedelta(seconds=cfg.fetch_failed_cooldown_sec)
            )
            row["queue_status"] = "fetch_failed"
            row["fetch_status"] = "fetch_failed"
            row["error_code"] = f"HTTP_{status}" if status else type(exc).__name__
            row["error_reason"] = str(exc)[:300]
            row["next_eligible_at"] = next_at
            row["updated_at"] = _iso()
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
                report.fetch_failed += 1
                rows[rid] = row
                save_queue(cfg.queue_path, rows)
                break
            save_health(health_path, health)
            report.source_health_state = health.state
            report.fetch_failed += 1
            consecutive_failures += 1
            rows[rid] = row
            save_queue(cfg.queue_path, rows)
            if consecutive_failures >= cfg.max_consecutive_failures:
                report.stopped_consecutive = True
                break
            continue
        except Exception as exc:  # noqa: BLE001
            report.http_request_count += 1
            next_at = _iso(
                _utc_now() + timedelta(seconds=cfg.fetch_failed_cooldown_sec)
            )
            row["queue_status"] = "fetch_failed"
            row["fetch_status"] = "fetch_failed"
            row["error_code"] = type(exc).__name__
            row["error_reason"] = str(exc)[:300]
            row["next_eligible_at"] = next_at
            row["updated_at"] = _iso()
            report.fetch_failed += 1
            report.errors.append(f"{rid}:{type(exc).__name__}")
            consecutive_failures += 1
            rows[rid] = row
            save_queue(cfg.queue_path, rows)
            if consecutive_failures >= cfg.max_consecutive_failures:
                report.stopped_consecutive = True
                break
            continue

        # Success path: persist shared HTML + W3-B parse
        html_path = _persist_shared_html(cfg, rid, html)
        row["fetch_status"] = "fetched"
        row["cache_html_path"] = str(html_path)
        row["raw_html_reference"] = str(html_path)
        row["error_code"] = None
        row["error_reason"] = None
        health = record_success(health)
        save_health(health_path, health)
        report.source_health_state = health.state
        report.fetch_ok += 1
        consecutive_failures = 0

        applied = apply_html_result_parse(
            cfg, race_id=rid, queue_row=row, html_path=html_path, html=html
        )
        st = applied["queue_status"]
        if st == "result_complete":
            report.result_complete += 1
        elif st == "partial":
            report.partial += 1
        else:
            report.parse_failed += 1
        rows[rid] = row
        save_queue(cfg.queue_path, rows)

        if report.http_request_count >= cfg.max_requests_per_run:
            report.stopped_budget = True
            break
        if len(report.processed_race_ids) >= cfg.max_races_per_run:
            report.stopped_budget = True
            break

    report.queue_status_counts = queue_stats(rows)
    report.total_queue = len(rows)
    _inventory_from_store(cfg, report)
    report.finished_at = _iso()
    report.finalize_stop_reason()

    # Incremental W4-A intake (HTTP 0). Failure must never stop W3-C.
    try:
        from ..w4_horse.config import W4Config
        from ..w4_horse.handoff import run_w4a_handoff

        w4cfg = W4Config.from_env(data_root=cfg.data_root)
        w4cfg.w3_root = cfg.w3_root
        w4_report = run_w4a_handoff(w4cfg)
        report.w4_candidate_unique_horses = int(
            w4_report.w4_canonical_horses or report.w4_candidate_unique_horses
        )
        if w4_report.errors:
            report.errors.append(f"w4a_handoff_nonfatal:{w4_report.errors[0]}")
        log(
            f"[w3c] w4a handoff horses={w4_report.w4_canonical_horses} "
            f"new={w4_report.new_rows} http={w4_report.http_request_count}"
        )
    except Exception as exc:  # noqa: BLE001
        report.errors.append(f"w4a_handoff_nonfatal:{type(exc).__name__}:{exc}")
        log(f"[w3c] w4a handoff skipped: {exc}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_path = cfg.runs_dir / f"w3c_acquire_{stamp}.json"
    write_run_report(run_path, report.to_dict())
    report.run_report_path = str(run_path)
    return report
