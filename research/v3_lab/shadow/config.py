# -*- coding: utf-8 -*-
"""A-05 Shadow runtime settings (independent of production Flag defaults).

F_V3_A05_ADM_FAVSAFE_ENABLED remains default OFF in flags.py.
This module only controls whether the Shadow harness may execute.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

LAB_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = LAB_ROOT / "baselines" / "a05_shadow" / "logs"

# Rollout Plan phases (design)
VALID_PHASES = ("S0", "S1", "S2")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class ShadowSettings:
    """Shadow-only config. Never mutates production Flag defaults."""

    # Independent of F_V3_A05_ADM_FAVSAFE_ENABLED (production mesh)
    shadow_runtime_enabled: bool = False
    phase: str = "S0"  # S0 dry-run / S1 hard-gate / S2 observe
    log_dir: str = str(DEFAULT_LOG_DIR)
    stake_yen: float = 100.0
    # Acceptance / ops thresholds (Rollout Plan)
    min_window_days: int = 14
    min_labeled_races: int = 285
    max_shadow_error_rate: float = 0.05
    max_input_mismatch_rate: float = 0.0
    # Safety
    purchase_forbidden: bool = True
    fail_open: bool = True
    forbid_a03_with_a05: bool = True
    # Soft promote-rate watchband (Offline ~ few % after FavSafe; informational)
    promote_rate_warn_max: float = 0.25

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_shadow_settings(**overrides: Any) -> ShadowSettings:
    """Load settings. Env: WIN5_V3_A05_SHADOW_RUNTIME_ENABLED (default false)."""
    enabled = _env_bool("WIN5_V3_A05_SHADOW_RUNTIME_ENABLED", False)
    phase = str(os.environ.get("WIN5_V3_A05_SHADOW_PHASE") or "S0").strip().upper()
    if phase not in VALID_PHASES:
        phase = "S0"
    log_dir = os.environ.get("WIN5_V3_A05_SHADOW_LOG_DIR") or str(DEFAULT_LOG_DIR)
    settings = ShadowSettings(
        shadow_runtime_enabled=enabled,
        phase=phase,
        log_dir=log_dir,
    )
    for k, v in overrides.items():
        if hasattr(settings, k) and v is not None:
            setattr(settings, k, v)
    if settings.phase not in VALID_PHASES:
        settings.phase = "S0"
    return settings


__all__ = ["ShadowSettings", "load_shadow_settings", "VALID_PHASES", "DEFAULT_LOG_DIR"]
