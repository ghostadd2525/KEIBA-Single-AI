# -*- coding: utf-8 -*-
"""Fetch netkeiba HTML (stdlib urllib)."""
from __future__ import annotations

import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

from ..http_budget import BudgetDenied, classify_http_result, public_url, reserve_for_request
from .debug_log import log_fetch

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
RACE_LIST_SUB_URL = "https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={date}"
RACE_LIST_SP_URL = "https://race.sp.netkeiba.com/?pid=race_list&kaisai_date={date}"
SHUTUBA_URL = "https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
SHUTUBA_SP_URL = "https://race.sp.netkeiba.com/race/shutuba.html?race_id={race_id}"
JRA_ODDS_API_URL = (
    "https://race.netkeiba.com/api/api_get_jra_odds.html"
    "?race_id={race_id}&type=1&action=init"
)


@dataclass
class RaceListPart:
    source: str
    url: str
    html: str


@dataclass
class RaceListFetchResult:
    """Merged HTML for existing parsers + per-part RAW bodies (no extra HTTP)."""

    merged_html: str
    parts: list[RaceListPart] = field(default_factory=list)
    kaisai_date: str = ""


class NetkeibaFetchError(Exception):
    """Netkeiba HTTP/URL failure. ``http_status`` set for HTTPError responses."""

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        self.http_status = http_status


