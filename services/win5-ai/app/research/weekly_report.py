# -*- coding: utf-8 -*-
"""Weekly Evidence quality report (Research-only)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import report_root
from .quality import aggregate_daily_metrics
from .repository import ResearchEvidenceRepository


def _week_id(d: datetime) -> str:
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def generate_weekly_report(*, end_date: str | None = None) -> dict[str, Any]:
    end = datetime.fromisoformat(end_date) if end_date else datetime.now(timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    start = end - timedelta(days=6)
    repo = ResearchEvidenceRepository()
    daily: dict[str, dict[str, Any]] = {}
    cur = start
    while cur <= end:
        day = cur.date().isoformat()
        metrics = aggregate_daily_metrics(metric_date=day)
        daily[day] = metrics
        for fid, meta in metrics.items():
            repo.upsert_daily_metric(metric_date=day, feature_id=fid, metrics=meta)
        cur += timedelta(days=1)

    report = {
        "schema_version": "expect-research-weekly-report/1.0",
        "week_id": _week_id(end),
        "period_start": start.date().isoformat(),
        "period_end": end.date().isoformat(),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "daily": daily,
        "summary": {
            "days": len(daily),
            "features": sorted({fid for day in daily.values() for fid in day.keys()}),
        },
    }

    out_dir = report_root()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{report['week_id']}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["path"] = str(path)
    return report
