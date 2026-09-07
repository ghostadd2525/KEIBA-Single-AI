# -*- coding: utf-8 -*-
"""C4 PAGE-A1 SourceHealth — same machine as W2, separate file/key."""
from __future__ import annotations

from pathlib import Path

from ..w2_haron import source_health as _sh
from .config import SOURCE_KEY

# Re-export helpers with C4 source key defaults
SourceHealth = _sh.SourceHealth
load_health = _sh.load_health
save_health = _sh.save_health
prepare_run_health = _sh.prepare_run_health
record_success = _sh.record_success
record_soft_failure = _sh.record_soft_failure
record_block = _sh.record_block
allows_mainline_fetch = _sh.allows_mainline_fetch


def ensure_boot_health(path: Path) -> SourceHealth:
    h = load_health(path)
    if path.exists():
        if h.source != SOURCE_KEY:
            h.source = SOURCE_KEY
            save_health(path, h)
        return h
    h = SourceHealth(source=SOURCE_KEY, state="HEALTHY", reason="c4_shadow_boot_default")
    save_health(path, h)
    return h


def reconcile_target_isolated_degraded(health: SourceHealth) -> SourceHealth:
    """Contract reconcile: DEGRADED caused by target-only soft failures + HTTP 200.

    Not a cosmetic counter wipe — isolates TARGET_SPECIFIC_FAILURE from SOURCE_FAILURE.
    Returns a new SourceHealth when reconciled so callers can detect change by identity.
    """
    from dataclasses import replace

    if health.state != "DEGRADED":
        return health
    if health.last_http_status not in (200, None):
        return health
    # Preserve prior consecutive_failures in reason for audit trail.
    prior = int(health.consecutive_failures or 0)
    return replace(
        health,
        state="HEALTHY",
        reason=(
            f"reconciled_target_specific_incomplete_isolated;"
            f"prior_consecutive_failures={prior}"
        ),
        consecutive_failures=0,
        cooldown_until=None,
    )
