# -*- coding: utf-8 -*-
"""PI / KeibaNet HTTP client for Research Evidence collection."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any


class ResearchPiClient:
    def __init__(self, *, base_url: str, timeout_sec: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    def _get(self, path: str) -> tuple[dict[str, Any] | None, float, str | None]:
        url = f"{self.base_url}{path}"
        t0 = time.monotonic()
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                body = resp.read().decode("utf-8")
            ms = (time.monotonic() - t0) * 1000.0
            data = json.loads(body)
            if isinstance(data, dict):
                return data, ms, None
            return None, ms, "invalid_json_shape"
        except urllib.error.HTTPError as exc:
            ms = (time.monotonic() - t0) * 1000.0
            return None, ms, f"http_{exc.code}"
        except urllib.error.URLError as exc:
            ms = (time.monotonic() - t0) * 1000.0
            return None, ms, f"url_error:{exc.reason}"
        except TimeoutError:
            ms = (time.monotonic() - t0) * 1000.0
            return None, ms, "timeout"
        except json.JSONDecodeError:
            ms = (time.monotonic() - t0) * 1000.0
            return None, ms, "json_decode_error"

    def fetch_race_board(self, race_id: str) -> tuple[dict[str, Any] | None, float, str | None]:
        return self._get(f"/v1/races/{race_id}/board")
