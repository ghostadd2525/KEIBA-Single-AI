# -*- coding: utf-8 -*-
"""KeibaNet HTTP client — transport only (no JSON parsing or validation)."""
from __future__ import annotations

import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urljoin

from ..budget import CollectBudget, BudgetExhaustedError


class KeibaNetError(Exception):
    """Base error for KeibaNet transport."""


class KeibaNetQuotaError(KeibaNetError):
    """Daily request budget exhausted (CollectBudget SoT)."""


class KeibaNetTimeoutError(KeibaNetError):
    """Request timed out."""


@dataclass(frozen=True)
class KeibaNetResponse:
    status_code: int
    body: bytes
    headers: dict[str, str]
    url: str

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


class KeibaNetClient:
    """
    HTTP transport for KeibaNet.

    Budget: CollectBudget を共有参照（SoT）。独自カウンタは持たない。
    消費（consume）は Scheduler.dequeue 側。Client は remaining を検査するのみ。
    """

    DEFAULT_USER_AGENT = "Expect-KeibaNet-Collector/1.0 (C-1)"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        user_agent: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        retry_backoff: float | None = None,
        min_interval_sec: float | None = None,
        budget: CollectBudget | None = None,
        daily_limit: int | None = None,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("EXPECT_KEIBANET_BASE_URL") or "").strip()
        if not self.base_url:
            raise ValueError("EXPECT_KEIBANET_BASE_URL or base_url is required")
        self.user_agent = (
            user_agent
            or os.environ.get("EXPECT_KEIBANET_USER_AGENT")
            or self.DEFAULT_USER_AGENT
        )
        self.timeout = float(
            timeout
            if timeout is not None
            else os.environ.get("EXPECT_KEIBANET_TIMEOUT", "30")
        )
        self.max_retries = int(
            max_retries
            if max_retries is not None
            else os.environ.get("EXPECT_KEIBANET_MAX_RETRIES", "3")
        )
        self.retry_backoff = float(
            retry_backoff
            if retry_backoff is not None
            else os.environ.get("EXPECT_KEIBANET_RETRY_BACKOFF", "0.5")
        )
        self.min_interval_sec = float(
            min_interval_sec
            if min_interval_sec is not None
            else os.environ.get("EXPECT_KEIBANET_MIN_INTERVAL_SEC", "0")
        )
        if budget is not None:
            self.budget = budget
        else:
            self.budget = CollectBudget.from_env(daily_limit=daily_limit)
        self._last_request_at = 0.0
        self._opener = opener or urllib.request.urlopen

    @property
    def daily_limit(self) -> int:
        return self.budget.daily_limit

    def fetch(self, path: str, *, method: str = "GET", body: bytes | None = None) -> KeibaNetResponse:
        url = path if "://" in path else urljoin(self.base_url.rstrip("/") + "/", path.lstrip("/"))
        self._assert_budget()
        self._wait_rate_limit()

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "*/*",
        }
        req = urllib.request.Request(url, data=body, headers=headers, method=method.upper())

        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with self._opener(req, timeout=self.timeout) as resp:
                    raw = resp.read()
                    status = int(getattr(resp, "status", resp.getcode()))
                    hdrs = {k.lower(): v for k, v in resp.headers.items()}
                    self._last_request_at = time.monotonic()
                    return KeibaNetResponse(
                        status_code=status,
                        body=raw,
                        headers=hdrs,
                        url=url,
                    )
            except TimeoutError as exc:
                last_exc = KeibaNetTimeoutError(f"KeibaNet timeout: {url}")
                last_exc.__cause__ = exc
            except urllib.error.HTTPError as exc:
                payload = exc.read() if exc.fp else b""
                self._last_request_at = time.monotonic()
                if exc.code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    time.sleep(self.retry_backoff * (attempt + 1))
                    continue
                return KeibaNetResponse(
                    status_code=int(exc.code),
                    body=payload,
                    headers={k.lower(): v for k, v in exc.headers.items()},
                    url=url,
                )
            except urllib.error.URLError as exc:
                last_exc = KeibaNetError(f"KeibaNet request failed: {url}: {exc.reason}")
                last_exc.__cause__ = exc
            if attempt < self.max_retries:
                time.sleep(self.retry_backoff * (attempt + 1))

        assert last_exc is not None
        raise last_exc

    def _assert_budget(self) -> None:
        """SoT 検査のみ（consume は Scheduler）。"""
        if self.budget.remaining <= 0 and self.budget.used > 0:
            raise KeibaNetQuotaError(
                f"daily KeibaNet request limit reached ({self.budget.daily_limit})"
            )

    def _wait_rate_limit(self) -> None:
        if self.min_interval_sec <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval_sec:
            time.sleep(self.min_interval_sec - elapsed)


# Re-export for callers that caught BudgetExhaustedError via client path
__all__ = [
    "BudgetExhaustedError",
    "KeibaNetClient",
    "KeibaNetError",
    "KeibaNetQuotaError",
    "KeibaNetResponse",
    "KeibaNetTimeoutError",
]
