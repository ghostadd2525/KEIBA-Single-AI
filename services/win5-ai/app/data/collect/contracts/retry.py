# -*- coding: utf-8 -*-
"""
Retry Policy Contract — FAILED / PARTIAL → retry_after (C-8 正本).

設計: 翌日（翌営業日）retry。CollectRetry は retry_after 到達後に PENDING へ戻す。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class RetryPolicy:
    """
    Availability と独立した再試行契約。

    next_business_day: 失敗日の翌営業日（月〜金）を retry_after にする。
    """

    strategy: str = "next_business_day"
    max_attempts: int = 5


DEFAULT_RETRY_POLICY = RetryPolicy()


def parse_date(value: str | date | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()


def next_business_day(from_date: date | str | None = None) -> date:
    """from_date の翌日以降で最初の平日（月=0 … 金=4）。"""
    d = parse_date(from_date) + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def compute_retry_after(
    *,
    as_of: date | str | None = None,
    attempt: int = 0,
    policy: RetryPolicy | None = None,
) -> str:
    """
    FAILED / PARTIAL 確定時に設定する retry_after（YYYY-MM-DD）。

    attempt が進むと追加の営業日を挟む（1 回目=翌営業日、2 回目=2 営業日後…）。
    """
    pol = policy or DEFAULT_RETRY_POLICY
    base = parse_date(as_of)
    # attempt は RUNNING 遷移時に既に +1 済みの値を想定
    steps = max(1, int(attempt) if attempt else 1)
    d = base
    for _ in range(steps):
        d = next_business_day(d)
    # policy.strategy は現時点 next_business_day のみ
    _ = pol.strategy
    return d.isoformat()
