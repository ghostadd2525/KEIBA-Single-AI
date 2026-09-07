# -*- coding: utf-8 -*-
"""A-05 Shadow package (Lab-only).

Parallel evaluation vs Control. Does not wire Production / Purchase / API.
F_V3_A05_ADM_FAVSAFE_ENABLED default remains OFF.
"""
from __future__ import annotations

from .comparator import build_race_diff_record, classify_diff
from .config import ShadowSettings, load_shadow_settings
from .harness import run_shadow_batch, write_shadow_artifacts
from .logger import ShadowLogger
from .metrics import aggregate_shadow_metrics, evaluate_acceptance
from .runner import run_shadow_race

__all__ = [
    "ShadowSettings",
    "load_shadow_settings",
    "ShadowLogger",
    "run_shadow_race",
    "run_shadow_batch",
    "write_shadow_artifacts",
    "build_race_diff_record",
    "classify_diff",
    "aggregate_shadow_metrics",
    "evaluate_acceptance",
]
