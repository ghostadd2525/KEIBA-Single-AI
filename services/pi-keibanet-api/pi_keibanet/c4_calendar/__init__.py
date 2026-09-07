# -*- coding: utf-8 -*-
"""C4 Shadow — Historical PAGE-A1 Hybrid Calendar Recovery (Research only).

No Feature / Prediction / PAGE-C consumers. P1 >>> W2 > C4.
"""

from .config import C4Config

__all__ = ["C4Config", "RunReport", "run_c4_shadow"]


def __getattr__(name: str):
    if name in ("RunReport", "run_c4_shadow"):
        from . import runner

        return getattr(runner, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
