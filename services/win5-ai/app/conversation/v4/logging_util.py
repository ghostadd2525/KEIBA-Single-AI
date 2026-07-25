# -*- coding: utf-8 -*-
"""Structured conversation logs（本文は既定で保存しない）。"""
from __future__ import annotations

import json
import sys
from typing import Any


def log_conversation_event(**fields: Any) -> None:
    payload = {"event": "conversation.v4", **fields}
    try:
        sys.stderr.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
