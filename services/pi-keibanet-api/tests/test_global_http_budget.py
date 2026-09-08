# -*- coding: utf-8 -*-
"""Process-shared Global HTTP budget tests. External HTTP is forbidden."""
from __future__ import annotations

import compileall
import importlib.util
import io
import json
import multiprocessing as mp
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.http_budget import (
    BudgetDenied,
    reserve,
    window_usage,
)
from pi_keibanet.http_budget.audit import (
    BUDGETED_FUNCTIONS,
    DIRECT_NETKEIBA_PROBES,
    INTERNAL_API_ONLY,
    NON_NETKEIBA_HTTP,
    UNBUDGETED_NETKEIBA_PATHS,
    WIN5_NETKEIBA_BUDGETED,
)
from pi_keibanet.http_budget.store import bootstrap, open_store
from pi_keibanet.netkeiba.client import NetkeibaClient, NetkeibaFetchError
from pi_keibanet.w3_maiden.acquisition import run_w3c_acquire
from pi_keibanet.w3_maiden.config import W3AConfig
from pi_keibanet.w3_maiden.queue import empty_row as w3_empty_row
from pi_keibanet.w3_maiden.queue import save_queue as w3_save_queue


def _pending_w3(race_id: str, kaisai_date: str = "2025-06-01") -> dict:
    return w3_empty_row(
        race_id=race_id,
        kaisai_date=kaisai_date,
        venue="東京",
        race_number=1,
        race_name="3歳未勝利",
        c4_day_status="race_day_complete",
        maiden_identification_basis="race_name_contains_literal_maiden",
        source="fixture",
        source_artifact_ref="fixture",
        queue_status="pending",
    )
from pi_keibanet.w5_maiden_history.acquisition import run_w5_acquire
from pi_keibanet.w5_maiden_history.config import W5Config
from pi_keibanet.w5_maiden_history.queue import empty_row as w5_empty_row
from pi_keibanet.w5_maiden_history.queue import save_queue as w5_save_queue
from pi_keibanet.c4_calendar.config import C4Config
from pi_keibanet.c4_calendar.runner import run_c4_shadow
from pi_keibanet.w2_haron.config import W2Config
from pi_keibanet.w2_haron.layer_b_store import empty_row as w2_empty_row
from pi_keibanet.w2_haron.layer_b_store import save_index as w2_save_index
from pi_keibanet.w2_haron.runner import run_w2_shadow
from pi_keibanet.w4_horse.acquisition import run_w4cd_acquire
from pi_keibanet.w4_horse.config import W4Config
from pi_keibanet.w4_horse.queue import empty_row as w4_empty_row
from pi_keibanet.w4_horse.queue import save_queue as w4_save_queue

EXTERNAL_HTTP_CALLS = 0
SOCKET_CALLS = 0
URLOPEN_CALLS = 0


def _count_external(*_a, **_k):
    global EXTERNAL_HTTP_CALLS, URLOPEN_CALLS
    EXTERNAL_HTTP_CALLS += 1
    URLOPEN_CALLS += 1
    raise AssertionError("external HTTP is forbidden")


def _count_socket(*_a, **_k):
    global SOCKET_CALLS
    SOCKET_CALLS += 1
    raise AssertionError("socket is forbidden in budget tests")


def _load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _FakeResp:
    def __init__(self, body: bytes = b"<html>ok</html>", code: int = 200) -> None:
        self._body = body
        self.code = code

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *_a) -> None:
        return None


class CountingOpener:
    def __init__(self, exc: BaseException | None = None, body: bytes = b"<html>ok</html>") -> None:
        self.calls = 0
        self.exc = exc
        self.body = body
        self.reserved_before: list[bool] = []

    def __call__(self, *_a, **_k):
        self.calls += 1
        if self.exc is not None:
            raise self.exc
        return _FakeResp(self.body)


def _staging_env(state: Path, **overrides: str) -> dict[str, str]:
    env = {
        "GLOBAL_HTTP_BUDGET_MODE": "enforce",
        "GLOBAL_HTTP_BUDGET_BOOTSTRAP": "1",
        "GLOBAL_HTTP_BUDGET_STATE_PATH": str(state),
        "GLOBAL_HTTP_BUDGET_TOTAL_LIMIT": "8",
        "GLOBAL_HTTP_BUDGET_RESERVED_P1_C4": "3",
        "GLOBAL_HTTP_BUDGET_RESERVED_WIN5_RESULTS": "0",
        "GLOBAL_HTTP_BUDGET_LIMIT_P1": "5",
        "GLOBAL_HTTP_BUDGET_LIMIT_C4": "3",
        "GLOBAL_HTTP_BUDGET_LIMIT_W2": "2",
        "GLOBAL_HTTP_BUDGET_LIMIT_W3C": "2",
        "GLOBAL_HTTP_BUDGET_LIMIT_W4": "2",
        "GLOBAL_HTTP_BUDGET_LIMIT_W5": "2",
        "GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESULTS": "2",
        "GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESEARCH": "2",
        "GLOBAL_HTTP_BUDGET_LIMIT_UNKNOWN": "1",
        "GLOBAL_HTTP_BUDGET_SHORT_WINDOW_SEC": "0",
        "GLOBAL_HTTP_BUDGET_SHORT_LIMIT": "0",
        "GLOBAL_HTTP_BUDGET_SHORT_LIMIT_HOST": "0",
        "GLOBAL_HTTP_BUDGET_BUSY_TIMEOUT_MS": "500",
        "W3W5_LIVE_HTTP": "0",
        "W3A_BEFORE_W3C": "0",
        "W3A_HANDOFF_DRY_RUN": "1",
    }
    env.update(overrides)
    return env


@contextmanager
def _budget_env(state: Path, **overrides: str):
    applied = _staging_env(state, **overrides)
    old = {key: os.environ.get(key) for key in applied}
    os.environ.update(applied)
    try:
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _url(component: str = "p1") -> str:
    return f"https://race.netkeiba.com/race/result.html?race_id={component}secret=token"


def _mp_reserve_one(payload: tuple[str, str, str]) -> str:
    state_path, component, total = payload
    os.environ["GLOBAL_HTTP_BUDGET_MODE"] = "enforce"
    os.environ["GLOBAL_HTTP_BUDGET_BOOTSTRAP"] = "0"
    os.environ["GLOBAL_HTTP_BUDGET_STATE_PATH"] = state_path
    os.environ["GLOBAL_HTTP_BUDGET_TOTAL_LIMIT"] = total
    os.environ["GLOBAL_HTTP_BUDGET_RESERVED_P1_C4"] = "0"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_P1"] = total
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_C4"] = total
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_W2"] = total
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_W3C"] = total
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_W4"] = total
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_W5"] = total
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESULTS"] = total
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESEARCH"] = total
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_UNKNOWN"] = total
    os.environ["GLOBAL_HTTP_BUDGET_SHORT_WINDOW_SEC"] = "0"
    os.environ["GLOBAL_HTTP_BUDGET_SHORT_LIMIT"] = "0"
    os.environ["GLOBAL_HTTP_BUDGET_SHORT_LIMIT_HOST"] = "0"
    os.environ["GLOBAL_HTTP_BUDGET_BUSY_TIMEOUT_MS"] = "5000"
    sys.path.insert(0, str(ROOT))
    from pi_keibanet.http_budget import BudgetDenied, reserve

    try:
        reserve(url="https://race.netkeiba.com/race/result.html", component=component)
        return "ok"
    except BudgetDenied as exc:
        return exc.reason


