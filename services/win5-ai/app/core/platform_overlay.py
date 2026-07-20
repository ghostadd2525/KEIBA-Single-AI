# -*- coding: utf-8 -*-
"""Apply Prediction Core overlay files onto AI_PLATFORM_ROOT at startup."""
from __future__ import annotations

import shutil
from pathlib import Path


def apply_platform_overlay(platform_root: Path, overlay_root: Path) -> list[str]:
    """
    Copy overlay files into ``platform_root/ai_platform/``.
    Returns list of applied relative paths.
    """
    src_root = overlay_root / "ai_platform"
    if not src_root.is_dir():
        return []
    target_root = platform_root / "ai_platform"
    if not target_root.is_dir():
        return []

    applied: list[str] = []
    for src in src_root.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(src_root)
        dst = target_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        applied.append(str(rel).replace("\\", "/"))
    return applied
