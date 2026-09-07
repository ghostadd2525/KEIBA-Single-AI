# -*- coding: utf-8 -*-
"""Evidence quality metrics: coverage, freshness, completeness, consistency."""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from typing import Any

from .config import PHASE1_FEATURES
from .anti_leak import parse_iso
from ..data.db import connect, migrate


def compute_runner_feature_metrics(
    runners: list[dict[str, Any]],
    *,
    prediction_created_at: str,
    sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not runners:
        return {
            "coverage": 0.0,
            "missing_rate": 1.0,
            "freshness_p50_sec": None,
            "completeness": 0.0,
            "consistency": 0.0,
            "by_feature": {},
        }

    pred_dt = parse_iso(prediction_created_at)
    freshness_secs: list[float] = []
    by_feature: dict[str, dict[str, Any]] = {}

    for fid in PHASE1_FEATURES:
        filled = sum(1 for r in runners if r.get(fid) is not None)
        total = len(runners)
        cov = filled / total if total else 0.0
        by_feature[fid] = {
            "coverage": round(cov, 4),
            "missing_rate": round(1.0 - cov, 4),
            "filled": filled,
            "total": total,
        }

    if sources and pred_dt:
        for src in sources:
            obs = parse_iso(src.get("observed_at"))
            if obs:
                freshness_secs.append(abs((pred_dt - obs).total_seconds()))

    total_cells = len(runners) * len(PHASE1_FEATURES)
    filled_cells = sum(
        1 for r in runners for fid in PHASE1_FEATURES if r.get(fid) is not None
    )
    coverage = filled_cells / total_cells if total_cells else 0.0

    # consistency: popularity order vs win_odds order (when both present)
    consistent = 0
    comparable = 0
    odds_rank = {}
    pop_rank = {}
    for r in runners:
        hn = r.get("horse_number")
        if r.get("win_odds") is not None:
            odds_rank[hn] = float(r["win_odds"])
        if r.get("popularity") is not None:
            pop_rank[hn] = int(r["popularity"])
    if len(odds_rank) >= 2 and len(pop_rank) >= 2:
        comparable = 1
        odds_sorted = sorted(odds_rank.items(), key=lambda x: (x[1], x[0]))
        pop_sorted = sorted(pop_rank.items(), key=lambda x: (x[1], x[0]))
        if [x[0] for x in odds_sorted[:3]] == [x[0] for x in pop_sorted[:3]]:
            consistent = 1

    return {
        "coverage": round(coverage, 4),
        "missing_rate": round(1.0 - coverage, 4),
        "freshness_p50_sec": (
            round(statistics.median(freshness_secs), 1) if freshness_secs else None
        ),
        "completeness": round(coverage, 4),
        "consistency": float(consistent) if comparable else None,
        "by_feature": by_feature,
    }


def aggregate_daily_metrics(*, metric_date: str) -> dict[str, dict[str, Any]]:
    migrate()
    conn = connect()
    out: dict[str, dict[str, Any]] = {}
    try:
        rows = conn.execute(
            """
            SELECT payload_json, captured_at
            FROM research_prediction_snapshots
            WHERE substr(captured_at, 1, 10) = ? OR race_date = ?
            """,
            (metric_date, metric_date),
        ).fetchall()

        buckets: dict[str, list[dict[str, Any]]] = {fid: [] for fid in PHASE1_FEATURES}
        latencies: list[float] = []
        successes = 0
        total_events = 0

        for row in rows:
            payload = json.loads(row["payload_json"] or "{}")
            runners = payload.get("runners") or []
            pred_created = payload.get("prediction_created_at") or row["captured_at"]
            q = compute_runner_feature_metrics(
                runners,
                prediction_created_at=str(pred_created or ""),
                sources=payload.get("sources"),
            )
            for fid, meta in (q.get("by_feature") or {}).items():
                buckets.setdefault(fid, []).append(meta)
            lat = (payload.get("quality") or {}).get("source_latency_ms")
            if lat is not None:
                latencies.append(float(lat))

        ev = conn.execute(
            """
            SELECT feature_id, success, latency_ms
            FROM research_source_events
            WHERE substr(created_at, 1, 10) = ?
            """,
            (metric_date,),
        ).fetchall()
        for e in ev:
            total_events += 1
            if e["success"]:
                successes += 1

        retry_total = conn.execute(
            """
            SELECT COALESCE(SUM(retry_count), 0)
            FROM research_collect_jobs
            WHERE substr(enqueued_at, 1, 10) = ?
            """,
            (metric_date,),
        ).fetchone()[0]

        for fid in PHASE1_FEATURES:
            items = buckets.get(fid) or []
            if not items:
                out[fid] = {
                    "coverage": 0.0,
                    "missing_rate": 1.0,
                    "freshness_p50_sec": None,
                    "completeness": 0.0,
                    "consistency": None,
                    "success_rate": 0.0,
                    "retry_total": int(retry_total or 0),
                    "source_latency_p50_ms": None,
                    "source_availability": 0.0,
                    "sample_count": 0,
                }
                continue
            cov_avg = statistics.mean(x["coverage"] for x in items)
            out[fid] = {
                "coverage": round(cov_avg, 4),
                "missing_rate": round(1.0 - cov_avg, 4),
                "freshness_p50_sec": None,
                "completeness": round(cov_avg, 4),
                "consistency": None,
                "success_rate": round(successes / total_events, 4) if total_events else 0.0,
                "retry_total": int(retry_total or 0),
                "source_latency_p50_ms": (
                    round(statistics.median(latencies), 1) if latencies else None
                ),
                "source_availability": round(successes / total_events, 4) if total_events else 0.0,
                "sample_count": len(items),
            }
        return out
    finally:
        conn.close()
