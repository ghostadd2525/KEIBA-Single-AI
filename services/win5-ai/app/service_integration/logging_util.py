# -*- coding: utf-8 -*-
"""A1 Application logging helpers."""
from __future__ import annotations

import json
import time
from typing import Any

from app.consumer.decision_service.dto import version_info_dict
from app.consumer.flags import snapshot_all_flags


def log_event(event: str, **fields: Any) -> None:
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "layer": "service_integration",
        "event": event,
        "flags": snapshot_all_flags(),
        "version": version_info_dict(),
        **fields,
    }
    print("[single-ai-http] " + json.dumps(row, ensure_ascii=False))
