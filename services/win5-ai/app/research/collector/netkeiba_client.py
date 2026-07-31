# -*- coding: utf-8 -*-
"""Lightweight netkeiba HTTP client for Research Evidence (stdlib only)."""
from __future__ import annotations

import os
import time
import urllib.error
import urllib.request

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class ResearchNetkeibaError(Exception):
    pass


class ResearchNetkeibaClient:
    """CloudFront-aware fetch matching PI NetkeibaClient header strategy."""

    def __init__(
        self,
        *,
        timeout: float | None = None,
        min_interval_sec: float | None = None,
    ) -> None:
        self.timeout = float(
            timeout or os.environ.get("RESEARCH_NETKEIBA_TIMEOUT", "25")
        )
        self.min_interval = float(
            min_interval_sec
            or os.environ.get("RESEARCH_NETKEIBA_MIN_INTERVAL_SEC", "0.6")
        )
        self.user_agent = os.environ.get("RESEARCH_NETKEIBA_UA", DEFAULT_UA)
        self._last_fetch = 0.0

    def fetch(self, url: str, *, label: str = "netkeiba") -> str:
        elapsed = time.monotonic() - self._last_fetch
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        is_db = "db.netkeiba.com" in url and "db.sp.netkeiba.com" not in url
        if is_db:
            accept = "application/json, text/javascript, */*;q=0.01"
            referer = "https://db.netkeiba.com/"
            xrw = "XMLHttpRequest"
        else:
            accept = "text/html,application/xhtml+xml"
            referer = "https://race.netkeiba.com/"
            xrw = "fetch"

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
                "Accept": accept,
                "Referer": referer,
                "X-Requested-With": xrw,
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                self._last_fetch = time.monotonic()
        except urllib.error.HTTPError as exc:
            raise ResearchNetkeibaError(f"HTTP {exc.code}: {url} ({label})") from exc
        except urllib.error.URLError as exc:
            raise ResearchNetkeibaError(f"URL error: {url}: {exc.reason}") from exc

        for enc in ("utf-8", "euc-jp", "cp932"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")

    def fetch_horse_profile(self, horse_id: str) -> str:
        hid = str(horse_id).strip()
        return self.fetch(
            f"https://db.netkeiba.com/horse/{hid}",
            label=f"horse_profile_{hid}",
        )

    def fetch_horse_pedigree_ajax(self, horse_id: str) -> str:
        hid = str(horse_id).strip()
        return self.fetch(
            f"https://db.netkeiba.com/horse/ajax_horse_pedigree.html?id={hid}",
            label=f"horse_pedigree_{hid}",
        )

    def fetch_oikiri(self, numeric_race_id: str, *, type_: int = 1) -> str:
        rid = str(numeric_race_id).strip()
        return self.fetch(
            f"https://race.netkeiba.com/race/oikiri.html?race_id={rid}&type={int(type_)}",
            label=f"oikiri_{rid}_t{type_}",
        )
