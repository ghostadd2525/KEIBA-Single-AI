# -*- coding: utf-8 -*-
"""Statistics Tool — Stub（実接続禁止）。"""
from __future__ import annotations

from typing import Any

from .base import ToolResult


class StatisticsTool:
    name = "statistics"
    read_only = True
    stub = True

    def invoke(self, **kwargs: Any) -> ToolResult:
        race_id = kwargs.get("race_id")
        return ToolResult(
            ok=True,
            tool=self.name,
            data={
                "stub": True,
                "connected": False,
                "race_id": race_id,
                "stats": {},
                "message": "Statistics Tool は stub です。実接続は禁止されています。",
            },
            stub=True,
            read_only=True,
            mutated=False,
        )