def _w3_cfg(tmp: Path, **kwargs) -> W3AConfig:
    dummy = tmp / "dummy"
    dummy.mkdir(parents=True, exist_ok=True)
    data = tmp / "data"
    cfg = W3AConfig(
        data_root=data,
        w3_root=data / "var" / "w3_maiden",
        race_refresh_state_root=data / "var" / "race_refresh",
        c4_queue_path=data / "var" / "c4_calendar" / "calendar_queue.jsonl",
        hbf_cache_root=dummy,
        extsrc_cache_root=dummy,
        w2_raw_root=dummy,
        p1_lock_path=data / "var" / "locks" / "p1_refresh.lock.json",
        page_c_health_path=data / "var" / "layer_b_haron" / "source_health_netkeiba_page_c.json",
        w3c_fetch_enabled=True,
        w3c_dry_run=False,
        max_races_per_run=2,
        max_requests_per_run=2,
        min_interval_sec=0,
    )
    for key, value in kwargs.items():
        setattr(cfg, key, value)
    return cfg


def _c4_cfg(tmp: Path) -> C4Config:
    data = tmp / "data"
    dummy = tmp / "dummy"
    dummy.mkdir(parents=True, exist_ok=True)
    return C4Config(
        data_root=data,
        c4_root=data / "var" / "c4_calendar",
        lock_path=data / "var" / "locks" / "p1_refresh.lock.json",
        race_refresh_state_root=data / "var" / "race_refresh",
        known_dates_path=dummy / "known.jsonl",
        domain_halt_path=data / "var" / "locks" / "netkeiba_domain_halt.json",
        universe_start="2025-06-01",
        universe_as_of="2025-06-01",
        max_dates_per_run=1,
        max_requests_per_run=2,
        min_interval_sec=0,
        fetch_enabled=True,
        dry_run=False,
        enabled=True,
    )


def _w2_cfg(tmp: Path) -> W2Config:
    data = tmp / "data"
    dummy = tmp / "dummy"
    dummy.mkdir(parents=True, exist_ok=True)
    return W2Config(
        data_root=data,
        layer_b_root=data / "var" / "layer_b_haron",
        lock_path=data / "var" / "locks" / "p1_refresh.lock.json",
        race_refresh_state_root=data / "var" / "race_refresh",
        seal_index_path=dummy / "no-seal.jsonl",
        hbf_cache_root=dummy / "hbf",
        extsrc_cache_root=dummy / "extsrc",
        max_races_per_run=1,
        min_interval_sec=0,
        fetch_enabled=True,
        dry_run=False,
        enabled=True,
    )


def _w4_cfg(tmp: Path) -> W4Config:
    data = tmp / "data"
    dummy = tmp / "dummy"
    dummy.mkdir(parents=True, exist_ok=True)
    return W4Config(
        data_root=data,
        w4_root=data / "var" / "w4_horse",
        w3_root=data / "var" / "w3_maiden",
        d1_cache_roots=[dummy / "d1"],
        d2_cache_roots=[dummy / "d2"],
        p1_lock_path=data / "var" / "locks" / "p1_refresh.lock.json",
        db_horse_health_path=data / "var" / "w4_horse" / "source_health_netkeiba_db_horse.json",
        w4cd_enabled=True,
        w4cd_fetch_enabled=True,
        w4cd_dry_run=False,
        max_horses_per_run=1,
        max_requests_per_run=2,
        min_interval_sec=0,
    )


def _mp_short_reserved(payload: tuple[str, str]) -> str:
    state_path, component = payload
    os.environ["GLOBAL_HTTP_BUDGET_MODE"] = "enforce"
    os.environ["GLOBAL_HTTP_BUDGET_BOOTSTRAP"] = "0"
    os.environ["GLOBAL_HTTP_BUDGET_STATE_PATH"] = state_path
    os.environ["GLOBAL_HTTP_BUDGET_TOTAL_LIMIT"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_RESERVED_P1_C4"] = "2"
    os.environ["GLOBAL_HTTP_BUDGET_RESERVED_WIN5_RESULTS"] = "2"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_P1"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_C4"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_W2"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_W3C"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_W4"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_W5"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESULTS"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESEARCH"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_UNKNOWN"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_SHORT_WINDOW_SEC"] = "120"
    os.environ["GLOBAL_HTTP_BUDGET_SHORT_LIMIT"] = "6"
    os.environ["GLOBAL_HTTP_BUDGET_SHORT_LIMIT_HOST"] = "0"
    os.environ["GLOBAL_HTTP_BUDGET_BUSY_TIMEOUT_MS"] = "5000"
    sys.path.insert(0, str(ROOT))
    from pi_keibanet.http_budget import BudgetDenied, reserve

    try:
        reserve(url="https://race.netkeiba.com/race/result.html", component=component)
        return f"ok:{component}"
    except BudgetDenied as exc:
        return f"{exc.reason}:{component}"


def _secret_urls() -> tuple[str, ...]:
    return (
        "https://race.netkeiba.com/race/result.html?token=secret",
        "https://race.netkeiba.com/race/result.html?race_id=202506010101",
        "https://race.netkeiba.com/race/result.html#fragment",
        "https://user:pass@race.netkeiba.com/race/result.html?token=secret&race_id=202506010101#fragment",
    )


def _assert_no_query_secret(text: str) -> None:
    lowered = (text or "").lower()
    for banned in (
        "token=secret",
        "token=",
        "?race_id=",
        "race_id=202506010101",
        "#fragment",
        "fragment",
        "user:pass",
        "user:pass@",
        "secret",
    ):
        if banned in lowered:
            raise AssertionError(f"secret leaked: {banned!r} in {text!r}")
    if "?" in (text or "") or "#" in (text or ""):
        raise AssertionError(f"query/fragment leaked: {text!r}")


