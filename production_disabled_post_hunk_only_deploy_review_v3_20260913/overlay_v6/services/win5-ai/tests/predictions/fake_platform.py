# -*- coding: utf-8 -*-
"""Install the fake AI_PLATFORM_ROOT and re-register FeatureLoader bridge."""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

FAKE_PLATFORM_ROOT = Path(__file__).resolve().parent / "fake_ai_platform"


def ensure_fake_ai_platform() -> Path:
    root = str(FAKE_PLATFORM_ROOT)
    os.environ["AI_PLATFORM_ROOT"] = root
    if root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)
    stale = [name for name in list(sys.modules) if name == "ai_platform" or name.startswith("ai_platform.")]
    for name in stale:
        del sys.modules[name]
    import ai_platform.core.features.feature_loader  # noqa: F401

    import app.core.feature_loader_bridge as bridge

    importlib.reload(bridge)
    bridge.register()
    return FAKE_PLATFORM_ROOT
