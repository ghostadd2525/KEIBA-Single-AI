# -*- coding: utf-8 -*-
"""A1 Application metrics (in-process counters)."""
from __future__ import annotations

import threading
import time
from typing import Any


class SingleServiceMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.requests_total = 0
        self.requests_ok = 0
        self.requests_error = 0
        self.latency_ms_sum = 0.0
        self.latency_ms_count = 0
        self.by_path: dict[str, int] = {}
        self.started_at = time.time()

    def record(self, path: str, *, ok: bool, latency_ms: float) -> None:
        with self._lock:
            self.requests_total += 1
            if ok:
                self.requests_ok += 1
            else:
                self.requests_error += 1
            self.latency_ms_sum += float(latency_ms)
            self.latency_ms_count += 1
            self.by_path[path] = self.by_path.get(path, 0) + 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            avg = (
                self.latency_ms_sum / self.latency_ms_count
                if self.latency_ms_count
                else 0.0
            )
            return {
                "service": "single-ai-http",
                "uptime_sec": round(time.time() - self.started_at, 3),
                "requests_total": self.requests_total,
                "requests_ok": self.requests_ok,
                "requests_error": self.requests_error,
                "latency_ms_avg": round(avg, 4),
                "by_path": dict(self.by_path),
            }


METRICS = SingleServiceMetrics()
