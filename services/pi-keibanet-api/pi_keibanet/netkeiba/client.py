# -*- coding: utf-8 -*-
"""Fetch netkeiba HTML (stdlib urllib)."""
from __future__ import annotations

import os
import time
import urllib.error
import urllib.request
from typing import Callable

from .debug_log import log_fetch

DEFAULT_UA = (
    "Mozilla/5.0 (compatible; Expect-PI-KeibaNet/1.0; +https://expect-keiba.com)"
)
RACE_LIST_SUB_URL = "https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={date}"
RACE_LIST_SP_URL = "https://race.sp.netkeiba.com/?pid=race_list&kaisai_date={date}"
SHUTUBA_URL = "https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"


class NetkeibaFetchError(Exception):
    pass


class NetkeibaClient:
    def __init__(
        self,
        *,
        timeout: float | None = None,
        min_interval_sec: float | None = None,
        opener: Callable[..., object] | None = None,
    ) -> None:
        self.timeout = float(timeout or os.environ.get("PI_NETKEIBA_TIMEOUT", "25"))
        self.min_interval = float(
            min_interval_sec or os.environ.get("PI_NETKEIBA_MIN_INTERVAL_SEC", "1.0")
        )
        self.user_agent = os.environ.get("PI_NETKEIBA_USER_AGENT", DEFAULT_UA)
        self._last_fetch = 0.0
        self._opener = opener or urllib.request.urlopen

    def fetch(self, url: str, *, label: str = "netkeiba") -> str:
        elapsed = time.monotonic() - self._last_fetch
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml",
                "Referer": "https://race.netkeiba.com/",
            },
            method="GET",
        )
        try:
            with self._opener(req, timeout=self.timeout) as resp:
                raw = resp.read()
                self._last_fetch = time.monotonic()
        except urllib.error.HTTPError as exc:
            raise NetkeibaFetchError(f"HTML取得失敗 HTTP {exc.code}: {url}") from exc
        except urllib.error.URLError as exc:
            raise NetkeibaFetchError(f"HTML取得失敗: {url}: {exc.reason}") from exc
        for enc in ("utf-8", "euc-jp", "cp932"):
            try:
                html = raw.decode(enc)
                break
            except UnicodeDecodeError:
                html = ""
                continue
        else:
            html = raw.decode("utf-8", errors="replace")
        log_fetch(url=url, html=html, label=label)
        return html

    def fetch_race_list(self, date_yyyy_mm_dd: str) -> str:
        token = date_yyyy_mm_dd.replace("-", "")
        sub_url = RACE_LIST_SUB_URL.format(date=token)
        sp_url = RACE_LIST_SP_URL.format(date=token)
        sub_html = self.fetch(sub_url, label=f"race_list_sub_{token}")
        try:
            sp_html = self.fetch(sp_url, label=f"race_list_sp_{token}")
        except NetkeibaFetchError as exc:
            print(f"[pi-keibanet] sp race_list skipped: {exc}")
            sp_html = ""
        return sub_html + "\n<!-- merged -->\n" + sp_html

    def fetch_shutuba(self, numeric_race_id: str) -> str:
        url = SHUTUBA_URL.format(race_id=numeric_race_id)
        return self.fetch(url, label=f"shutuba_{numeric_race_id}")
