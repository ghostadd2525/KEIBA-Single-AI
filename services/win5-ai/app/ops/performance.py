# -*- coding: utf-8 -*-
"""Performance timing — API / ETL / Conversation 応答時間記録。"""
from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def _metrics_dir() -> Path:
    env = (os.environ.get("EXPECT_AI_OPS_DIR") or "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "var" / "ops"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PerformanceRecorder:
    def __init__(self) -> None:
        self.path = _metrics_dir() / "metrics.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        *,
        category: str,
        name: str,
        duration_ms: float,
        status: str = "ok",
        extra: dict[str, Any] | None = None,
    ) -> None:
        row = {
            "ts": _now(),
            "category": category,
            "name": name,
            "duration_ms": round(duration_ms, 2),
            "status": status,
            **(extra or {}),
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    def summarize(self, *, limit: int = 500) -> dict[str, Any]:
        if not self.path.exists():
            return {"samples": 0, "by_name": {}}
        rows: list[dict[str, Any]] = []
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        rows = rows[-limit:]
        by_name: dict[str, list[float]] = {}
        for r in rows:
            by_name.setdefault(r["name"], []).append(float(r["duration_ms"]))

        summary: dict[str, Any] = {}
        for name, vals in by_name.items():
            vals_sorted = sorted(vals)
            n = len(vals_sorted)
            summary[name] = {
                "count": n,
                "p50_ms": vals_sorted[n // 2],
                "p95_ms": vals_sorted[int(n * 0.95)] if n > 1 else vals_sorted[0],
                "max_ms": vals_sorted[-1],
                "avg_ms": round(sum(vals_sorted) / n, 2),
            }
        return {"samples": len(rows), "by_name": summary}


_default_recorder: PerformanceRecorder | None = None


def get_recorder() -> PerformanceRecorder:
    global _default_recorder
    if _default_recorder is None:
        _default_recorder = PerformanceRecorder()
    return _default_recorder


def record_timing(
    category: str,
    name: str,
    duration_ms: float,
    *,
    status: str = "ok",
    extra: dict[str, Any] | None = None,
) -> None:
    get_recorder().record(
        category=category,
        name=name,
        duration_ms=duration_ms,
        status=status,
        extra=extra,
    )


@contextmanager
def measure(category: str, name: str, **extra: Any) -> Iterator[None]:
    start = time.perf_counter()
    status = "ok"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        ms = (time.perf_counter() - start) * 1000
        record_timing(category, name, ms, status=status, extra=extra or None)