class NetkeibaClient:
    def __init__(
        self,
        *,
        timeout: float | None = None,
        min_interval_sec: float | None = None,
        opener: Callable[..., object] | None = None,
        component: str | None = None,
    ) -> None:
        self.timeout = float(timeout or os.environ.get("PI_NETKEIBA_TIMEOUT", "25"))
        self.min_interval = float(
            min_interval_sec or os.environ.get("PI_NETKEIBA_MIN_INTERVAL_SEC", "1.0")
        )
        self.user_agent = os.environ.get("PI_NETKEIBA_USER_AGENT", DEFAULT_UA)
        self._last_fetch = 0.0
        self._opener = opener or urllib.request.urlopen
        self.component = component

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_fetch
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    def _open_budgeted(self, req: urllib.request.Request, *, url: str, label: str) -> bytes:
        """Reserve immediately before opener. No reserve ⇒ no HTTP."""
        reservation = reserve_for_request(url=url, component=self.component, label=label)
        try:
            with self._opener(req, timeout=self.timeout) as resp:
                raw = resp.read()
                self._last_fetch = time.monotonic()
        except BudgetDenied:
            raise
        except urllib.error.HTTPError as exc:
            reservation.complete(
                result=classify_http_result(http_status=int(exc.code)),
                http_status=int(exc.code),
            )
            raise
        except urllib.error.URLError as exc:
            timeout = _is_timeout(exc)
            reservation.complete(result=classify_http_result(timeout=timeout))
            raise
        except TimeoutError:
            reservation.complete(result="timeout")
            raise
        except Exception:
            reservation.complete(result="reserved_no_http")
            raise
        reservation.complete(result="success", http_status=200)
        return raw

    def fetch(self, url: str, *, label: str = "netkeiba", accept: str | None = None) -> str:
        self._throttle()
        is_db_pc = "db.netkeiba.com" in url and "db.sp.netkeiba.com" not in url
        is_db_sp = "db.sp.netkeiba.com" in url
        if accept:
            accept_header = accept
        elif is_db_pc:
            accept_header = "application/json, text/javascript, */*;q=0.01"
        else:
            accept_header = "text/html,application/xhtml+xml"
        if is_db_pc:
            referer = "https://db.netkeiba.com/"
        elif is_db_sp:
            referer = "https://db.sp.netkeiba.com/"
        else:
            referer = "https://race.netkeiba.com/"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
                "Accept": accept_header,
                "Referer": referer,
                "X-Requested-With": "XMLHttpRequest" if is_db_pc else "fetch",
            },
            method="GET",
        )
        try:
            raw = self._open_budgeted(req, url=url, label=label)
        except BudgetDenied:
            raise
        except urllib.error.HTTPError as exc:
            raise NetkeibaFetchError(
                f"HTML取得失敗 HTTP {exc.code}: {public_url(url)}",
                http_status=int(exc.code),
            ) from exc
        except urllib.error.URLError as exc:
            raise NetkeibaFetchError(
                f"HTML取得失敗: {public_url(url)}: {exc.reason}"
            ) from exc
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

    def fetch_race_list_result(self, date_yyyy_mm_dd: str) -> RaceListFetchResult:
        """Fetch race_list with per-part RAW preserved (same GETs as fetch_race_list)."""
        token = date_yyyy_mm_dd.replace("-", "")
        sub_url = RACE_LIST_SUB_URL.format(date=token)
        sp_url = RACE_LIST_SP_URL.format(date=token)
        parts: list[RaceListPart] = []
        # PC版 race_list_sub は 400 になることがある → SP を正にフォールバック
        try:
            html = self.fetch(sub_url, label=f"race_list_sub_{token}")
            parts.append(RaceListPart(source="race_list_sub", url=sub_url, html=html))
        except NetkeibaFetchError as exc:
            print(f"[pi-keibanet] race_list_sub skipped: {exc}")
        try:
            html = self.fetch(sp_url, label=f"race_list_sp_{token}")
            parts.append(RaceListPart(source="race_list_sp", url=sp_url, html=html))
        except NetkeibaFetchError as exc:
            print(f"[pi-keibanet] race_list_sp skipped: {exc}")
        if not parts:
            raise NetkeibaFetchError(
                f"HTML取得失敗: race list unavailable for {date_yyyy_mm_dd}"
            )
        merged = "\n<!-- merged -->\n".join(p.html for p in parts)
        return RaceListFetchResult(
            merged_html=merged,
            parts=parts,
            kaisai_date=date_yyyy_mm_dd[:10],
        )

    def fetch_race_list(self, date_yyyy_mm_dd: str) -> str:
        """Backward-compatible: returns merged HTML only (same HTTP as fetch_race_list_result)."""
        return self.fetch_race_list_result(date_yyyy_mm_dd).merged_html

    def fetch_shutuba(self, numeric_race_id: str) -> str:
        url = SHUTUBA_URL.format(race_id=numeric_race_id)
        try:
            return self.fetch(url, label=f"shutuba_{numeric_race_id}")
        except NetkeibaFetchError as exc:
            print(f"[pi-keibanet] shutuba pc skipped: {exc}")
            sp_url = SHUTUBA_SP_URL.format(race_id=numeric_race_id)
            return self.fetch(sp_url, label=f"shutuba_sp_{numeric_race_id}")

    def fetch_jra_odds_json(self, numeric_race_id: str) -> str:
        """単勝オッズ JSON（api_get_jra_odds）。HTML 出馬表には載らないことが多い。"""
        url = JRA_ODDS_API_URL.format(race_id=numeric_race_id)
        self._throttle()
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
                "Accept": "application/json,text/javascript,*/*;q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": (
                    "https://race.netkeiba.com/odds/index.html"
                    f"?type=b1&race_id={numeric_race_id}&rf=shutuba_submenu"
                ),
            },
            method="GET",
        )
        try:
            raw = self._open_budgeted(req, url=url, label=f"jra_odds_{numeric_race_id}")
        except BudgetDenied:
            raise
        except urllib.error.HTTPError as exc:
            raise NetkeibaFetchError(
                f"オッズ取得失敗 HTTP {exc.code}: {public_url(url)}",
                http_status=int(exc.code),
            ) from exc
        except urllib.error.URLError as exc:
            raise NetkeibaFetchError(
                f"オッズ取得失敗: {public_url(url)}: {exc.reason}"
            ) from exc
        text = raw.decode("utf-8", errors="replace")
        log_fetch(url=url, html=text[:4000], label=f"jra_odds_{numeric_race_id}")
        return text


def _is_timeout(exc: BaseException) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    reason = getattr(exc, "reason", None)
    if isinstance(reason, TimeoutError):
        return True
    text = str(exc).lower()
    return "timed out" in text or "timeout" in type(exc).__name__.lower()
