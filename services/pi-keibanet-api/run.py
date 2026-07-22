"""Entry: python services/pi-keibanet-api/run.py"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

runpy.run_module("pi_keibanet.server", run_name="__main__")
