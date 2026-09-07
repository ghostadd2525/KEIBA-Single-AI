# -*- coding: utf-8 -*-
"""Version 3 Lab — Miss Taxonomy Lock (P1).

Layer labels for residual misses under V2 Final Control (Hit 218).
Counts are frozen placeholders until the 285R corpus is attached offline.
"""
from __future__ import annotations

from typing import Any

# Control baseline (V2 Final PE-V2-A)
CONTROL_HIT = 218
CONTROL_CORPUS_SIZE = 285
CONTROL_MISS = CONTROL_CORPUS_SIZE - CONTROL_HIT  # 67

MISS_LAYERS = (
    "Eval",       # ranking / calibration insufficiency
    "Boundary",   # near-capacity / margin races
    "Reorder",    # selection order effects (not rescue)
    "Pool",       # not admitted to candidate pool
    "Delete",     # purchase/delete boundary (immutable)
)

# Locked taxonomy scaffold (review table). Counts sum to CONTROL_MISS.
# These are structural placeholders for harness accounting — not Accuracy claims.
TAXONOMY_LOCK: dict[str, int] = {
    "Eval": 28,
    "Boundary": 14,
    "Reorder": 10,
    "Pool": 9,
    "Delete": 6,
}


def taxonomy_snapshot() -> dict[str, Any]:
    total = sum(TAXONOMY_LOCK.values())
    return {
        "control_hit": CONTROL_HIT,
        "corpus_size": CONTROL_CORPUS_SIZE,
        "control_miss": CONTROL_MISS,
        "layers": list(MISS_LAYERS),
        "counts": dict(TAXONOMY_LOCK),
        "counts_sum": total,
        "locked": total == CONTROL_MISS,
        "note": "P1 lock scaffold — attach 285R labels in offline ops; no Accuracy intervention",
    }


def validate_taxonomy_lock() -> list[str]:
    errors: list[str] = []
    snap = taxonomy_snapshot()
    if snap["counts_sum"] != CONTROL_MISS:
        errors.append(
            f"taxonomy counts sum {snap['counts_sum']} != control_miss {CONTROL_MISS}"
        )
    for layer in MISS_LAYERS:
        if layer not in TAXONOMY_LOCK:
            errors.append(f"missing layer {layer}")
    return errors


__all__ = [
    "CONTROL_HIT",
    "CONTROL_CORPUS_SIZE",
    "CONTROL_MISS",
    "MISS_LAYERS",
    "TAXONOMY_LOCK",
    "taxonomy_snapshot",
    "validate_taxonomy_lock",
]
