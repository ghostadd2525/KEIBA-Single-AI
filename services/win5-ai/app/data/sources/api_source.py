# -*- coding: utf-8 -*-
"""APISource — HTTP 経由で開催日データを取得（スタブ + 環境変数 URL）。"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .base import DownloadResult


class APISource:
    source_type = "api"

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.environ.get("EXPECT_AI_DATA_API_URL") or "").strip()

    def available(self) -> bool:
        return bool(self.base_url)

    def download(self, race_date: str) -> DownloadResult:
        result = DownloadResult(race_date=race_date, source_type=self.source_type)
        if not self.available():
            result.notes.append("EXPECT_AI_DATA_API_URL not configured")
            return result

        for kind in ("races", "features"):
            url = f"{self.base_url.rstrip('/')}/v1/data/{kind}?date={race_date}"
            try:
                with urllib.request.urlopen(url, timeout=30) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                rows = body.get("data") or body.get("rows") or []
                if kind == "races":
                    result.race_rows.extend(rows)
                else:
                    result.feature_rows.extend(rows)
                result.notes.append(f"api {kind}: {len(rows)} rows")
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                result.notes.append(f"api {kind} failed: {exc}")

        return result