def _c0_tip() -> str:
    for ref in (
        "origin/cursor/c4-w2-w4-runtime-baseline-22d3",
        "cursor/c4-w2-w4-runtime-baseline-22d3",
    ):
        proc = subprocess.run(
            ["git", "rev-parse", "--verify", ref],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    return "HEAD~1"


def _mp_short_reserve(payload: tuple[str]) -> str:
    state_path = payload[0]
    os.environ["GLOBAL_HTTP_BUDGET_MODE"] = "enforce"
    os.environ["GLOBAL_HTTP_BUDGET_BOOTSTRAP"] = "0"
    os.environ["GLOBAL_HTTP_BUDGET_STATE_PATH"] = state_path
    os.environ["GLOBAL_HTTP_BUDGET_TOTAL_LIMIT"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_RESERVED_P1_C4"] = "0"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_P1"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_C4"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_W2"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_W3C"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_W4"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_W5"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESULTS"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESEARCH"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_LIMIT_UNKNOWN"] = "20"
    os.environ["GLOBAL_HTTP_BUDGET_SHORT_WINDOW_SEC"] = "120"
    os.environ["GLOBAL_HTTP_BUDGET_SHORT_LIMIT"] = "3"
    os.environ["GLOBAL_HTTP_BUDGET_SHORT_LIMIT_HOST"] = "0"
    os.environ["GLOBAL_HTTP_BUDGET_BUSY_TIMEOUT_MS"] = "5000"
    sys.path.insert(0, str(ROOT))
    from pi_keibanet.http_budget import BudgetDenied, reserve

    try:
        reserve(url="https://race.netkeiba.com/race/result.html", component="p1")
        return "ok"
    except BudgetDenied as exc:
        return exc.reason


def _w5_cfg(tmp: Path, **kwargs) -> W5Config:
    data = tmp / "data"
    cfg = W5Config(
        data_root=data,
        w5_root=data / "var" / "w5_maiden_history",
        w3_root=data / "var" / "w3_maiden",
        p1_lock_path=data / "var" / "locks" / "p1_refresh.lock.json",
        health_path=data / "var" / "w5_maiden_history" / "source_health_netkeiba_horse_history.json",
        fetch_enabled=True,
        dry_run=False,
        max_horses_per_run=2,
        max_requests_per_run=4,
        min_interval_sec=0,
    )
    for key, value in kwargs.items():
        setattr(cfg, key, value)
    return cfg


class GlobalHttpBudgetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ghb-"))
        self.state = self.tmp / "budget.sqlite"
        self.urlopen_patch = patch("urllib.request.urlopen", side_effect=_count_external)
        self.socket_patch = patch("socket.create_connection", side_effect=_count_socket)
        self.urlopen_patch.start()
        self.socket_patch.start()

    def tearDown(self) -> None:
        self.urlopen_patch.stop()
        self.socket_patch.stop()

    def test_audit_lists_real_budgeted_and_unbudgeted_paths(self) -> None:
        text = (ROOT / "pi_keibanet" / "netkeiba" / "client.py").read_text(encoding="utf-8")
        self.assertIn("def fetch(", text)
        self.assertIn("def fetch_jra_odds_json(", text)
        self.assertIn("reserve_for_request", text)
        for name in BUDGETED_FUNCTIONS:
            self.assertIn("NetkeibaClient", name)
        self.assertEqual(UNBUDGETED_NETKEIBA_PATHS, ())
        for item in WIN5_NETKEIBA_BUDGETED:
            path = REPO / item.split(":")[0]
            self.assertTrue(path.is_file(), item)
            self.assertIn("reserve_win5", path.read_text(encoding="utf-8"))
        for rel in INTERNAL_API_ONLY:
            self.assertTrue((REPO / rel.split(":")[0]).is_file(), rel)
        for rel in NON_NETKEIBA_HTTP:
            self.assertTrue((REPO / rel).is_file(), rel)
            self.assertNotIn(rel, UNBUDGETED_NETKEIBA_PATHS)
        for rel in DIRECT_NETKEIBA_PROBES:
            self.assertTrue((REPO / rel).is_file(), rel)
            self.assertIn("budgeted_probe_client", (REPO / rel).read_text(encoding="utf-8"))
        self.assertFalse((ROOT / "scripts" / "w4_global_budget_deny_probe.py").exists())

    def test_multiprocess_reserve_never_exceeds_total(self) -> None:
        with _budget_env(self.state, GLOBAL_HTTP_BUDGET_TOTAL_LIMIT="5", GLOBAL_HTTP_BUDGET_LIMIT_P1="5"):
            from pi_keibanet.http_budget.config import load_budget_config

            bootstrap(load_budget_config())
            ctx = mp.get_context("fork")
            with ctx.Pool(8) as pool:
                results = pool.map(
                    _mp_reserve_one,
                    [(str(self.state), "p1", "5")] * 16,
                )
        self.assertEqual(results.count("ok"), 5)
        self.assertEqual(len(results) - results.count("ok"), 11)
        with _budget_env(self.state, GLOBAL_HTTP_BUDGET_BOOTSTRAP="0"):
            snap = window_usage()
        self.assertEqual(snap["total"], 5)

    def test_component_and_total_limits(self) -> None:
        with _budget_env(self.state):
            reserve(url=_url(), component="p1")
            reserve(url=_url(), component="p1")
            with self.assertRaises(BudgetDenied) as ctx:
                # p1 limit 5, but use w3c limit 2
                reserve(url=_url(), component="w3c")
                reserve(url=_url(), component="w3c")
                reserve(url=_url(), component="w3c")
            self.assertEqual(ctx.exception.reason, "component_limit")

    def test_p1_reserved_capacity_blocks_research(self) -> None:
        with _budget_env(
            self.state,
            GLOBAL_HTTP_BUDGET_TOTAL_LIMIT="5",
            GLOBAL_HTTP_BUDGET_RESERVED_P1_C4="3",
            GLOBAL_HTTP_BUDGET_LIMIT_W5="5",
            GLOBAL_HTTP_BUDGET_LIMIT_P1="5",
        ):
            reserve(url=_url(), component="w5")
            reserve(url=_url(), component="w5")
            with self.assertRaises(BudgetDenied) as denied:
                reserve(url=_url(), component="w5")
            self.assertEqual(denied.exception.reason, "reserved_capacity")
            reserve(url=_url(), component="p1")
            reserve(url=_url(), component="c4")
            reserve(url=_url(), component="p1")
            with self.assertRaises(BudgetDenied) as total:
                reserve(url=_url(), component="p1")
            self.assertEqual(total.exception.reason, "total_limit")
            snap = window_usage()
            self.assertEqual(snap["by_component"].get("w5"), 2)
            self.assertEqual(snap["by_component"].get("p1"), 2)
            self.assertEqual(snap["by_component"].get("c4"), 1)

    def test_research_cannot_consume_p1_reserve(self) -> None:
        with _budget_env(
            self.state,
            GLOBAL_HTTP_BUDGET_TOTAL_LIMIT="4",
            GLOBAL_HTTP_BUDGET_RESERVED_P1_C4="3",
            GLOBAL_HTTP_BUDGET_LIMIT_W4="4",
            GLOBAL_HTTP_BUDGET_LIMIT_W3C="4",
            GLOBAL_HTTP_BUDGET_LIMIT_W2="4",
        ):
            reserve(url=_url(), component="w2")
            for component in ("w3c", "w4", "w5"):
                with self.assertRaises(BudgetDenied) as ctx:
                    reserve(url=_url(), component=component)
                self.assertEqual(ctx.exception.reason, "reserved_capacity")
            reserve(url=_url(), component="p1")
            snap = window_usage()
            self.assertEqual(snap["by_component"].get("p1"), 1)
            self.assertNotIn("w3c", snap["by_component"])
            self.assertNotIn("w4", snap["by_component"])
            self.assertNotIn("w5", snap["by_component"])

    def test_missing_state_research_fail_closed(self) -> None:
        missing = self.tmp / "no-such" / "budget.sqlite"
        with _budget_env(missing, GLOBAL_HTTP_BUDGET_BOOTSTRAP="0"):
            for component in ("w2", "w3c", "w4", "w5"):
                with self.assertRaises(BudgetDenied) as ctx:
                    reserve(url=_url(), component=component)
                self.assertEqual(ctx.exception.reason, "missing_state")

    def test_corrupt_state_fail_closed(self) -> None:
        self.state.write_text("not-a-sqlite-file", encoding="utf-8")
        with _budget_env(self.state, GLOBAL_HTTP_BUDGET_BOOTSTRAP="0"):
            with self.assertRaises(BudgetDenied) as ctx:
                reserve(url=_url(), component="p1")
            self.assertEqual(ctx.exception.reason, "corrupt_state")
            with self.assertRaises(BudgetDenied) as research:
                reserve(url=_url(), component="w5")
            self.assertEqual(research.exception.reason, "corrupt_state")

    def test_sqlite_busy_timeout_fail_closed(self) -> None:
        with _budget_env(self.state, GLOBAL_HTTP_BUDGET_BUSY_TIMEOUT_MS="200"):
            from pi_keibanet.http_budget.config import load_budget_config

            cfg = load_budget_config()
            bootstrap(cfg)
            holder = sqlite3.connect(str(self.state), timeout=0, isolation_level=None)
            holder.execute("BEGIN IMMEDIATE")
            try:
                with self.assertRaises(BudgetDenied) as ctx:
                    reserve(url=_url(), component="p1")
                self.assertEqual(ctx.exception.reason, "busy_timeout")
            finally:
                holder.execute("ROLLBACK")
                holder.close()

    def test_crash_after_reserve_still_consumed(self) -> None:
        with _budget_env(self.state, GLOBAL_HTTP_BUDGET_TOTAL_LIMIT="1", GLOBAL_HTTP_BUDGET_LIMIT_P1="1"):
            first = reserve(url=_url(), component="p1")
            self.assertEqual(first.consumed, True)
            with self.assertRaises(BudgetDenied) as ctx:
                reserve(url=_url(), component="p1")
            self.assertEqual(ctx.exception.reason, "total_limit")
            snap = window_usage()
            self.assertEqual(snap["total"], 1)

    def test_utc_window_boundary(self) -> None:
        before = datetime(2026, 9, 7, 23, 59, 59, tzinfo=timezone.utc)
        after = datetime(2026, 9, 8, 0, 0, 1, tzinfo=timezone.utc)
        with _budget_env(self.state, GLOBAL_HTTP_BUDGET_TOTAL_LIMIT="1", GLOBAL_HTTP_BUDGET_LIMIT_P1="1"):
            reserve(url=_url(), component="p1", now=before)
            with self.assertRaises(BudgetDenied):
                reserve(url=_url(), component="p1", now=before)
            reserve(url=_url(), component="p1", now=after)
            self.assertEqual(window_usage(now=before)["total"], 1)
            self.assertEqual(window_usage(now=after)["total"], 1)

    def test_http_errors_and_timeout_consume(self) -> None:
        cases = (
            (urllib.error.HTTPError(_url(), 403, "no", hdrs=None, fp=io.BytesIO()), "http_403", 403),
            (urllib.error.HTTPError(_url(), 429, "slow", hdrs=None, fp=io.BytesIO()), "http_429", 429),
            (urllib.error.HTTPError(_url(), 500, "err", hdrs=None, fp=io.BytesIO()), "http_5xx", 500),
            (urllib.error.URLError(TimeoutError("timed out")), "timeout", None),
        )
        with _budget_env(self.state, GLOBAL_HTTP_BUDGET_TOTAL_LIMIT="8", GLOBAL_HTTP_BUDGET_LIMIT_P1="8"):
            for exc, result, status in cases:
                opener = CountingOpener(exc=exc)
                client = NetkeibaClient(min_interval_sec=0, opener=opener, component="p1")
                with self.assertRaises(NetkeibaFetchError):
                    client.fetch("https://race.netkeiba.com/race/result.html")
                self.assertEqual(opener.calls, 1)
            snap = window_usage()
            self.assertEqual(snap["total"], 4)
            conn = sqlite3.connect(str(self.state))
            rows = conn.execute("SELECT result, http_status FROM reservations ORDER BY reserved_at").fetchall()
            conn.close()
            self.assertEqual([r[0] for r in rows], ["http_403", "http_429", "http_5xx", "timeout"])
            self.assertEqual([r[1] for r in rows], [403, 429, 500, None])

    def test_reserve_happens_before_opener(self) -> None:
        seen = {"reserved": False}

        def opener(*_a, **_k):
            snap = window_usage()
            seen["reserved"] = snap["total"] == 1
            return _FakeResp()

        with _budget_env(self.state):
            client = NetkeibaClient(min_interval_sec=0, opener=opener, component="p1")
            html = client.fetch("https://race.netkeiba.com/top/race_list_sub.html")
        self.assertTrue(seen["reserved"])
        self.assertIn("ok", html)

    def test_deny_means_zero_http(self) -> None:
        opener = CountingOpener()
        missing = self.tmp / "absent.sqlite"
        with _budget_env(missing, GLOBAL_HTTP_BUDGET_BOOTSTRAP="0"):
            client = NetkeibaClient(min_interval_sec=0, opener=opener, component="w5")
            with self.assertRaises(BudgetDenied):
                client.fetch("https://db.netkeiba.com/horse/ajax_horse_results.html")
        self.assertEqual(opener.calls, 0)

    def test_w3c_runner_deny_exit_and_report(self) -> None:
        cfg = _w3_cfg(self.tmp)
        rid = "202506010101"
        cfg.w3_root.mkdir(parents=True, exist_ok=True)
        w3_save_queue(cfg.queue_path, {rid: _pending_w3(rid)})
        opener = CountingOpener()
        client = NetkeibaClient(min_interval_sec=0, opener=opener, component="w3c")
        missing = self.tmp / "missing-w3c.sqlite"
        with _budget_env(missing, GLOBAL_HTTP_BUDGET_BOOTSTRAP="0"):
            report = run_w3c_acquire(cfg, client=client)
        self.assertTrue(report.stopped_global_budget)
        self.assertEqual(report.global_budget_reason, "missing_state")
        self.assertEqual(report.http_request_count, 0)
        self.assertEqual(report.stop_reason, "global_http_budget")
        self.assertEqual(opener.calls, 0)
        runner = _load_script("w3_maiden_page_c_acquire_run.py")
        with patch.object(runner, "W3AConfig") as cfg_cls, patch.object(
            runner, "run_w3c_acquire", return_value=report
        ), patch.object(runner, "_unit_busy", return_value=False), patch.object(
            sys, "argv", ["w3c", "--data-root", str(cfg.data_root)]
        ):
            cfg_cls.from_env.return_value = cfg
            self.assertEqual(runner.main(), 5)

    def test_w5_runner_deny_exit_and_report(self) -> None:
        cfg = _w5_cfg(self.tmp)
        hid = "2021107235"
        cfg.w5_root.mkdir(parents=True, exist_ok=True)
        w5_save_queue(cfg.queue_path, {hid: w5_empty_row(horse_id=hid, source="fixture")})
        opener = CountingOpener()
        client = NetkeibaClient(min_interval_sec=0, opener=opener, component="w5")
        missing = self.tmp / "missing-w5.sqlite"
        with _budget_env(missing, GLOBAL_HTTP_BUDGET_BOOTSTRAP="0"):
            report = run_w5_acquire(cfg, client=client)
        self.assertTrue(report.stopped_global_budget)
        self.assertEqual(report.http_request_count, 0)
        self.assertEqual(opener.calls, 0)
        runner = _load_script("w5_maiden_history_acquire_run.py")
        from pi_keibanet.w5_maiden_history.gate_monitor import GateMonitorState

        gate = GateMonitorState(reevaluation_ready=False)
        with patch.object(runner, "W5Config") as cfg_cls, patch.object(
            runner, "run_w5_acquire", return_value=report
        ), patch.object(runner, "run_w5_handoff"), patch.object(
            runner, "update_gate_monitor", return_value=gate
        ), patch.object(runner, "_busy", return_value=False), patch.object(
            sys, "argv", ["w5", "--data-root", str(cfg.data_root)]
        ):
            cfg_cls.from_env.return_value = cfg
            self.assertEqual(runner.main(), 5)

    def test_real_c4_w2_w4_runner_deny_http_zero(self) -> None:
        missing = self.tmp / "missing-runners.sqlite"
        opener = CountingOpener()
        c4 = _c4_cfg(self.tmp)
        w2 = _w2_cfg(self.tmp)
        w4 = _w4_cfg(self.tmp)
        w2_save_index(w2.index_path, {"202506010101": w2_empty_row("202506010101")})
        w4.w4_root.mkdir(parents=True, exist_ok=True)
        w4_save_queue(
            w4.queue_path,
            {
                "2021107235": w4_empty_row(
                    horse_id="2021107235",
                    horse_id_raw="2021107235",
                    horse_id_format="netkeiba_10digit",
                    first_seen_race_id="202506010101",
                    first_seen_at="2025-06-01T00:00:00Z",
                )
            },
        )
        with _budget_env(missing, GLOBAL_HTTP_BUDGET_BOOTSTRAP="0"):
            c4_report = run_c4_shadow(
                c4,
                client=NetkeibaClient(min_interval_sec=0, opener=opener, component="c4"),
            )
            w2_report = run_w2_shadow(
                w2,
                client=NetkeibaClient(min_interval_sec=0, opener=opener, component="w2"),
            )
            w4_report = run_w4cd_acquire(
                w4,
                client=NetkeibaClient(min_interval_sec=0, opener=opener, component="w4"),
                horse_ids=["2021107235"],
            )
        self.assertTrue(c4_report.stopped_global_budget)
        self.assertTrue(w2_report.stopped_global_budget)
        self.assertTrue(w4_report.stopped_global_budget)
        self.assertEqual(c4_report.http_request_count, 0)
        self.assertEqual(w2_report.http_request_count, 0)
        self.assertEqual(w4_report.http_request_count, 0)
        self.assertEqual(opener.calls, 0)
        c4_script = _load_script("c4_calendar_shadow_run.py")
        w2_script = _load_script("w2_haron_shadow_run.py")
        w4_script = _load_script("w4_horse_d1d2_acquire_run.py")
        with patch.object(c4_script, "C4Config") as c4_cls, patch.object(
            c4_script, "run_c4_shadow", return_value=c4_report
        ), patch.object(c4_script, "_w2_service_busy", return_value=False), patch.object(
            sys, "argv", ["c4", "--data-root", str(c4.data_root)]
        ):
            c4_cls.from_env.return_value = c4
            self.assertEqual(c4_script.main(), 5)
        with patch.object(w2_script, "W2Config") as w2_cls, patch.object(
            w2_script, "run_w2_shadow", return_value=w2_report
        ), patch.object(sys, "argv", ["w2", "--data-root", str(w2.data_root)]):
            w2_cls.from_env.return_value = w2
            self.assertEqual(w2_script.main(), 5)
        with patch.object(w4_script, "W4Config") as w4_cls, patch.object(
            w4_script, "run_w4cd_acquire", return_value=w4_report
        ), patch.object(w4_script, "_unit_busy", return_value=False), patch.object(
            sys, "argv", ["w4", "--data-root", str(w4.data_root)]
        ):
            w4_cls.from_env.return_value = w4
            self.assertEqual(w4_script.main(), 5)

    def test_code_only_deploy_does_not_stop_p1(self) -> None:
        opener = CountingOpener()
        missing = self.tmp / "deploy-no-state.sqlite"
        old_mode = os.environ.pop("GLOBAL_HTTP_BUDGET_MODE", None)
        old_enabled = os.environ.pop("GLOBAL_HTTP_BUDGET_ENABLED", None)
        try:
            with _budget_env(
                missing,
                GLOBAL_HTTP_BUDGET_MODE="off",
                GLOBAL_HTTP_BUDGET_BOOTSTRAP="0",
            ):
                client = NetkeibaClient(min_interval_sec=0, opener=opener, component="p1")
                html = client.fetch("https://race.netkeiba.com/race/result.html")
            self.assertIn("ok", html)
            self.assertEqual(opener.calls, 1)
            self.assertEqual(os.environ.get("W3W5_LIVE_HTTP", "0"), "0")
        finally:
            if old_mode is not None:
                os.environ["GLOBAL_HTTP_BUDGET_MODE"] = old_mode
            if old_enabled is not None:
                os.environ["GLOBAL_HTTP_BUDGET_ENABLED"] = old_enabled

    def test_unset_mode_default_off_does_not_stop_p1(self) -> None:
        opener = CountingOpener()
        missing = self.tmp / "unset-mode.sqlite"
        applied = _staging_env(missing, GLOBAL_HTTP_BUDGET_BOOTSTRAP="0")
        applied.pop("GLOBAL_HTTP_BUDGET_MODE", None)
        old = {key: os.environ.get(key) for key in list(applied) + ["GLOBAL_HTTP_BUDGET_MODE"]}
        os.environ.pop("GLOBAL_HTTP_BUDGET_MODE", None)
        os.environ.update(applied)
        try:
            from pi_keibanet.http_budget.config import load_budget_config, resolve_mode

            self.assertEqual(resolve_mode(), "off")
            self.assertEqual(load_budget_config().mode, "off")
            client = NetkeibaClient(min_interval_sec=0, opener=opener, component="p1")
            html = client.fetch("https://race.netkeiba.com/race/result.html")
            self.assertIn("ok", html)
            self.assertEqual(opener.calls, 1)
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_explicit_invalid_mode_fail_closed(self) -> None:
        from pi_keibanet.http_budget.config import load_budget_config, resolve_mode

        for raw in ("enfroce", "  please-enforce  ", "enforce-now", "ON"):
            opener = CountingOpener()
            state = self.tmp / f"invalid-{raw.strip()[:12]}.sqlite"
            with _budget_env(state, GLOBAL_HTTP_BUDGET_MODE=raw, GLOBAL_HTTP_BUDGET_BOOTSTRAP="1"):
                self.assertEqual(resolve_mode(raw), "invalid")
                self.assertEqual(resolve_mode(), "invalid")
                cfg = load_budget_config()
                self.assertEqual(cfg.mode, "invalid")
                self.assertIn("invalid_mode", cfg.mode_invalid_reason)
                client = NetkeibaClient(min_interval_sec=0, opener=opener, component="p1")
                with self.assertRaises(BudgetDenied) as ctx:
                    client.fetch("https://race.netkeiba.com/race/result.html")
                self.assertEqual(ctx.exception.reason, "invalid_mode")
                self.assertIn(raw.strip()[:64], ctx.exception.detail)
                conn = sqlite3.connect(str(state))
                rows = conn.execute("SELECT result, consumed FROM reservations").fetchall()
                conn.close()
                self.assertTrue(rows)
                self.assertTrue(str(rows[0][0]).startswith("invalid_mode:"))
                self.assertEqual(rows[0][1], 0)
            self.assertEqual(opener.calls, 0)

    def test_observe_audits_without_blocking(self) -> None:
        opener = CountingOpener()
        with _budget_env(
            self.state,
            GLOBAL_HTTP_BUDGET_MODE="observe",
            GLOBAL_HTTP_BUDGET_TOTAL_LIMIT="1",
            GLOBAL_HTTP_BUDGET_LIMIT_P1="1",
        ):
            client = NetkeibaClient(min_interval_sec=0, opener=opener, component="p1")
            client.fetch("https://race.netkeiba.com/race/result.html")
            client.fetch("https://race.netkeiba.com/race/shutuba.html")
            conn = sqlite3.connect(str(self.state))
            rows = conn.execute(
                "SELECT result, consumed FROM reservations ORDER BY reserved_at"
            ).fetchall()
            conn.close()
        self.assertEqual(opener.calls, 2)
        self.assertEqual(rows[0][1], 0)
        self.assertTrue(str(rows[1][0]).startswith("observe_would_"))

    def test_enforce_missing_and_corrupt_http_zero(self) -> None:
        opener = CountingOpener()
        missing = self.tmp / "enforce-missing.sqlite"
        with _budget_env(missing, GLOBAL_HTTP_BUDGET_BOOTSTRAP="0"):
            client = NetkeibaClient(min_interval_sec=0, opener=opener, component="p1")
            with self.assertRaises(BudgetDenied) as ctx:
                client.fetch("https://race.netkeiba.com/race/result.html")
            self.assertEqual(ctx.exception.reason, "missing_state")
        self.state.write_text("not-sqlite", encoding="utf-8")
        with _budget_env(self.state, GLOBAL_HTTP_BUDGET_BOOTSTRAP="0"):
            with self.assertRaises(BudgetDenied) as ctx:
                client.fetch("https://race.netkeiba.com/race/result.html")
            self.assertEqual(ctx.exception.reason, "corrupt_state")
        self.assertEqual(opener.calls, 0)

    def test_short_window_global_and_host_and_boundary(self) -> None:
        before = datetime(2026, 9, 7, 23, 59, 50, tzinfo=timezone.utc)
        after = datetime(2026, 9, 8, 0, 0, 10, tzinfo=timezone.utc)
        with _budget_env(
            self.state,
            GLOBAL_HTTP_BUDGET_TOTAL_LIMIT="10",
            GLOBAL_HTTP_BUDGET_LIMIT_P1="10",
            GLOBAL_HTTP_BUDGET_LIMIT_W5="10",
            GLOBAL_HTTP_BUDGET_SHORT_WINDOW_SEC="60",
            GLOBAL_HTTP_BUDGET_SHORT_LIMIT="2",
            GLOBAL_HTTP_BUDGET_SHORT_LIMIT_HOST="2",
            GLOBAL_HTTP_BUDGET_RESERVED_P1_C4="1",
        ):
            reserve(url="https://race.netkeiba.com/a", component="p1", now=before)
            reserve(url="https://db.netkeiba.com/b", component="p1", now=before)
            with self.assertRaises(BudgetDenied) as burst:
                reserve(url="https://race.netkeiba.com/c", component="p1", now=after)
            self.assertEqual(burst.exception.reason, "short_limit")
        with _budget_env(
            self.tmp / "host.sqlite",
            GLOBAL_HTTP_BUDGET_TOTAL_LIMIT="10",
            GLOBAL_HTTP_BUDGET_LIMIT_P1="10",
            GLOBAL_HTTP_BUDGET_SHORT_WINDOW_SEC="60",
            GLOBAL_HTTP_BUDGET_SHORT_LIMIT="8",
            GLOBAL_HTTP_BUDGET_SHORT_LIMIT_HOST="1",
        ):
            reserve(url="https://race.netkeiba.com/a", component="p1")
            with self.assertRaises(BudgetDenied) as host:
                reserve(url="https://race.netkeiba.com/b", component="p1")
            self.assertEqual(host.exception.reason, "short_limit_host")
            reserve(url="https://db.netkeiba.com/c", component="p1")

    def test_short_reserved_p1_does_not_consume_win5(self) -> None:
        with _budget_env(
            self.state,
            GLOBAL_HTTP_BUDGET_TOTAL_LIMIT="20",
            GLOBAL_HTTP_BUDGET_RESERVED_P1_C4="2",
            GLOBAL_HTTP_BUDGET_RESERVED_WIN5_RESULTS="2",
            GLOBAL_HTTP_BUDGET_LIMIT_P1="20",
            GLOBAL_HTTP_BUDGET_LIMIT_C4="20",
            GLOBAL_HTTP_BUDGET_LIMIT_W5="20",
            GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESULTS="20",
            GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESEARCH="20",
            GLOBAL_HTTP_BUDGET_SHORT_WINDOW_SEC="60",
            GLOBAL_HTTP_BUDGET_SHORT_LIMIT="6",
        ):
            for _ in range(4):
                reserve(url="https://race.netkeiba.com/p1", component="p1")
            with self.assertRaises(BudgetDenied) as p1_block:
                reserve(url="https://race.netkeiba.com/p1-extra", component="p1")
            self.assertEqual(p1_block.exception.reason, "short_reserved_capacity")
            with self.assertRaises(BudgetDenied) as research_block:
                reserve(url="https://race.netkeiba.com/research", component="win5_research")
            self.assertEqual(research_block.exception.reason, "short_reserved_capacity")
            reserve(url="https://race.netkeiba.com/win5-a", component="win5_results")
            reserve(url="https://race.netkeiba.com/win5-b", component="win5_results")
            with self.assertRaises(BudgetDenied) as total:
                reserve(url="https://race.netkeiba.com/win5-c", component="win5_results")
            self.assertEqual(total.exception.reason, "short_limit")
            snap = window_usage()
            self.assertEqual(snap["by_component"].get("p1"), 4)
            self.assertEqual(snap["by_component"].get("win5_results"), 2)
            self.assertNotIn("win5_research", snap["by_component"])
            self.assertEqual(snap["total"], 6)

    def test_short_reserved_win5_does_not_consume_p1(self) -> None:
        with _budget_env(
            self.state,
            GLOBAL_HTTP_BUDGET_TOTAL_LIMIT="20",
            GLOBAL_HTTP_BUDGET_RESERVED_P1_C4="2",
            GLOBAL_HTTP_BUDGET_RESERVED_WIN5_RESULTS="2",
            GLOBAL_HTTP_BUDGET_LIMIT_P1="20",
            GLOBAL_HTTP_BUDGET_LIMIT_C4="20",
            GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESULTS="20",
            GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESEARCH="20",
            GLOBAL_HTTP_BUDGET_SHORT_WINDOW_SEC="60",
            GLOBAL_HTTP_BUDGET_SHORT_LIMIT="6",
        ):
            for _ in range(4):
                reserve(url="https://race.netkeiba.com/win5", component="win5_results")
            with self.assertRaises(BudgetDenied) as win5_block:
                reserve(url="https://race.netkeiba.com/win5-extra", component="win5_results")
            self.assertEqual(win5_block.exception.reason, "short_reserved_capacity")
            with self.assertRaises(BudgetDenied) as research_block:
                reserve(url="https://race.netkeiba.com/research", component="w5")
            self.assertEqual(research_block.exception.reason, "short_reserved_capacity")
            reserve(url="https://race.netkeiba.com/p1-a", component="p1")
            reserve(url="https://race.netkeiba.com/c4-a", component="c4")
            with self.assertRaises(BudgetDenied) as total:
                reserve(url="https://race.netkeiba.com/p1-b", component="p1")
            self.assertEqual(total.exception.reason, "short_limit")
            snap = window_usage()
            self.assertEqual(snap["by_component"].get("win5_results"), 4)
            self.assertEqual(snap["by_component"].get("p1"), 1)
            self.assertEqual(snap["by_component"].get("c4"), 1)
            self.assertEqual(snap["total"], 6)

    def test_short_reserved_multiprocess(self) -> None:
        with _budget_env(
            self.state,
            GLOBAL_HTTP_BUDGET_TOTAL_LIMIT="20",
            GLOBAL_HTTP_BUDGET_RESERVED_P1_C4="2",
            GLOBAL_HTTP_BUDGET_RESERVED_WIN5_RESULTS="2",
            GLOBAL_HTTP_BUDGET_LIMIT_P1="20",
            GLOBAL_HTTP_BUDGET_LIMIT_C4="20",
            GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESULTS="20",
            GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESEARCH="20",
            GLOBAL_HTTP_BUDGET_SHORT_WINDOW_SEC="120",
            GLOBAL_HTTP_BUDGET_SHORT_LIMIT="6",
        ):
            from pi_keibanet.http_budget.config import load_budget_config

            bootstrap(load_budget_config())
            jobs = (
                [(str(self.state), "p1")] * 8
                + [(str(self.state), "c4")] * 8
                + [(str(self.state), "win5_results")] * 8
                + [(str(self.state), "win5_research")] * 8
            )
            ctx = mp.get_context("fork")
            with ctx.Pool(8) as pool:
                pool.map(_mp_short_reserved, jobs)
            snap = window_usage()
        p1c4 = int(snap["by_component"].get("p1", 0)) + int(snap["by_component"].get("c4", 0))
        win5 = int(snap["by_component"].get("win5_results", 0))
        research = int(snap["by_component"].get("win5_research", 0))
        self.assertLessEqual(snap["total"], 6)
        self.assertGreaterEqual(p1c4, 2)
        self.assertGreaterEqual(win5, 2)
        self.assertLessEqual(research, 2)

    def test_short_reserved_holds_across_rolling_boundary(self) -> None:
        first = datetime(2026, 9, 8, 0, 0, 0, tzinfo=timezone.utc)
        still = datetime(2026, 9, 8, 0, 0, 30, tzinfo=timezone.utc)
        after = datetime(2026, 9, 8, 0, 1, 35, tzinfo=timezone.utc)
        with _budget_env(
            self.state,
            GLOBAL_HTTP_BUDGET_TOTAL_LIMIT="20",
            GLOBAL_HTTP_BUDGET_RESERVED_P1_C4="2",
            GLOBAL_HTTP_BUDGET_RESERVED_WIN5_RESULTS="2",
            GLOBAL_HTTP_BUDGET_LIMIT_P1="20",
            GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESULTS="20",
            GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESEARCH="20",
            GLOBAL_HTTP_BUDGET_SHORT_WINDOW_SEC="60",
            GLOBAL_HTTP_BUDGET_SHORT_LIMIT="6",
        ):
            for _ in range(4):
                reserve(url="https://race.netkeiba.com/p1", component="p1", now=first)
            with self.assertRaises(BudgetDenied) as mid:
                reserve(url="https://race.netkeiba.com/p1", component="p1", now=still)
            self.assertEqual(mid.exception.reason, "short_reserved_capacity")
            reserve(url="https://race.netkeiba.com/win5-a", component="win5_results", now=still)
            reserve(url="https://race.netkeiba.com/win5-b", component="win5_results", now=still)
            with self.assertRaises(BudgetDenied) as research:
                reserve(url="https://race.netkeiba.com/r", component="win5_research", now=still)
            self.assertEqual(research.exception.reason, "short_limit")
            for _ in range(4):
                reserve(url="https://race.netkeiba.com/p1-next", component="p1", now=after)
            with self.assertRaises(BudgetDenied) as later:
                reserve(url="https://race.netkeiba.com/steal", component="p1", now=after)
            self.assertEqual(later.exception.reason, "short_reserved_capacity")
            reserve(url="https://race.netkeiba.com/win5-next-a", component="win5_results", now=after)
            reserve(url="https://race.netkeiba.com/win5-next-b", component="win5_results", now=after)

    def test_short_window_multiprocess(self) -> None:
        with _budget_env(
            self.state,
            GLOBAL_HTTP_BUDGET_TOTAL_LIMIT="20",
            GLOBAL_HTTP_BUDGET_LIMIT_P1="20",
            GLOBAL_HTTP_BUDGET_SHORT_WINDOW_SEC="120",
            GLOBAL_HTTP_BUDGET_SHORT_LIMIT="3",
        ):
            from pi_keibanet.http_budget.config import load_budget_config

            bootstrap(load_budget_config())
            ctx = mp.get_context("fork")
            with ctx.Pool(6) as pool:
                results = pool.map(_mp_short_reserve, [(str(self.state),)] * 10)
        self.assertEqual(results.count("ok"), 3)
        self.assertGreaterEqual(results.count("short_limit"), 1)

    def test_win5_netkeiba_paths_reserve(self) -> None:
        sys.path.insert(0, str(REPO / "services" / "win5-ai"))
        from app.ops.netkeiba_results import NetkeibaHttp
        from app.research.collector.netkeiba_client import ResearchNetkeibaClient
        from app.netkeiba_budget import BudgetDenied as Win5Denied

        opener = CountingOpener()
        missing = self.tmp / "win5-missing.sqlite"
        with _budget_env(missing, GLOBAL_HTTP_BUDGET_BOOTSTRAP="0"):
            http = NetkeibaHttp(min_interval_sec=0, opener=opener)
            with self.assertRaises(Win5Denied):
                http.fetch("https://race.netkeiba.com/race/result.html?race_id=1")
            with patch(
                "urllib.request.urlopen", side_effect=_count_external
            ), self.assertRaises(Win5Denied):
                ResearchNetkeibaClient(min_interval_sec=0).fetch(
                    "https://db.netkeiba.com/horse/2021107235/"
                )
        self.assertEqual(opener.calls, 0)

    def test_direct_probes_refused_in_production_and_default(self) -> None:
        env = os.environ.copy()
        env.update(_staging_env(self.state, GLOBAL_HTTP_BUDGET_MODE="off"))
        env["PYTHONPATH"] = str(ROOT) + (os.pathsep + env.get("PYTHONPATH", ""))
        env["EXPECT_PRODUCTION"] = "1"
        for script in ("probe_netkeiba_api.py", "probe_full_list.py", "verify_sub_list.py"):
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / script)],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(proc.returncode, 0, script)
            self.assertIn("probe refused", (proc.stdout + proc.stderr).lower())
        smoke = (ROOT / "scripts" / "prod_smoke.py").read_text(encoding="utf-8")
        self.assertIn("127.0.0.1:8081", smoke)
        self.assertNotIn("netkeiba.com", smoke)

    def test_live_http_default_still_blocks_even_with_budget(self) -> None:
        cfg = _w3_cfg(self.tmp, w3c_fetch_enabled=False)
        rid = "202506010102"
        cfg.w3_root.mkdir(parents=True, exist_ok=True)
        w3_save_queue(cfg.queue_path, {rid: _pending_w3(rid)})
        opener = CountingOpener()
        client = NetkeibaClient(min_interval_sec=0, opener=opener, component="w3c")
        with _budget_env(self.state):
            report = run_w3c_acquire(cfg, client=client)
        self.assertEqual(opener.calls, 0)
        self.assertEqual(report.http_request_count, 0)
        self.assertNotEqual(os.environ.get("W3W5_LIVE_HTTP", "0"), "1")

    def test_ledger_has_no_query_or_secrets(self) -> None:
        with _budget_env(self.state):
            reserve(url="https://race.netkeiba.com/api/api_get_jra_odds.html?race_id=1&token=secret", component="p1")
            conn = sqlite3.connect(str(self.state))
            row = conn.execute("SELECT host, path, source FROM reservations").fetchone()
            dumped = " ".join(str(cell) for cell in conn.execute("SELECT * FROM reservations").fetchone())
            conn.close()
        self.assertEqual(row[0], "race.netkeiba.com")
        self.assertEqual(row[1], "/api/api_get_jra_odds.html")
        self.assertEqual(row[2], "netkeiba")
        self.assertNotIn("token", row[1])
        self.assertNotIn("?", row[1])
        _assert_no_query_secret(dumped)

    def test_exceptions_and_logs_strip_query_userinfo_fragment(self) -> None:
        from pi_keibanet.http_budget.sanitize import public_url
        from pi_keibanet.netkeiba.debug_log import log_fetch

        sys.path.insert(0, str(REPO / "services" / "win5-ai"))
        from app.ops.netkeiba_results import NetkeibaHttp, NetkeibaResultError
        from app.research.collector.netkeiba_client import ResearchNetkeibaClient, ResearchNetkeibaError

        for url in _secret_urls():
            self.assertEqual(public_url(url), "https://race.netkeiba.com/race/result.html")
            opener = CountingOpener(
                exc=urllib.error.HTTPError(url, 404, "no", hdrs=None, fp=io.BytesIO())
            )
            with _budget_env(
                self.state,
                GLOBAL_HTTP_BUDGET_LIMIT_P1="20",
                GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESULTS="20",
                GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESEARCH="20",
                GLOBAL_HTTP_BUDGET_TOTAL_LIMIT="20",
            ):
                client = NetkeibaClient(min_interval_sec=0, opener=opener, component="p1")
                with self.assertRaises(NetkeibaFetchError) as pi_ctx:
                    client.fetch(url)
                _assert_no_query_secret(str(pi_ctx.exception))
                win5 = NetkeibaHttp(min_interval_sec=0, opener=opener)
                with self.assertRaises(NetkeibaResultError) as win5_ctx:
                    win5.fetch(url)
                _assert_no_query_secret(str(win5_ctx.exception))
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                log_fetch(url=url, html="<html></html>", label="unit")
            _assert_no_query_secret(buf.getvalue())
        self.urlopen_patch.stop()
        try:
            for url in _secret_urls():
                opener = CountingOpener(
                    exc=urllib.error.HTTPError(url, 404, "no", hdrs=None, fp=io.BytesIO())
                )
                with _budget_env(
                    self.state,
                    GLOBAL_HTTP_BUDGET_LIMIT_WIN5_RESEARCH="20",
                    GLOBAL_HTTP_BUDGET_TOTAL_LIMIT="20",
                ), patch("urllib.request.urlopen", opener):
                    with self.assertRaises(ResearchNetkeibaError) as research_ctx:
                        ResearchNetkeibaClient(min_interval_sec=0).fetch(url, label="token=secret")
                    _assert_no_query_secret(str(research_ctx.exception))
        finally:
            self.urlopen_patch.start()
        conn = sqlite3.connect(str(self.state))
        for row in conn.execute("SELECT host, path, source FROM reservations").fetchall():
            for cell in row:
                _assert_no_query_secret(str(cell))
        conn.close()

    def test_defaults_do_not_authorize_http(self) -> None:
        with _budget_env(
            self.state,
            GLOBAL_HTTP_BUDGET_TOTAL_LIMIT="0",
            GLOBAL_HTTP_BUDGET_RESERVED_P1_C4="0",
            GLOBAL_HTTP_BUDGET_LIMIT_P1="0",
        ):
            with self.assertRaises(BudgetDenied) as ctx:
                reserve(url=_url(), component="p1")
            self.assertEqual(ctx.exception.reason, "total_limit")

    def test_compileall_and_diff_check(self) -> None:
        gitattributes = "\n".join(
            line
            for line in (REPO / ".gitattributes").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        self.assertNotIn("whitespace=-trailing-space", gitattributes)
        self.assertNotIn("whitespace=-cr-at-eol", gitattributes)
        pkg = ROOT / "pi_keibanet" / "http_budget"
        self.assertTrue(compileall.compile_dir(str(pkg), quiet=1, force=True))
        self.assertTrue(compileall.compile_file(str(ROOT / "pi_keibanet" / "netkeiba" / "client.py"), quiet=1))
        dirty = subprocess.run(
            ["git", "diff", "--check"],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(dirty.returncode, 0, dirty.stdout + dirty.stderr)
        c0 = _c0_tip()
        ranged = subprocess.run(
            ["git", "diff", "--check", f"{c0}...HEAD"],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(ranged.returncode, 0, ranged.stdout + ranged.stderr)
        self.assertEqual((ranged.stdout + ranged.stderr).strip(), "")

    def test_external_http_remains_zero(self) -> None:
        self.assertEqual(EXTERNAL_HTTP_CALLS, 0)
        self.assertEqual(URLOPEN_CALLS, 0)
        self.assertEqual(SOCKET_CALLS, 0)


if __name__ == "__main__":
    unittest.main()
