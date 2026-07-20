# -*- coding: utf-8 -*-
"""Data source abstraction — Prediction は取得元を意識しない。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class DownloadResult:
    """Download ステップの成果物。"""

    race_date: str
    source_type: str
    race_files: list[str] = field(default_factory=list)
    feature_files: list[str] = field(default_factory=list)
    race_rows: list[dict[str, Any]] = field(default_factory=list)
    feature_rows: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class DataSource(Protocol):
    """データ取得元の共通インターフェース。"""

    @property
    def source_type(self) -> str:
        ...

    def download(self, race_date: str) -> DownloadResult:
        """開催日データを取得（ファイルパスまたは行データ）。"""
        ...

    def available(self) -> bool:
        """このソースが現環境で利用可能か。"""
        ...


def source_summary(source: DataSource) -> dict[str, Any]:
    return {
        "source_type": source.source_type,
        "available": source.available(),
    }
