# -*- coding: utf-8 -*-
"""Race Info Tool — Stub（実接続禁止）。"""
from __future__ import annotations

from typing import Any

from .base import ToolResult


class RaceInfoTool:
    name = "race_info"
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
                "venue": None,
                "race_number": None,
                "distance": None,
                "surface": None,
                "message": "Race Info Tool は stub です。実接続は禁止されています。",
            },
            stub=True,
            read_only=True,
            mutated=False,
        )
