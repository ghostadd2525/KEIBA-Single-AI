# -*- coding: utf-8 -*-
"""Single-model retraining gate — run only after dataset is ready."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def training_output_dir() -> Path:
    return Path(
        os.environ.get("EXPECT_AI_TRAINING_DIR")
        or Path(__file__).resolve().parents[2] / "var" / "training"
    )


def load_dataset_report(path: Path | None = None) -> dict[str, Any] | None:
    report_path = path or training_output_dir() / "dataset_report.json"
    if not report_path.exists():
        return None
    return json.loads(report_path.read_text(encoding="utf-8"))


def is_dataset_ready_for_training(
    *,
    report_path: Path | None = None,
    min_rows: int | None = None,
) -> dict[str, Any]:
    report = load_dataset_report(report_path)
    if report is None:
        return {
            "ready": False,
            "reason": "dataset_report_missing",
            "hint": "Run scripts/ops/run_training_dataset.py first",
        }
    floor = min_rows if min_rows is not None else int(report.get("min_rows_for_training") or 500)
    rows = int((report.get("totals") or {}).get("rows") or 0)
    ready = bool(report.get("ready_for_training")) and rows >= floor
    return {
        "ready": ready,
        "reason": "ok" if ready else "insufficient_rows",
        "rows": rows,
        "min_rows": floor,
        "report_path": str(report_path or training_output_dir() / "dataset_report.json"),
    }


def retrain_single_model_if_ready(**kwargs: Any) -> dict[str, Any]:
    """
    Placeholder for Single dedicated model retraining.
    Actual LGBM training runs after PC-3B dataset gate passes.
    """
    gate = is_dataset_ready_for_training(**kwargs)
    if not gate["ready"]:
        return {"ok": False, "skipped": True, **gate}
    return {
        "ok": True,
        "skipped": True,
        "reason": "dataset_ready_retrain_pending",
        "message": "Dataset is ready. Invoke platform train_win5_lgbm_ranker.py with var/training/train.csv",
        **gate,
    }
