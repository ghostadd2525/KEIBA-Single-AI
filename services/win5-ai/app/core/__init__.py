# -*- coding: utf-8 -*-
"""Core package — FeatureLoader bridge registration."""
from __future__ import annotations

from . import feature_loader_bridge  # noqa: F401 — registers DB provider on import

__all__ = ["feature_loader_bridge"]
