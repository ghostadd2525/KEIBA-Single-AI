# -*- coding: utf-8 -*-
"""CSVSource — platform/data または指定ディレクトリから CSV を取得。"""
from __future__ import annotations

import os
from pathlib import Path

from .base import DownloadResult


class CSVSource:
    source_type = "csv"

    def __init__(self, data_dir: Path | None = None) -> None:
        env = (os.environ.get("AI_PLATFORM_ROOT") or "").strip()
        default = Path(env) / "data" if env else None
        self.data_dir = data_dir or default or Path("data")

    def available(self) -> bool:
        return self.data_dir.is_dir()

    def download(self, race_date: str) -> DownloadResult:
        result = DownloadResult(race_date=race_date, source_type=self.source_type)
        if not self.available():
            result.notes.append(f"data_dir missing: {self.data_dir}")
            return result

        patterns = [
            "races.csv",
            "demo_races.csv",
            "Demo_races*.csv",
            "runners_pace_market_features.csv",
            "demo_runners_pace_market_features.csv",
            "Runners_pace_market_features.csv",
        ]
        for pat in patterns:
            for p in sorted(self.data_dir.glob(pat)):
                name = p.name.lower()
                if "runner" in name or "feature" in name:
                    result.feature_files.append(str(p))
                else:
                    result.race_files.append(str(p))

        sub = self.data_dir / race_date
        if sub.is_dir():
            for p in sorted(sub.glob("*.csv")):
                name = p.name.lower()
                if "runner" in name or "feature" in name:
                    result.feature_files.append(str(p))
                else:
                    result.race_files.append(str(p))

        result.notes.append(
            f"found {len(result.race_files)} race files, {len(result.feature_files)} feature files"
        )
        return result
