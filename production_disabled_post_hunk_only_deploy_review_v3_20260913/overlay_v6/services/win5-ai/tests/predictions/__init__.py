# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

_WIN5 = Path(__file__).resolve().parents[2]
s = str(_WIN5)
if s not in sys.path:
    sys.path.insert(0, s)
