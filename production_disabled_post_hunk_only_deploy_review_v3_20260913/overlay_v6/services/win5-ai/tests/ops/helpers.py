# -*- coding: utf-8 -*-
"""Test helpers for ops E2E / regression / performance."""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def enable_prediction_runs(
    *,
    dates: str = "2026-07-19",
    key: str = "test-run-key",
) -> dict[str, str]:
    os.environ["PREDICTION_RUNS_ENABLED"] = "1"
    os.environ["PREDICTION_RUN_ALLOWED_DATES"] = dates
    os.environ["PREDICTION_RUN_API_KEY"] = key
    return {"X-Prediction-Run-Key": key}


@contextmanager
def isolated_env(
    *,
    engine: str = "mock",
    allow_migration_019: bool = True,
    allow_migration_022: bool | None = None,
) -> Iterator[dict[str, str]]:
    tmp = tempfile.TemporaryDirectory()
    db_path = Path(tmp.name) / "test.db"
    ops_dir = Path(tmp.name) / "ops"
    report_dir = Path(tmp.name) / "reports"
    log_dir = Path(tmp.name) / "logs"
    for d in (ops_dir, report_dir, log_dir):
        d.mkdir(parents=True, exist_ok=True)

    if allow_migration_022 is None:
        allow_migration_022 = allow_migration_019

    env = {
        "EXPECT_AI_DB_PATH": str(db_path),
        "EXPECT_AI_OPS_DIR": str(ops_dir),
        "EXPECT_AI_REPORT_DIR": str(report_dir),
        "EXPECT_AI_LOG_DIR": str(log_dir),
        "EXPECT_AI_USE_DB_CATALOG": "1",
        "AI_ENGINE": engine,
    }
    if allow_migration_022:
        env["EXPECT_AI_ALLOW_MIGRATION_022"] = "1"
    old: dict[str, str | None] = {}
    for k, v in env.items():
        old[k] = os.environ.get(k)
        os.environ[k] = v
    for extra in (
        "PREDICTION_RUNS_ENABLED",
        "PREDICTION_RUN_ALLOWED_DATES",
        "PREDICTION_RUN_API_KEY",
        "PREDICTION_RUN_RATE_LIMIT",
        "PREDICTION_RUN_MAX_BODY_BYTES",
        "EXPECT_AI_ALLOW_MIGRATION_019",
        "EXPECT_AI_ALLOW_MIGRATION_022",
    ):
        old.setdefault(extra, os.environ.get(extra))
    # Superseded 019 gate must not apply even if callers still pass the old name.
    os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_019", None)
    if not allow_migration_022:
        os.environ.pop("EXPECT_AI_ALLOW_MIGRATION_022", None)

    try:
        from app.engine import data as engine_data

        engine_data.clear_caches()
    except Exception:
        pass
    try:
        from app.predictions.guards import reset_prediction_run_rate_limit

        reset_prediction_run_rate_limit()
    except Exception:
        pass
    try:
        from app.ops import performance as perf_mod

        perf_mod._default_recorder = None
    except Exception:
        pass

    try:
        yield env
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        try:
            from app.engine import data as engine_data

            engine_data.clear_caches()
        except Exception:
            pass
        tmp.cleanup()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@contextmanager
def running_server(
    *,
    engine: str = "mock",
    allow_migration_019: bool = True,
    prediction_runs: bool = False,
    prediction_run_dates: str = "2026-07-19",
    prediction_run_key: str = "test-run-key",
) -> Iterator[str]:
    with isolated_env(engine=engine, allow_migration_019=allow_migration_019):
        if prediction_runs:
            enable_prediction_runs(dates=prediction_run_dates, key=prediction_run_key)
            os.environ["PREDICTION_RUN_RATE_LIMIT"] = "1000"
            from app.predictions.guards import reset_prediction_run_rate_limit

            reset_prediction_run_rate_limit()
        from app.data.db import migrate

        migrate()

        from app.main import Handler

        port = _free_port()
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{port}"
        for _ in range(20):
            try:
                http_json(f"{base}/health")
                break
            except Exception:
                time.sleep(0.05)
        try:
            yield base
        finally:
            server.shutdown()
            server.server_close()


def http_json(
    url: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30,
) -> tuple[int, dict[str, Any]]:
    data = None
    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req_headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return exc.code, payload


def load_fixture(name: str) -> Path:
    return FIXTURES / name


def import_sample_data() -> None:
    from app.data.etl import EtlPipeline

    pipe = EtlPipeline()
    pipe.import_races_csv(load_fixture("sample_races.csv"))
    pipe.import_features_csv(load_fixture("sample_features.csv"))
