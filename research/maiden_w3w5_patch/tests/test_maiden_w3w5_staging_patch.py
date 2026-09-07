# -*- coding: utf-8 -*-
"""Offline staging tests for the W3-A / W5 maiden patch (HTTP forbidden)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pi_keibanet.netkeiba.client import NetkeibaClient, NetkeibaFetchError
from pi_keibanet.w3_maiden.config import W3AConfig
from pi_keibanet.w3_maiden.handoff import run_w3a_handoff
from pi_keibanet.w3_maiden.queue import load_queue, save_queue
from pi_keibanet.w5_maiden_history.acquisition import (
    run_w5_acquire,
    select_eligible,
    select_pending,
)
from pi_keibanet.w5_maiden_history.config import W5Config
from pi_keibanet.w5_maiden_history.queue import (
    empty_row as w5_empty_row,
)
from pi_keibanet.w5_maiden_history.queue import (
    load_queue as w5_load_queue,
)
from pi_keibanet.w5_maiden_history.queue import (
    save_queue as w5_save_queue,
)

HTTP_CALLS = 0
EXISTING_W3 = 59
COMPLETE_W5 = 835
FAILED_W5 = ("2021107235", "2021107273", "2021100988")


def _forbid_http(*_a, **_k):
    global HTTP_CALLS
    HTTP_CALLS += 1
    raise AssertionError("HTTP is forbidden in staging tests")


def _load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ForbiddenClient(NetkeibaClient):
    def fetch(self, url: str, *, label: str = "netkeiba", accept: str | None = None) -> str:
        _forbid_http(url, label=label)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _w3_cfg(tmp: Path, **kwargs) -> W3AConfig:
    data = tmp / "data"
    dummy = tmp / "dummy"
    dummy.mkdir(parents=True, exist_ok=True)
    cfg = W3AConfig(
        data_root=data,
        w3_root=data / "var" / "w3_maiden",
        race_refresh_state_root=data / "var" / "race_refresh",
        c4_queue_path=data / "var" / "c4_calendar" / "calendar_queue.jsonl",
        hbf_cache_root=dummy,
        extsrc_cache_root=dummy,
        w2_raw_root=dummy,
        w3a_handoff_dry_run=True,
        w3a_max_enqueue_per_run=2,
        enabled=True,
        w3c_fetch_enabled=False,
    )
    for key, value in kwargs.items():
        setattr(cfg, key, value)
    return cfg


def _w5_cfg(tmp: Path, **kwargs) -> W5Config:
    data = tmp / "data"
    cfg = W5Config(
        data_root=data,
        w5_root=data / "var" / "w5_maiden_history",
        w3_root=data / "var" / "w3_maiden",
        p1_lock_path=data / "var" / "locks" / "p1_refresh.lock.json",
        health_path=data / "var" / "w5_maiden_history" / "source_health_netkeiba_horse_history.json",
        enabled=True,
        fetch_enabled=False,
        dry_run=False,
        retry_fetch_failed=False,
        max_attempts_per_horse=3,
        max_horses_per_run=2,
        max_requests_per_run=4,
    )
    for key, value in kwargs.items():
        setattr(cfg, key, value)
    return cfg


def _write_c4_health(tmp: Path, state: str) -> None:
    path = tmp / "data" / "var" / "c4_calendar" / "source_health_netkeiba_page_a1.json"
    _write_json(
        path,
        {
            "source": "netkeiba_page_a1",
            "state": state,
            "reason": f"fixture_{state}",
            "consecutive_failures": 0,
        },
    )


def _write_complete_day(cfg: W3AConfig, date_s: str, races: list[dict]) -> None:
    day = cfg.race_refresh_state_root / date_s
    _write_json(
        day / "kaisai_day_index.json",
        {"completeness_state": "COMPLETE", "day_kind": "RACE_DAY", "date": date_s},
    )
    _write_json(day / "page_a1" / "listed_races.json", {"races": races})


def _existing_w3_rows() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for i in range(EXISTING_W3):
        rid = f"20240101{i + 1:04d}"
        rows[rid] = {
            "race_id": rid,
            "kaisai_date": "2024-01-06",
            "venue": "中山",
            "race_number": 1,
            "race_name": "3歳未勝利",
            "queue_status": "result_complete",
            "updated_at": "2024-01-07T00:00:00Z",
            "created_at": "2024-01-06T00:00:00Z",
        }
    return rows


def _seed_w3_world(cfg: W3AConfig, tmp: Path) -> list[str]:
    _write_c4_health(tmp, "HEALTHY")
    cfg.w3_root.mkdir(parents=True, exist_ok=True)
    cfg.c4_queue_path.parent.mkdir(parents=True, exist_ok=True)
    existing = _existing_w3_rows()
    save_queue(cfg.queue_path, existing)
    listed_existing = [
        {
            "race_id": rid,
            "race_name": rec["race_name"],
            "venue": rec["venue"],
            "race_number": rec["race_number"],
        }
        for rid, rec in existing.items()
    ]
    new_ids = ["202506010101", "202506010102", "202606010101"]
    _write_complete_day(cfg, "2024-01-06", listed_existing)
    _write_complete_day(
        cfg,
        "2025-06-01",
        [
            {"race_id": "202506010101", "race_name": "3歳未勝利", "venue": "東京", "race_number": 1},
            {"race_id": "202506010102", "race_name": "3歳未勝利", "venue": "東京", "race_number": 2},
            {"race_id": "202506010199", "race_name": "3歳1勝クラス", "venue": "東京", "race_number": 3},
        ],
    )
    _write_complete_day(
        cfg,
        "2026-06-01",
        [
            {"race_id": "202606010101", "race_name": "3歳未勝利", "venue": "阪神", "race_number": 1},
        ],
    )
    cfg.c4_queue_path.write_text(
        json.dumps({"date": "2025-06-01", "state": "race_day_complete"}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    return new_ids


def _seed_w5_queue(cfg: W5Config) -> None:
    rows: dict[str, dict] = {}
    for i in range(COMPLETE_W5):
        hid = f"2010000{i:03d}"
        rec = w5_empty_row(horse_id=hid, source="fixture")
        rec["queue_status"] = "complete"
        rec["attempt_count"] = 1
        rows[hid] = rec
    for hid in FAILED_W5:
        rec = w5_empty_row(horse_id=hid, source="fixture")
        rec["queue_status"] = "fetch_failed"
        rec["error_code"] = "TimeoutError"
        rec["error_reason"] = "timeout"
        rec["attempt_count"] = 1
        rec["next_eligible_at"] = None
        rows[hid] = rec
    cfg.w5_root.mkdir(parents=True, exist_ok=True)
    w5_save_queue(cfg.queue_path, rows)


class MaidenW3W5StagingTests(unittest.TestCase):
    def setUp(self) -> None:
        global HTTP_CALLS
        HTTP_CALLS = 0
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.w4_pedigree = self.tmp / "data" / "var" / "w4_horse" / "pedigree.json"
        _write_json(self.w4_pedigree, {"protected": True, "horses": 838})
        self.w4_hash = _sha256(self.w4_pedigree)
        self.urlopen_patch = patch("urllib.request.urlopen", side_effect=_forbid_http)
        self.urlopen_patch.start()
        os.environ["C4_ROOT"] = str(self.tmp / "data" / "var" / "c4_calendar")
        os.environ["PI_DATA_ROOT"] = str(self.tmp / "data")
        os.environ["W3W5_LIVE_HTTP"] = "0"
        os.environ["W3A_HANDOFF_DRY_RUN"] = "1"
        os.environ["W5_RETRY_FETCH_FAILED"] = "0"

    def tearDown(self) -> None:
        self.urlopen_patch.stop()
        self.assertEqual(HTTP_CALLS, 0)
        self.assertEqual(_sha256(self.w4_pedigree), self.w4_hash)
        self._tmp.cleanup()

    def test_w3a_dry_run_plans_cap_and_skips_existing(self) -> None:
        cfg = _w3_cfg(self.tmp, w3a_handoff_dry_run=True, w3a_max_enqueue_per_run=2)
        _seed_w3_world(cfg, self.tmp)
        before = cfg.queue_path.read_bytes()
        before_rows = load_queue(cfg.queue_path)
        report = run_w3a_handoff(cfg)
        after_rows = load_queue(cfg.queue_path)
        self.assertTrue(report.dry_run)
        self.assertFalse(report.queue_written)
        self.assertEqual(report.http_request_count, 0)
        self.assertEqual(report.planned_new_race_ids, ["202506010101", "202506010102"])
        self.assertTrue(report.enqueue_capped)
        self.assertEqual(report.maidens_enqueued_new, 0)
        self.assertEqual(len(after_rows), EXISTING_W3)
        self.assertEqual(before, cfg.queue_path.read_bytes())
        for rid, rec in before_rows.items():
            self.assertEqual(after_rows[rid]["updated_at"], rec["updated_at"])
            self.assertEqual(after_rows[rid]["queue_status"], "result_complete")

    def test_w3a_degraded_stops_new_supply_without_queue_write(self) -> None:
        cfg = _w3_cfg(self.tmp, w3a_handoff_dry_run=False)
        _seed_w3_world(cfg, self.tmp)
        _write_c4_health(self.tmp, "DEGRADED")
        before = cfg.queue_path.read_bytes()
        report = run_w3a_handoff(cfg)
        self.assertEqual(report.c4_source_health_state, "DEGRADED")
        self.assertEqual(report.supply_skipped_reason, "c4_degraded")
        self.assertEqual(report.planned_new_race_ids, [])
        self.assertFalse(report.queue_written)
        self.assertEqual(cfg.queue_path.read_bytes(), before)

    def test_w3a_apply_inserts_only_cap_and_leaves_existing(self) -> None:
        cfg = _w3_cfg(self.tmp, w3a_handoff_dry_run=False, w3a_max_enqueue_per_run=2)
        _seed_w3_world(cfg, self.tmp)
        before_rows = load_queue(cfg.queue_path)
        report = run_w3a_handoff(cfg)
        after_rows = load_queue(cfg.queue_path)
        self.assertTrue(report.queue_written)
        self.assertEqual(report.maidens_enqueued_new, 2)
        self.assertEqual(set(report.planned_new_race_ids), {"202506010101", "202506010102"})
        self.assertNotIn("202606010101", after_rows)
        self.assertEqual(len(after_rows), EXISTING_W3 + 2)
        for rid, rec in before_rows.items():
            self.assertEqual(after_rows[rid]["updated_at"], rec["updated_at"])
            self.assertEqual(after_rows[rid]["queue_status"], "result_complete")

    def test_w3c_runner_skips_w3c_on_w3a_failure(self) -> None:
        runner = _load_script("w3_maiden_page_c_acquire_run.py")
        os.environ["W3A_BEFORE_W3C"] = "1"
        os.environ["W3W5_LIVE_HTTP"] = "0"
        cfg = _w3_cfg(self.tmp)
        called = {"w3c": 0}

        def boom(_cfg):
            raise RuntimeError("handoff_boom")

        def w3c(*_a, **_k):
            called["w3c"] += 1
            raise AssertionError("W3-C must not run after W3-A failure")

        with patch.object(runner, "W3AConfig") as cfg_cls, patch.object(
            runner, "run_w3a_handoff", side_effect=boom
        ), patch.object(runner, "run_w3c_acquire", side_effect=w3c), patch.object(
            runner, "_unit_busy", return_value=False
        ), patch.object(sys, "argv", ["w3_maiden_page_c_acquire_run.py", "--data-root", str(cfg.data_root)]):
            cfg_cls.from_env.return_value = cfg
            rc = runner.main()
        self.assertEqual(rc, 1)
        self.assertEqual(called["w3c"], 0)

    def test_w3c_runner_degraded_still_runs_w3c(self) -> None:
        runner = _load_script("w3_maiden_page_c_acquire_run.py")
        os.environ["W3A_BEFORE_W3C"] = "1"
        cfg = _w3_cfg(self.tmp)
        from pi_keibanet.w3_maiden.handoff import HandoffReport
        from pi_keibanet.w3_maiden.acquisition import AcquireReport

        handoff = HandoffReport(
            supply_skipped_reason="c4_degraded",
            c4_source_health_state="DEGRADED",
            queue_rows_total=0,
        )
        w3c_report = AcquireReport(enabled=True, fetch_enabled=False)

        with patch.object(runner, "W3AConfig") as cfg_cls, patch.object(
            runner, "run_w3a_handoff", return_value=handoff
        ), patch.object(runner, "run_w3c_acquire", return_value=w3c_report) as w3c, patch.object(
            runner, "_unit_busy", return_value=False
        ), patch.object(sys, "argv", ["w3_maiden_page_c_acquire_run.py", "--data-root", str(cfg.data_root)]):
            cfg_cls.from_env.return_value = cfg
            rc = runner.main()
        self.assertEqual(rc, 0)
        self.assertEqual(w3c.call_count, 1)
        self.assertFalse(cfg.w3c_fetch_enabled)

    def test_w5_select_never_complete_and_retry_gate(self) -> None:
        now = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
        past = (now - timedelta(seconds=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        future = (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = {
            "c1": {"queue_status": "complete", "attempt_count": 1, "created_at": "1"},
            "p1": {"queue_status": "pending", "attempt_count": 0, "created_at": "2"},
            "f_ready": {
                "queue_status": "fetch_failed",
                "error_code": "TimeoutError",
                "attempt_count": 1,
                "next_eligible_at": past,
                "created_at": "3",
            },
            "f_wait": {
                "queue_status": "fetch_failed",
                "error_code": "TimeoutError",
                "attempt_count": 1,
                "next_eligible_at": future,
                "created_at": "4",
            },
            "f_max": {
                "queue_status": "fetch_failed",
                "error_code": "TimeoutError",
                "attempt_count": 3,
                "next_eligible_at": past,
                "created_at": "5",
            },
        }
        self.assertEqual(select_pending(rows, max_horses=10, now=now), ["p1"])
        self.assertEqual(
            select_eligible(rows, max_horses=10, now=now, retry_fetch_failed=False),
            ["p1"],
        )
        self.assertEqual(
            select_eligible(rows, max_horses=10, now=now, retry_fetch_failed=True, max_attempts=3),
            ["p1", "f_ready"],
        )

    def test_w5_invariants_and_exception_sets_next_eligible(self) -> None:
        cfg = _w5_cfg(self.tmp, fetch_enabled=True, retry_fetch_failed=True, max_horses_per_run=1)
        _seed_w5_queue(cfg)
        before = w5_load_queue(cfg.queue_path)
        self.assertEqual(sum(1 for r in before.values() if r["queue_status"] == "complete"), COMPLETE_W5)

        def boom(_client, _hid):
            raise TimeoutError("read timed out")

        with patch(
            "pi_keibanet.w5_maiden_history.acquisition.fetch_horse_history",
            side_effect=boom,
        ):
            report = run_w5_acquire(
                cfg,
                client=ForbiddenClient(min_interval_sec=0),
                w2_busy=False,
                c4_busy=False,
                w3c_busy=False,
                w4_busy=False,
                horse_ids=["2010000000"],
            )
        self.assertEqual(report.fetch_failed, 0)
        self.assertNotIn("2010000000", report.processed_horse_ids)

        pending = w5_empty_row(horse_id="2021999999", source="fixture")
        rows = w5_load_queue(cfg.queue_path)
        rows["2021999999"] = pending
        w5_save_queue(cfg.queue_path, rows)
        with patch(
            "pi_keibanet.w5_maiden_history.acquisition.fetch_horse_history",
            side_effect=boom,
        ):
            report2 = run_w5_acquire(
                cfg,
                client=ForbiddenClient(min_interval_sec=0),
                horse_ids=["2021999999"],
            )
        after = w5_load_queue(cfg.queue_path)
        rec = after["2021999999"]
        self.assertEqual(rec["queue_status"], "fetch_failed")
        self.assertEqual(rec["error_code"], "TimeoutError")
        self.assertTrue(rec.get("next_eligible_at"))
        self.assertEqual(report2.fetch_failed, 1)
        self.assertEqual(
            sum(1 for r in after.values() if r["queue_status"] == "complete"),
            COMPLETE_W5,
        )

    def test_w5_migrate_default_dry_run_then_apply(self) -> None:
        migrate = _load_script("w5_fetch_failed_retry_migrate.py")
        cfg = _w5_cfg(self.tmp)
        _seed_w5_queue(cfg)
        before = cfg.queue_path.read_bytes()
        dry = migrate.migrate(cfg.queue_path, apply=False)
        self.assertEqual(dry["planned_count"], 3)
        self.assertEqual(dry["applied_count"], 0)
        self.assertEqual(cfg.queue_path.read_bytes(), before)
        applied = migrate.migrate(cfg.queue_path, apply=True)
        self.assertEqual(applied["applied_count"], 3)
        rows = w5_load_queue(cfg.queue_path)
        for hid in FAILED_W5:
            self.assertEqual(rows[hid]["queue_status"], "fetch_failed")
            self.assertTrue(rows[hid]["next_eligible_at"])
            self.assertEqual(rows[hid]["error_code"], "TimeoutError")
        self.assertEqual(
            sum(1 for r in rows.values() if r["queue_status"] == "complete"),
            COMPLETE_W5,
        )

    def test_w5_runner_gate_ready_exits_zero(self) -> None:
        runner = _load_script("w5_maiden_history_acquire_run.py")
        from pi_keibanet.w5_maiden_history.acquisition import AcquireReport
        from pi_keibanet.w5_maiden_history.gate_monitor import GateMonitorState

        cfg = _w5_cfg(self.tmp, fetch_enabled=True)
        report = AcquireReport(enabled=True, fetch_enabled=False, fetch_failed=0)
        gate = GateMonitorState(reevaluation_ready=True)

        with patch.object(runner, "W5Config") as cfg_cls, patch.object(
            runner, "run_w5_acquire", return_value=report
        ), patch.object(runner, "run_w5_handoff"), patch.object(
            runner, "update_gate_monitor", return_value=gate
        ), patch.object(runner, "_busy", return_value=False), patch.object(
            sys, "argv", ["w5_maiden_history_acquire_run.py", "--data-root", str(cfg.data_root)]
        ):
            cfg_cls.from_env.return_value = cfg
            rc = runner.main()
        self.assertEqual(rc, 0)
        self.assertFalse(cfg.fetch_enabled)

    def test_historical_unknown_days_are_not_zero_maidens(self) -> None:
        hist = _load_script("w3_maiden_historical_dry_run.py")
        cfg = _w3_cfg(self.tmp)
        _seed_w3_world(cfg, self.tmp)
        week_dir = self.tmp / "data" / "var" / "c4_calendar" / "weeks" / "2024-W02"
        _write_json(
            week_dir / "calendar.json",
            {"days": [{"date": "2024-01-08", "kind": "unknown_local_only"}]},
        )
        os.environ["W3_ROOT"] = str(cfg.w3_root)
        os.environ["PI_RACE_REFRESH_STATE_ROOT"] = str(cfg.race_refresh_state_root)
        os.environ["W3_C4_QUEUE_PATH"] = str(cfg.c4_queue_path)
        report = hist.run_historical_dry_run(cfg)
        self.assertEqual(report["http_calls"], 0)
        self.assertEqual(report["existing_w3_queue_by_year"]["2024"], EXISTING_W3)
        self.assertEqual(report["existing_w3_queue_by_year"]["2025"], 0)
        self.assertEqual(report["existing_w3_queue_by_year"]["2026"], 0)
        self.assertGreaterEqual(report["planned_maiden_count"], 3)
        self.assertIn("2024-01-08", report["unknown_days"])
        self.assertGreater(report["unknown_day_count"], 0)
        self.assertIn("not treated as 0 maidens", report["note"])

    def test_live_http_switch_defaults_off(self) -> None:
        os.environ.pop("W3W5_LIVE_HTTP", None)
        self.assertNotEqual(os.environ.get("W3W5_LIVE_HTTP", "0"), "1")

    def test_w3w5_live_http_zero_fail_closes_w3c_and_w5(self) -> None:
        os.environ.pop("W3W5_LIVE_HTTP", None)
        os.environ["W3C_FETCH_ENABLED"] = "1"
        os.environ["W5_FETCH_ENABLED"] = "1"
        w3 = _load_script("w3_maiden_page_c_acquire_run.py")
        w5 = _load_script("w5_maiden_history_acquire_run.py")
        cfg3 = _w3_cfg(self.tmp, w3c_fetch_enabled=True)
        cfg5 = _w5_cfg(self.tmp, fetch_enabled=True)
        from pi_keibanet.w3_maiden.acquisition import AcquireReport as W3Rep
        from pi_keibanet.w5_maiden_history.acquisition import AcquireReport as W5Rep
        from pi_keibanet.w5_maiden_history.gate_monitor import GateMonitorState

        with patch.object(w3, "W3AConfig") as c3, patch.object(
            w3, "run_w3c_acquire", return_value=W3Rep()
        ), patch.object(w3, "_unit_busy", return_value=False), patch.object(
            sys, "argv", ["w3", "--data-root", str(cfg3.data_root)]
        ):
            c3.from_env.return_value = cfg3
            self.assertEqual(w3.main(), 0)
        self.assertFalse(cfg3.w3c_fetch_enabled)

        with patch.object(w5, "W5Config") as c5, patch.object(
            w5, "run_w5_acquire", return_value=W5Rep(fetch_failed=0)
        ), patch.object(w5, "run_w5_handoff"), patch.object(
            w5, "update_gate_monitor", return_value=GateMonitorState()
        ), patch.object(w5, "_busy", return_value=False), patch.object(
            sys, "argv", ["w5", "--data-root", str(cfg5.data_root)]
        ):
            c5.from_env.return_value = cfg5
            self.assertEqual(w5.main(), 0)
        self.assertFalse(cfg5.fetch_enabled)

    def test_w3a_dry_run_zero_writes(self) -> None:
        cfg = _w3_cfg(self.tmp, w3a_handoff_dry_run=True, w3a_max_enqueue_per_run=2)
        _seed_w3_world(cfg, self.tmp)
        root = self.tmp / "data"

        def snap() -> dict[str, str]:
            out: dict[str, str] = {}
            for p in sorted(root.rglob("*")):
                if p.is_file():
                    out[str(p.relative_to(root))] = _sha256(p)
            return out

        before = snap()
        report = run_w3a_handoff(cfg)
        after = snap()
        self.assertTrue(report.dry_run)
        self.assertFalse(report.queue_written)
        self.assertEqual(report.run_report_path, "")
        self.assertEqual(list(cfg.runs_dir.glob("w3a_handoff_*.json")) if cfg.runs_dir.exists() else [], [])
        self.assertEqual(before, after)

    def test_w3a_apply_keeps_existing_row_bytes(self) -> None:
        cfg = _w3_cfg(self.tmp, w3a_handoff_dry_run=False, w3a_max_enqueue_per_run=2)
        _seed_w3_world(cfg, self.tmp)

        def lines_by_id(path: Path) -> dict[str, str]:
            out: dict[str, str] = {}
            for line in path.read_text(encoding="utf-8").splitlines():
                rec = json.loads(line)
                out[str(rec["race_id"])] = line
            return out

        before = lines_by_id(cfg.queue_path)
        self.assertEqual(len(before), EXISTING_W3)
        report = run_w3a_handoff(cfg)
        after = lines_by_id(cfg.queue_path)
        self.assertTrue(report.queue_written)
        for rid, line in before.items():
            self.assertEqual(after[rid], line)
        self.assertEqual(len(after), EXISTING_W3 + 2)

    def test_w3a_cap_scan_order_is_deterministic(self) -> None:
        planned = []
        for _ in range(5):
            tmp = Path(tempfile.mkdtemp(dir=self.tmp))
            os.environ["C4_ROOT"] = str(tmp / "data" / "var" / "c4_calendar")
            cfg = _w3_cfg(tmp, w3a_handoff_dry_run=True, w3a_max_enqueue_per_run=2)
            _seed_w3_world(cfg, tmp)
            planned.append(run_w3a_handoff(cfg).planned_new_race_ids)
        self.assertTrue(all(p == ["202506010101", "202506010102"] for p in planned))

    def test_c4_health_path_matches_production_contract(self) -> None:
        from pi_keibanet.c4_calendar.config import C4Config
        from pi_keibanet.w3_maiden.handoff import _c4_page_a1_health_state

        os.environ.pop("C4_ROOT", None)
        data = Path("/opt/expect-ai/platform/data")
        c4 = C4Config.from_env(data_root=data)
        self.assertEqual(
            str(c4.health_path),
            "/opt/expect-ai/platform/data/var/c4_calendar/source_health_netkeiba_page_a1.json",
        )
        cfg = _w3_cfg(self.tmp)
        os.environ["C4_ROOT"] = str(self.tmp / "data" / "var" / "c4_calendar")
        _write_c4_health(self.tmp, "HEALTHY")
        self.assertEqual(_c4_page_a1_health_state(cfg), "HEALTHY")

    def test_w5_attempt_count_single_increment_on_exception_and_http(self) -> None:
        from pi_keibanet.netkeiba.client import NetkeibaFetchError
        from pi_keibanet.w5_maiden_history import acquisition as acq

        cfg = _w5_cfg(
            self.tmp,
            fetch_enabled=True,
            retry_fetch_failed=True,
            max_horses_per_run=1,
            fetch_failed_cooldown_sec=3600,
            cooldown_seconds=86400,
        )
        cfg.w5_root.mkdir(parents=True, exist_ok=True)
        frozen = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)

        def run_one(hid: str, exc: BaseException) -> dict:
            rec = w5_empty_row(horse_id=hid, source="fixture")
            rec["attempt_count"] = 1
            w5_save_queue(cfg.queue_path, {hid: rec})
            with patch.object(acq, "fetch_horse_history", side_effect=exc), patch.object(
                acq, "_utc_now", return_value=frozen
            ):
                run_w5_acquire(
                    cfg,
                    client=ForbiddenClient(min_interval_sec=0),
                    horse_ids=[hid],
                    now=frozen,
                )
            return w5_load_queue(cfg.queue_path)[hid]

        timeout = run_one("2021000001", TimeoutError("x"))
        self.assertEqual(timeout["attempt_count"], 2)
        self.assertEqual(timeout["queue_status"], "fetch_failed")
        self.assertEqual(timeout["next_eligible_at"], "2026-09-07T13:00:00Z")

        http500 = run_one("2021000002", NetkeibaFetchError("HTTP 500", http_status=500))
        self.assertEqual(http500["attempt_count"], 2)
        self.assertEqual(http500["queue_status"], "fetch_failed")
        self.assertEqual(http500["error_code"], "HTTP_500")
        self.assertEqual(http500["next_eligible_at"], "2026-09-07T13:00:00Z")

        http403 = run_one("2021000003", NetkeibaFetchError("HTTP 403", http_status=403))
        self.assertEqual(http403["attempt_count"], 2)
        self.assertEqual(http403["queue_status"], "blocked")
        self.assertEqual(http403["next_eligible_at"], "2026-09-08T12:00:00Z")

    def test_w5_retry_stops_at_max_three_attempts(self) -> None:
        now = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)
        past = "2026-09-07T11:00:00Z"
        hid = "2021107235"
        row = {
            "queue_status": "fetch_failed",
            "error_code": "TimeoutError",
            "attempt_count": 2,
            "next_eligible_at": past,
            "created_at": "1",
        }
        self.assertEqual(
            select_eligible({hid: row}, max_horses=10, now=now, retry_fetch_failed=True, max_attempts=3),
            [hid],
        )
        cfg = _w5_cfg(self.tmp, fetch_enabled=True, retry_fetch_failed=True, max_horses_per_run=1)
        cfg.w5_root.mkdir(parents=True, exist_ok=True)
        rec = w5_empty_row(horse_id=hid, source="fixture")
        rec.update(row)
        w5_save_queue(cfg.queue_path, {hid: rec})
        with patch(
            "pi_keibanet.w5_maiden_history.acquisition.fetch_horse_history",
            side_effect=TimeoutError("again"),
        ):
            run_w5_acquire(cfg, client=ForbiddenClient(min_interval_sec=0), horse_ids=[hid], now=now)
        after = w5_load_queue(cfg.queue_path)[hid]
        self.assertEqual(after["attempt_count"], 3)
        self.assertEqual(
            select_eligible(
                {hid: after},
                max_horses=10,
                now=now + timedelta(hours=2),
                retry_fetch_failed=True,
                max_attempts=3,
            ),
            [],
        )

    def test_next_eligible_at_uses_datetime_not_string(self) -> None:
        from pi_keibanet.w5_maiden_history.acquisition import _is_retryable_fetch_failed

        now = datetime(2026, 9, 7, 6, 0, tzinfo=timezone.utc)
        row = {
            "queue_status": "fetch_failed",
            "error_code": "TimeoutError",
            "attempt_count": 1,
            "next_eligible_at": "2026-09-07T12:30:00+09:00",
        }
        self.assertTrue(_is_retryable_fetch_failed(row, now=now, max_attempts=3))
        now_s = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        nxt_s = row["next_eligible_at"]
        self.assertLess(now_s, nxt_s)

    def test_w5_runner_exit4_is_this_run_only(self) -> None:
        runner = _load_script("w5_maiden_history_acquire_run.py")
        from pi_keibanet.w5_maiden_history.acquisition import AcquireReport
        from pi_keibanet.w5_maiden_history.gate_monitor import GateMonitorState

        cfg = _w5_cfg(self.tmp)
        gate = GateMonitorState(reevaluation_ready=False)
        queued_fail = AcquireReport(fetch_failed=0)
        this_run_fail = AcquireReport(fetch_failed=1)
        with patch.object(runner, "W5Config") as cfg_cls, patch.object(
            runner, "run_w5_handoff"
        ), patch.object(runner, "update_gate_monitor", return_value=gate), patch.object(
            runner, "_busy", return_value=False
        ):
            cfg_cls.from_env.return_value = cfg
            with patch.object(runner, "run_w5_acquire", return_value=queued_fail), patch.object(
                sys, "argv", ["w5", "--data-root", str(cfg.data_root)]
            ):
                self.assertEqual(runner.main(), 0)
            with patch.object(runner, "run_w5_acquire", return_value=this_run_fail), patch.object(
                sys, "argv", ["w5", "--data-root", str(cfg.data_root)]
            ):
                self.assertEqual(runner.main(), 4)

    def test_w3a_before_w3c_unset_keeps_old_behavior(self) -> None:
        runner = _load_script("w3_maiden_page_c_acquire_run.py")
        os.environ.pop("W3A_BEFORE_W3C", None)
        cfg = _w3_cfg(self.tmp)
        from pi_keibanet.w3_maiden.acquisition import AcquireReport

        with patch.object(runner, "W3AConfig") as cfg_cls, patch.object(
            runner, "run_w3a_handoff"
        ) as handoff, patch.object(
            runner, "run_w3c_acquire", return_value=AcquireReport()
        ), patch.object(runner, "_unit_busy", return_value=False), patch.object(
            sys, "argv", ["w3", "--data-root", str(cfg.data_root)]
        ):
            cfg_cls.from_env.return_value = cfg
            self.assertEqual(runner.main(), 0)
        handoff.assert_not_called()

    def test_w5_fetch_disabled_does_not_call_http(self) -> None:
        cfg = _w5_cfg(self.tmp, fetch_enabled=False)
        rec = w5_empty_row(horse_id="2021999998", source="fixture")
        cfg.w5_root.mkdir(parents=True, exist_ok=True)
        w5_save_queue(cfg.queue_path, {rec["horse_id"]: rec})
        with patch(
            "pi_keibanet.w5_maiden_history.acquisition.fetch_horse_history",
            side_effect=_forbid_http,
        ) as fetch:
            report = run_w5_acquire(cfg, client=ForbiddenClient(min_interval_sec=0))
        fetch.assert_not_called()
        self.assertEqual(report.http_request_count, 0)


if __name__ == "__main__":
    unittest.main()
