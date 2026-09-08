# -*- coding: utf-8 -*-
"""W2 Shadow runner - bounded incremental PAGE-C acquisition."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from ..http_budget import BudgetDenied
from ..netkeiba.client import NetkeibaClient, NetkeibaFetchError
from .config import PARSER_VERSION, RESULT_URL, SOURCE_NAME, W2Config
from .eligibility import select_eligible_race_ids
from .haron_parse import parse_haron
from .intake import collect_history_race_ids_from_csv, collect_new_ids_from_state
from .layer_b_store import (
    bootstrap_from_seal,
    find_cache_html,
    mark_row,
    save_index,
    try_promote_cache_hit_from_disk,
    upsert_pending,
)
from .p1_lock import p1_allows_w2, read_p1_lock
from .source_health import (
    ensure_boot_health,
    prepare_run_health,
    record_block,
    record_soft_failure,
    record_success,
    save_health,
)

BLOCK_HTTP_STATUSES = frozenset({400, 403, 429})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _utc_now()).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class RunReport:
    started_at: str
    finished_at: str | None = None
    enabled: bool = True
    dry_run: bool = False
    fetch_enabled: bool = True
    seal_bootstrapped: bool = False
    index_rows: int = 0
    new_pending_added: int = 0
    cache_promoted: int = 0
    requested: int = 0
    cache_hit_skipped: int = 0
    success_cache_hit: int = 0
    source_missing: int = 0
    fetch_failed: int = 0
    blocked: int = 0
    parse_failed: int = 0
    paused_p1: bool = False
    stopped_block: bool = False
    stopped_budget: bool = False
    stopped_global_budget: bool = False
    global_budget_reason: str = ""
    stopped_runtime: bool = False
    stopped_consecutive: bool = False
    source_health_state: str | None = None
    p1_state: str | None = None
    candidate_count: int = 0
    pending_remaining: int = 0
    stop_reason: str | None = None
    errors: list[str] = field(default_factory=list)
    processed_race_ids: list[str] = field(default_factory=list)
    http_request_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "ended_at": self.finished_at,
            "finished_at": self.finished_at,
            "enabled": self.enabled,
            "dry_run": self.dry_run,
            "fetch_enabled": self.fetch_enabled,
            "seal_bootstrapped": self.seal_bootstrapped,
            "index_rows": self.index_rows,
            "new_pending_added": self.new_pending_added,
            "cache_promoted": self.cache_promoted,
            "candidate_count": self.candidate_count,
            "requested": self.requested,
            "fetched": self.success_cache_hit + self.source_missing + self.parse_failed,
            "cache_hits": self.cache_hit_skipped + self.cache_promoted + self.success_cache_hit,
            "cache_hit_skipped": self.cache_hit_skipped,
            "success_cache_hit": self.success_cache_hit,
            "source_missing": self.source_missing,
            "fetch_failed": self.fetch_failed,
            "blocked": self.blocked,
            "parse_failed": self.parse_failed,
            "pending_remaining": self.pending_remaining,
            "paused_p1": self.paused_p1,
            "p1_state": self.p1_state,
            "stopped_block": self.stopped_block,
            "stopped_budget": self.stopped_budget,
            "stopped_global_budget": self.stopped_global_budget,
            "global_budget_reason": self.global_budget_reason,
            "stopped_runtime": self.stopped_runtime,
            "stopped_consecutive": self.stopped_consecutive,
            "stop_reason": self.stop_reason,
            "source_health_state": self.source_health_state,
            "errors": self.errors,
            "processed_race_ids": self.processed_race_ids,
            "http_request_count": self.http_request_count,
            "shadow_only": True,
            "feature_consumer": False,
            "prediction_consumer": False,
        }

    def finalize_stop_reason(self) -> None:
        if self.stop_reason:
            return
        if not self.enabled:
            self.stop_reason = "disabled"
        elif self.paused_p1:
            self.stop_reason = "p1_active"
        elif self.stopped_global_budget:
            self.stop_reason = "global_http_budget"
        elif self.stopped_block:
            self.stop_reason = "source_blocked"
        elif self.stopped_runtime:
            self.stop_reason = "max_runtime"
        elif self.stopped_consecutive:
            self.stop_reason = "max_consecutive_failures"
        elif self.stopped_budget:
            self.stop_reason = "max_races_budget"
        elif self.dry_run or not self.fetch_enabled:
            self.stop_reason = "dry_run"
        else:
            self.stop_reason = "completed"


def _extract_http_status(exc: BaseException) -> int | None:
    if isinstance(exc, NetkeibaFetchError) and exc.http_status is not None:
        return int(exc.http_status)
    msg = str(exc)
    if "HTTP " in msg:
        try:
            part = msg.split("HTTP ", 1)[1].split(":", 1)[0].strip()
            return int(part)
        except ValueError:
            return None
    return None


def run_w2_shadow(
    config: W2Config | None = None,
    *,
    client: NetkeibaClient | None = None,
    history_csv: Path | None = None,
    date: str | None = None,
    logger: Callable[[str], None] | None = None,
    now: datetime | None = None,
) -> RunReport:
    cfg = config or W2Config.from_env()
    log = logger or print
    started = now or _utc_now()
    report = RunReport(
        started_at=_iso(started),
        enabled=cfg.enabled,
        dry_run=cfg.dry_run,
        fetch_enabled=cfg.fetch_enabled and not cfg.dry_run,
    )

    if not cfg.enabled:
        report.finished_at = _iso()
        report.p1_state = read_p1_lock(cfg.lock_path).state
        report.finalize_stop_reason()
        report.errors.append("W2_ENABLED=0")
        log("[w2-haron] disabled (W2_ENABLED=0) - rollback/off")
        return report

    cfg.layer_b_root.mkdir(parents=True, exist_ok=True)
    cfg.raw_dir.mkdir(parents=True, exist_ok=True)
    cfg.parsed_dir.mkdir(parents=True, exist_ok=True)
    cfg.runs_dir.mkdir(parents=True, exist_ok=True)

    seal_existed = cfg.index_path.exists()
    rows = bootstrap_from_seal(cfg.index_path, cfg.seal_index_path)
    report.seal_bootstrapped = not seal_existed and cfg.seal_index_path.exists()
    report.index_rows = len(rows)

    health = ensure_boot_health(cfg.health_path)
    health = prepare_run_health(health, now=started)
    save_health(cfg.health_path, health)

    # Incremental intake (new W1 ids only - never full 10431 re-enqueue).
    new_ids: set[str] = set()
    if history_csv is not None:
        new_ids |= collect_history_race_ids_from_csv(history_csv)
    else:
        new_ids |= collect_new_ids_from_state(
            cfg.race_refresh_state_root, date=date, lookback_days=7
        )
    added = upsert_pending(rows, new_ids)
    report.new_pending_added = len(added)
    if added:
        log(f"[w2-haron] new pending registered: {len(added)}")

    # Cache-first promote (no HTTP).
    for rid, row in list(rows.items()):
        if row.get("canonical_status") in ("pending", "fetch_failed"):
            if try_promote_cache_hit_from_disk(
                row, cache_roots=cfg.cache_roots(), parse_fn=parse_haron
            ):
                report.cache_promoted += 1

    save_index(cfg.index_path, rows)

    p1 = read_p1_lock(cfg.lock_path, now=started)
    report.p1_state = p1.state
    if p1.state != "IDLE":
        report.paused_p1 = True
        report.source_health_state = health.state
        report.pending_remaining = sum(
            1 for r in rows.values() if r.get("canonical_status") == "pending"
        )
        report.finished_at = _iso()
        report.finalize_stop_reason()
        save_index(cfg.index_path, rows)
        _write_run_report(cfg, report)
        log(f"[w2-haron] suspend: P1 lock state={p1.state}")
        return report

    if not report.fetch_enabled:
        report.source_health_state = health.state
        report.pending_remaining = sum(
            1 for r in rows.values() if r.get("canonical_status") == "pending"
        )
        report.finished_at = _iso()
        report.finalize_stop_reason()
        save_index(cfg.index_path, rows)
        _write_run_report(cfg, report)
        log("[w2-haron] dry-run / fetch disabled - intake+cache-promote only")
        return report

    eligible = select_eligible_race_ids(
        rows,
        health=health,
        p1=p1,
        max_attempts=cfg.max_attempts_per_race,
        max_races=cfg.max_races_per_run,
        now=started,
    )
    report.candidate_count = len(eligible)
    if not eligible:
        report.source_health_state = health.state
        report.pending_remaining = sum(
            1 for r in rows.values() if r.get("canonical_status") == "pending"
        )
        report.finished_at = _iso()
        report.finalize_stop_reason()
        save_index(cfg.index_path, rows)
        _write_run_report(cfg, report)
        log("[w2-haron] no eligible races")
        return report

    net = client or NetkeibaClient(min_interval_sec=cfg.min_interval_sec, component="w2")
    consecutive_failures = 0
    run_t0 = time.monotonic()

    for rid in eligible:
        # Runtime / P1 re-check before each request.
        if time.monotonic() - run_t0 >= cfg.max_runtime_sec:
            report.stopped_runtime = True
            log("[w2-haron] stop: max runtime")
            break
        if not p1_allows_w2(cfg.lock_path):
            report.paused_p1 = True
            log("[w2-haron] pause: P1 became active - no further requests")
            break

        row = rows[rid]
        # Final cache-first guard (V1).
        if row.get("canonical_status") == "cache_hit" or row.get("refetch_prohibited"):
            if row.get("canonical_status") == "cache_hit":
                report.cache_hit_skipped += 1
            continue
        cached = find_cache_html(rid, cfg.cache_roots())
        if cached is not None:
            try:
                html_cached = cached.read_text(encoding="utf-8", errors="replace")
                parsed_c = parse_haron(html_cached)
                if parsed_c.get("parse_ok"):
                    mark_row(
                        row,
                        status="cache_hit",
                        raw_html_path=str(cached),
                        raw_haron_present=True,
                        parsed_haron_present=True,
                        sectional_sequence=parsed_c.get("sectional")
                        or parsed_c.get("cumulative"),
                        retrieved=True,
                    )
                    row["refetch_prohibited"] = True
                    report.cache_hit_skipped += 1
                    report.cache_promoted += 1
                    continue
            except OSError:
                pass

        url = RESULT_URL.format(race_id=rid)
        report.requested += 1
        report.processed_race_ids.append(rid)
        try:
            html = net.fetch(url, label=f"w2_result_{rid}")
            report.http_request_count += 1
        except BudgetDenied as exc:
            report.stopped_global_budget = True
            report.global_budget_reason = exc.reason
            report.errors.append(f"global_budget_denied:{exc.reason}")
            log(f"[w2-haron] global budget denied reason={exc.reason}")
            break
        except NetkeibaFetchError as exc:
            report.http_request_count += 1
            status = _extract_http_status(exc)
            if status in BLOCK_HTTP_STATUSES:
                cooldown_iso = _iso(
                    _utc_now() + timedelta(seconds=cfg.source_cooldown_sec)
                )
                mark_row(
                    row,
                    status="blocked",
                    error_code=f"HTTP_{status}",
                    error_reason=str(exc)[:300],
                    next_eligible_at=cooldown_iso,
                    bump_attempt=True,
                )
                health = record_block(
                    health,
                    http_status=status,
                    cooldown_sec=cfg.source_cooldown_sec,
                    reason=f"HTTP_{status}_HARD_STOP",
                )
                save_health(cfg.health_path, health)
                report.blocked += 1
                report.stopped_block = True
                log(f"[w2-haron] BLOCKED HTTP {status} race={rid} - stop run")
                if cfg.stop_on_block:
                    break
                continue
            # Soft failure
            next_at = _iso(
                _utc_now() + timedelta(seconds=cfg.fetch_failed_cooldown_sec)
            )
            mark_row(
                row,
                status="fetch_failed",
                error_code=f"HTTP_{status}" if status else type(exc).__name__,
                error_reason=str(exc)[:300],
                next_eligible_at=next_at,
                bump_attempt=True,
            )
            health = record_soft_failure(
                health,
                http_status=status,
                degraded_after=cfg.max_consecutive_failures,
            )
            if health.state == "RECOVERING":
                health = record_block(
                    health,
                    http_status=status,
                    cooldown_sec=cfg.source_cooldown_sec,
                    reason="RECOVERING_PROBE_FAIL",
                )
                report.stopped_block = True
                save_health(cfg.health_path, health)
                report.fetch_failed += 1
                log(f"[w2-haron] RECOVERING probe failed - BLOCKED")
                break
            save_health(cfg.health_path, health)
            report.fetch_failed += 1
            consecutive_failures += 1
            if consecutive_failures >= cfg.max_consecutive_failures:
                report.stopped_consecutive = True
                log("[w2-haron] stop: max consecutive failures")
                break
            continue
        except Exception as exc:  # noqa: BLE001 - persist & continue bounded
            next_at = _iso(
                _utc_now() + timedelta(seconds=cfg.fetch_failed_cooldown_sec)
            )
            mark_row(
                row,
                status="fetch_failed",
                error_code=type(exc).__name__,
                error_reason=str(exc)[:300],
                next_eligible_at=next_at,
                bump_attempt=True,
            )
            report.fetch_failed += 1
            report.errors.append(f"{rid}: {type(exc).__name__}")
            consecutive_failures += 1
            if consecutive_failures >= cfg.max_consecutive_failures:
                report.stopped_consecutive = True
                break
            continue

        # Persist RAW HTML under Layer-B (not Feature).
        raw_path = cfg.raw_dir / f"{rid}.html"
        raw_path.write_text(html, encoding="utf-8")
        parsed = parse_haron(html)
        parsed_path = cfg.parsed_dir / f"{rid}.json"
        parsed_path.write_text(
            json.dumps(
                {
                    "history_race_id": rid,
                    "source": SOURCE_NAME,
                    "parser_version": PARSER_VERSION,
                    "retrieved_at": _iso(),
                    "parse": parsed,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        if parsed.get("parse_ok"):
            mark_row(
                row,
                status="cache_hit",
                raw_html_path=str(raw_path),
                raw_haron_present=True,
                parsed_haron_present=True,
                sectional_sequence=parsed.get("sectional") or parsed.get("cumulative"),
                retrieved=True,
            )
            row["refetch_prohibited"] = True
            row["error_code"] = None
            row["error_reason"] = None
            health = record_success(health)
            save_health(cfg.health_path, health)
            report.success_cache_hit += 1
            consecutive_failures = 0
        elif not parsed.get("haron_exists"):
            mark_row(
                row,
                status="source_missing",
                raw_html_path=str(raw_path),
                raw_haron_present=False,
                parsed_haron_present=False,
                error_code="NO_HARON_TABLE",
                error_reason=parsed.get("malformed_reason") or "no_haron",
                retrieved=True,
            )
            health = record_success(health)  # page OK
            save_health(cfg.health_path, health)
            report.source_missing += 1
            consecutive_failures = 0
        else:
            mark_row(
                row,
                status="parse_failed",
                raw_html_path=str(raw_path),
                raw_haron_present=True,
                parsed_haron_present=False,
                error_code="PARSE_FAILED",
                error_reason=parsed.get("malformed_reason"),
                retrieved=True,
            )
            health = record_success(health)
            save_health(cfg.health_path, health)
            report.parse_failed += 1
            consecutive_failures = 0

        # Persist after each race for resume safety.
        save_index(cfg.index_path, rows)

        if report.requested >= cfg.max_races_per_run:
            report.stopped_budget = True
            break

    report.index_rows = len(rows)
    report.source_health_state = health.state
    report.p1_state = read_p1_lock(cfg.lock_path).state
    report.pending_remaining = sum(
        1 for r in rows.values() if r.get("canonical_status") == "pending"
    )
    report.finished_at = _iso()
    report.finalize_stop_reason()
    save_index(cfg.index_path, rows)
    save_health(cfg.health_path, health)
    _write_run_report(cfg, report)
    log(
        f"[w2-haron] done requested={report.requested} http={report.http_request_count} "
        f"hit={report.success_cache_hit} blocked={report.blocked} health={health.state} "
        f"stop={report.stop_reason}"
    )
    return report


def _write_run_report(cfg: W2Config, report: RunReport) -> Path:
    report.finalize_stop_reason()
    cfg.runs_dir.mkdir(parents=True, exist_ok=True)
    name = f"w2_run_{report.started_at.replace(':', '').replace('-', '')}.json"
    path = cfg.runs_dir / name
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    latest = cfg.runs_dir / "latest.json"
    latest.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
