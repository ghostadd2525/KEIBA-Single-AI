#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PC-3B Training Dataset Builder — collect, label, split, report.

Usage:
  cd services/win5-ai
  python scripts/ops/run_training_dataset.py
  python scripts/ops/run_training_dataset.py --year-from 2023 --year-to 2025
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Prediction Core training dataset")
    parser.add_argument("--year-from", type=int, default=None)
    parser.add_argument("--year-to", type=int, default=None)
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--min-rows", type=int, default=500)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    from app.data.training.dataset_builder import TrainingDatasetBuilder

    builder = TrainingDatasetBuilder()
    result = builder.build(
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        min_rows_for_training=args.min_rows,
        year_from=args.year_from,
        year_to=args.year_to,
        write_csv=not args.no_write,
    )
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    if result.output_dir:
        print(f"dataset: {result.output_dir}", file=sys.stderr)
    return 0 if result.report.get("ready_for_training") else 2


if __name__ == "__main__":
    raise SystemExit(main())
