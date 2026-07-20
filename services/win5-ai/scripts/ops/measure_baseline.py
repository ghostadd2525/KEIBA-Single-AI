#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
F-4 Performance baseline measurement.

Usage:
  cd services/win5-ai
  python scripts/ops/measure_baseline.py
  python scripts/ops/measure_baseline.py --engine mock --output tests/ops/baseline.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.ops.helpers import http_json, import_sample_data, isolated_env, running_server


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def measure_api(base: str, path: str, *, method: str = "GET", body: dict | None = None, rounds: int = 5) -> dict:
    times: list[float] = []
    status = 200
    for _ in range(rounds):
        start = time.perf_counter()
        status, _ = http_json(f"{base}{path}", method=method, body=body)
        times.append((time.perf_counter() - start) * 1000)
    times.sort()
    n = len(times)
    return {
        "path": path,
        "status": status,
        "rounds": rounds,
        "p50_ms": round(times[n // 2], 2),
        "p95_ms": round(times[int(n * 0.95)] if n > 1 else times[0], 2),
        "avg_ms": round(sum(times) / n, 2),
    }


def measure_etl() -> dict:
    start = time.perf_counter()
    with isolated_env(engine="mock"):
        from app.data.db import migrate
        from app.data.etl import EtlPipeline

        migrate()
        pipe = EtlPipeline()
        from tests.ops.helpers import load_fixture

        r = pipe.import_races_csv(load_fixture("sample_races.csv"))
        f = pipe.import_features_csv(load_fixture("sample_features.csv"))
        ms = (time.perf_counter() - start) * 1000
    return {
        "name": "etl_import_sample",
        "duration_ms": round(ms, 2),
        "races": r.races,
        "features": f.features,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure ops performance baseline")
    parser.add_argument("--engine", default="mock", choices=["mock", "real"])
    parser.add_argument("--output", default=str(ROOT / "tests" / "ops" / "baseline.json"))
    parser.add_argument("--rounds", type=int, default=5)
    args = parser.parse_args()

    api_results: list[dict] = []
    with running_server(engine=args.engine) as base:
        endpoints = [
            ("/health", "GET", None),
            ("/v1/predictions", "GET", None),
            ("/v1/data/coverage", "GET", None),
            ("/v1/diagnostics/missing", "GET", None),
            ("/v1/admin/monitoring", "GET", None),
            (
                "/v1/conversation/chat",
                "POST",
                {"message": "20260719_hanshin_11を予想して"},
            ),
        ]
        for path, method, body in endpoints:
            api_results.append(
                measure_api(base, path, method=method, body=body, rounds=args.rounds)
            )

    etl = measure_etl()
    report = {
        "generated_at": _now(),
        "engine": args.engine,
        "api": api_results,
        "etl": etl,
        "notes": "Baseline for Phase F operational readiness. Re-run after major changes.",
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
