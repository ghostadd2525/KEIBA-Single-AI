# -*- coding: utf-8 -*-
"""W2 Shadow — Historical Haron incremental acquisition (Research/Shadow only).

No Feature / Prediction consumers. P1 is highest priority.
"""

from .config import W2Config
from .runner import RunReport, run_w2_shadow

__all__ = ["W2Config", "RunReport", "run_w2_shadow"]
