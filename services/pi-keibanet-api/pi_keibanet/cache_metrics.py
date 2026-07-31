# -*- coding: utf-8 -*-
"""In-process cache / fallback counters for Ops (PE/CE 非変更)."""
from __future__ import annotations

import threading
import time
from typing import Any

_lock = threading.Lock()
_started = time.time()
_stats: dict[str, Any] = {
    "board_hits": 0,
    "board_misses": 0,
    "board_cold_ms": [],
    "board_warm_ms": [],
    "odds_hits": 0,
    "odds_misses": 0,
    "odds_cold_ms": [],
    "odds_warm_ms": [],
    "history_hits": 0,
    "history_misses": 0,
    "history_ms": [],
    "history_ajax_ok": 0,
    "history_sp_fallback": 0,
    "history_static": 0,
    "history_live": 0,
    "history_fail": 0,
    "prediction_hits": 0,
    "prediction_misses": 0,
    "prediction_ms": [],
}


def _push(arr: list[float], value: float, limit: int = 40) -> None:
    arr.append(value)
    if len(arr) > limit:
        del arr[: len(arr) - limit]


def _avg(arr: list[float]) -> float | None:
    if not arr:
        return None
    return round(sum(arr) / len(arr), 1)


def note_board(*, hit: bool, ms: float) -> None:
    with _lock:
        if hit:
            _stats["board_hits"] += 1
            _push(_stats["board_warm_ms"], ms)
        else:
            _stats["board_misses"] += 1
            _push(_stats["board_cold_ms"], ms)


def note_odds(*, hit: bool, ms: float) -> None:
    with _lock:
        if hit:
            _stats["odds_hits"] += 1
            _push(_stats["odds_warm_ms"], ms)
        else:
            _stats["odds_misses"] += 1
            _push(_stats["odds_cold_ms"], ms)


def note_history(*, hit: bool, ms: float) -> None:
    with _lock:
        if hit:
            _stats["history_hits"] += 1
        else:
            _stats["history_misses"] += 1
        _push(_stats["history_ms"], ms)


def note_history_source(source: str) -> None:
    with _lock:
        if source == "ajax":
            _stats["history_ajax_ok"] += 1
        elif source == "sp":
            _stats["history_sp_fallback"] += 1
        elif source in {"csv", "db"}:
            _stats["history_static"] = int(_stats.get("history_static") or 0) + 1
        elif source == "live":
            _stats["history_live"] = int(_stats.get("history_live") or 0) + 1
        else:
            _stats["history_fail"] += 1


def note_prediction(*, hit: bool, ms: float) -> None:
    with _lock:
        if hit:
            _stats["prediction_hits"] += 1
        else:
            _stats["prediction_misses"] += 1
        _push(_stats["prediction_ms"], ms)


def snapshot() -> dict[str, Any]:
    with _lock:
        def rate(hits: int, misses: int) -> float | None:
            total = hits + misses
            if not total:
                return None
            return round(100.0 * hits / total, 1)

        hist_total = (
            int(_stats["history_ajax_ok"])
            + int(_stats["history_sp_fallback"])
            + int(_stats.get("history_static") or 0)
            + int(_stats.get("history_live") or 0)
            + int(_stats["history_fail"])
        )
        sp_rate = None
        static_rate = None
        if hist_total:
            sp_rate = round(100.0 * int(_stats["history_sp_fallback"]) / hist_total, 1)
            static_rate = round(
                100.0 * int(_stats.get("history_static") or 0) / hist_total, 1
            )

        return {
            "schema_version": "expect-pi-cache-metrics/1.0",
            "uptime_sec": round(time.time() - _started, 1),
            "board": {
                "hits": _stats["board_hits"],
                "misses": _stats["board_misses"],
                "hit_rate_pct": rate(_stats["board_hits"], _stats["board_misses"]),
                "avg_cold_ms": _avg(_stats["board_cold_ms"]),
                "avg_warm_ms": _avg(_stats["board_warm_ms"]),
            },
            "odds": {
                "hits": _stats["odds_hits"],
                "misses": _stats["odds_misses"],
                "hit_rate_pct": rate(_stats["odds_hits"], _stats["odds_misses"]),
                "avg_cold_ms": _avg(_stats["odds_cold_ms"]),
                "avg_warm_ms": _avg(_stats["odds_warm_ms"]),
            },
            "history": {
                "hits": _stats["history_hits"],
                "misses": _stats["history_misses"],
                "hit_rate_pct": rate(_stats["history_hits"], _stats["history_misses"]),
                "avg_ms": _avg(_stats["history_ms"]),
                "ajax_ok": _stats["history_ajax_ok"],
                "sp_fallback": _stats["history_sp_fallback"],
                "static": int(_stats.get("history_static") or 0),
                "live": int(_stats.get("history_live") or 0),
                "fail": _stats["history_fail"],
                "sp_fallback_rate_pct": sp_rate,
                "static_rate_pct": static_rate,
            },
            "prediction_response_cache": {
                "hits": _stats["prediction_hits"],
                "misses": _stats["prediction_misses"],
                "hit_rate_pct": rate(_stats["prediction_hits"], _stats["prediction_misses"]),
                "avg_ms": _avg(_stats["prediction_ms"]),
            },
        }
