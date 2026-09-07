# -*- coding: utf-8 -*-
"""W3 — C4 maiden handoff (A) + PAGE-C cache parse (B) + bounded acquire (C)."""

from .acquisition import AcquireReport, run_w3c_acquire
from .config import W3AConfig
from .handoff import HandoffReport, run_w3a_handoff
from .result_runner import ParseReport, run_w3b_parse

__all__ = [
    "W3AConfig",
    "HandoffReport",
    "run_w3a_handoff",
    "ParseReport",
    "run_w3b_parse",
    "AcquireReport",
    "run_w3c_acquire",
]
