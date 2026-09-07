# -*- coding: utf-8 -*-
"""UI1 Existing UI Adaptation — View Mapper package."""
from __future__ import annotations

from app.ui_adaptation.handlers import (
    handle_map_prediction_bundle,
    try_dispatch_get,
    try_dispatch_post,
)
from app.ui_adaptation.single_to_bundle import (
    assert_no_internal_terms_leaked,
    map_single_to_prediction_bundle,
    sanitize_bundle_for_existing_ui,
)

__all__ = [
    "assert_no_internal_terms_leaked",
    "handle_map_prediction_bundle",
    "map_single_to_prediction_bundle",
    "sanitize_bundle_for_existing_ui",
    "try_dispatch_get",
    "try_dispatch_post",
]
