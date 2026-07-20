# -*- coding: utf-8 -*-
"""FutureJRASource — 将来の JRA 公式データ連携用スタブ。"""
from __future__ import annotations

import os

from .base import DownloadResult


class FutureJRASource:
    source_type = "jra"

    def available(self) -> bool:
        return (os.environ.get("EXPECT_AI_JRA_ENABLED") or "").lower() in ("1", "true", "yes")

    def download(self, race_date: str) -> DownloadResult:
        result = DownloadResult(race_date=race_date, source_type=self.source_type)
        if not self.available():
            result.notes.append(
                "JRA source not enabled (set EXPECT_AI_JRA_ENABLED=1 when connector is ready)"
            )
            return result
        result.notes.append(f"JRA connector stub: race_date={race_date} — implement in future phase")
        return result
