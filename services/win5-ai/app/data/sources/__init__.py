# -*- coding: utf-8 -*-
"""Data source registry — 環境に応じた取得元を選択。"""
from __future__ import annotations

import os
from pathlib import Path

from .api_source import APISource
from .base import DataSource, DownloadResult, source_summary
from .csv_source import CSVSource
from .database_source import DatabaseSource
from .jra_source import FutureJRASource

__all__ = [
    "DataSource",
    "DownloadResult",
    "CSVSource",
    "DatabaseSource",
    "APISource",
    "FutureJRASource",
    "get_source",
    "list_sources",
    "resolve_sources",
    "source_summary",
]

_REGISTRY: dict[str, type] = {
    "csv": CSVSource,
    "database": DatabaseSource,
    "api": APISource,
    "jra": FutureJRASource,
}


def get_source(source_type: str | None = None, **kwargs) -> DataSource:
    raw = (source_type or os.environ.get("EXPECT_AI_DATA_SOURCE") or "csv").lower()
    cls = _REGISTRY.get(raw, CSVSource)
    if cls is CSVSource:
        data_dir = kwargs.get("data_dir")
        return CSVSource(Path(data_dir) if data_dir else None)
    if cls is APISource:
        return APISource(kwargs.get("base_url"))
    return cls()


def list_sources() -> list[dict]:
    out = []
    for name, cls in _REGISTRY.items():
        inst = get_source(name) if name != "csv" else CSVSource()
        out.append({"source_type": name, "available": inst.available()})
    return out


def resolve_sources(source_type: str | None = None) -> list[DataSource]:
    """Primary + fallback chain."""
    primary = (source_type or os.environ.get("EXPECT_AI_DATA_SOURCE") or "csv").lower()
    chain = [primary]
    for fb in ("csv", "database", "api"):
        if fb not in chain:
            chain.append(fb)
    sources: list[DataSource] = []
    seen: set[str] = set()
    for name in chain:
        if name in seen:
            continue
        seen.add(name)
        src = get_source(name)
        if src.available():
            sources.append(src)
    return sources or [CSVSource()]
