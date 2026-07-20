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


@contextmanager
def isolated_env(*, engine: str = "mock") -> Iterator[dict[str, str]]:
    tmp = tempfile.TemporaryDirectory()
    db_path = Path(tmp.name) / "test.db"
    ops_dir = Path(tmp.name) / "ops"
    report_dir = Path(tmp.name) / "reports"
    log_dir = Path(tmp.name) / "logs"
    for d in (ops_dir, report_dir, log_dir):
        d.mkdir(parents=True, exist_ok=True)

    env = {
        "EXPECT_AI_DB_PATH": str(db_path),
        "EXPECT_AI_OPS_DIR": str(ops_dir),
        "EXPECT_AI_REPORT_DIR": str(report_dir),
        "EXPECT_AI_LOG_DIR": str(log_dir),
        "EXPECT_AI_USE_DB_CATALOG": "1",
        "AI_ENGINE": engine,
    }
    old: dict[str, str | None] = {}
    for k, v in env.items():
        old[k] = os.environ.get(k)
        os.environ[k] = v

    try:
        from app.engine import data as engine_data

        engine_data.clear_caches()
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
def running_server(*, engine: str = "mock") -> Iterator[str]:
    with isolated_env(engine=engine):
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
