# -*- coding: utf-8 -*-
"""
不足データ自動収集 — real_ai 化に必要な差分を可視化する。
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .reasons import REASON_HELP


def _reports_dir() -> Path:
    env = (os.environ.get("EXPECT_AI_REPORT_DIR") or "").strip()
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "var" / "reports"


def _platform_data_dir() -> Path | None:
    root = (os.environ.get("AI_PLATFORM_ROOT") or "").strip()
    if not root:
        return None
    data = Path(root) / "data"
    return data if data.is_dir() else None


def collect_missing_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    """
    provenance items（engine_source / fallback_reason）から不足一覧を生成しディスクへ保存。
    """
    now = datetime.now(timezone.utc).isoformat()
    fallbacks = [i for i in items if i.get("engine_source") == "mock_fallback"]
    by_reason: dict[str, list[dict[str, Any]]] = {}
    for it in fallbacks:
        reason = str(it.get("fallback_reason") or "unknown")
        by_reason.setdefault(reason, []).append(
            {
                "race_id": it.get("race_id"),
                "core_race_id": it.get("core_race_id"),
                "detail": it.get("detail"),
                "remediation": REASON_HELP.get(reason, REASON_HELP["unknown"]),
            }
        )

    data_dir = _platform_data_dir()
    csv_inventory: list[dict[str, Any]] = []
    expected_csvs = [
        "races.csv",
        "demo_races.csv",
        "Demo_races_2026.csv",
        "runners_pace_market_features.csv",
        "Runners_pace_market_features.csv",
        "demo_runners_pace_market_features.csv",
    ]
    if data_dir:
        for name in expected_csvs:
            p = data_dir / name
            csv_inventory.append(
                {
                    "table_or_file": name,
                    "path": str(p),
                    "exists": p.exists(),
                    "size_bytes": p.stat().st_size if p.exists() else 0,
                }
            )
    else:
        csv_inventory.append(
            {
                "table_or_file": "(AI_PLATFORM_ROOT/data)",
                "path": None,
                "exists": False,
                "size_bytes": 0,
                "note": "AI_PLATFORM_ROOT not set",
            }
        )

    missing_features_rows: list[dict[str, Any]] = []
    for reason, rows in by_reason.items():
        if reason in ("feature_csv_missing", "market_feature_missing", "feature_missing", "race_not_found"):
            for r in rows:
                missing_features_rows.append(
                    {
                        "race_id": r["race_id"],
                        "core_race_id": r.get("core_race_id") or "",
                        "fallback_reason": reason,
                        "needed": _needed_assets(reason),
                        "remediation": r["remediation"],
                    }
                )

    missing_tables = [
        {
            "table": "races",
            "needed_when": "race_not_found",
            "count": len(by_reason.get("race_not_found") or []),
        },
        {
            "table": "features",
            "needed_when": "market_feature_missing|feature_csv_missing|feature_missing",
            "count": sum(len(by_reason.get(k) or []) for k in (
                "market_feature_missing",
                "feature_csv_missing",
                "feature_missing",
            )),
        },
        {
            "table": "ai_platform",
            "needed_when": "platform_missing|model_not_loaded",
            "count": sum(len(by_reason.get(k) or []) for k in ("platform_missing", "model_not_loaded")),
        },
    ]

    report = {
        "generated_at": now,
        "summary": {
            "total_items": len(items),
            "real_ai": sum(1 for i in items if i.get("engine_source") == "real_ai"),
            "mock_fallback": len(fallbacks),
            "by_reason": {k: len(v) for k, v in sorted(by_reason.items())},
        },
        "by_reason": by_reason,
        "csv_inventory": csv_inventory,
        "missing_tables": missing_tables,
        "how_to_reach_real_ai": [
            {
                "fallback_reason": reason,
                "count": len(rows),
                "remediation": REASON_HELP.get(reason, REASON_HELP["unknown"]),
                "race_ids": [r["race_id"] for r in rows],
            }
            for reason, rows in sorted(by_reason.items())
        ],
    }

    out = _reports_dir()
    out.mkdir(parents=True, exist_ok=True)
    (out / "missing_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    feat_path = out / "missing_features.csv"
    with feat_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["race_id", "core_race_id", "fallback_reason", "needed", "remediation"],
        )
        writer.writeheader()
        for row in missing_features_rows:
            writer.writerow(row)

    tables_path = out / "missing_tables.csv"
    with tables_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["table", "needed_when", "count"])
        writer.writeheader()
        for row in missing_tables:
            writer.writerow(row)

    report["paths"] = {
        "missing_report": str(out / "missing_report.json"),
        "missing_features": str(feat_path),
        "missing_tables": str(tables_path),
    }
    return report


def _needed_assets(reason: str) -> str:
    mapping = {
        "race_not_found": "races.csv / DB races (date,venue,race_no,race_id)",
        "feature_csv_missing": "runners_pace_market_features.csv",
        "market_feature_missing": "features rows for core_race_id",
        "feature_missing": "feature columns for CorePipeline",
    }
    return mapping.get(reason, "see remediation")
