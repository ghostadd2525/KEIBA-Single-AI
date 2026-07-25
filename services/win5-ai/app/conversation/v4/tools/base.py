# -*- coding: utf-8 -*-
"""Tool Layer — 共通型。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolCapability:
    name: str
    description: str
    read_only: bool
    stub: bool
    intents: tuple[str, ...] = ()
    modes: tuple[str, ...] = ()


@dataclass
class ToolResult:
    ok: bool
    tool: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    stub: bool = False
    read_only: bool = True
    mutated: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "tool": self.tool,
            "data": self.data,
            "error": self.error,
            "stub": self.stub,
            "read_only": self.read_only,
            "mutated": self.mutated,
        }


class Tool(Protocol):
    name: str
    read_only: bool
    stub: bool

    def invoke(self, **kwargs: Any) -> ToolResult:
        ...
