# -*- coding: utf-8 -*-
"""
Daily KeibaNet request budget — Source of Truth (C-8).

正本: CollectBudget（EXPECT_COLLECT_DAILY_LIMIT、既定 150）。
Manifest / Scheduler / KeibaNetClient は同一 CollectBudget を共有する。
Client は独自カウンタを持たない。
"""
from __future__ import annotations

import os
from dataclasses import dataclass


# 推奨 150 / 設計上限 200
DEFAULT_DAILY_LIMIT = 150
MAX_DAILY_LIMIT = 200

# 互換: 旧 Client 用 env は SoT へフォールバック参照のみ（正本キーは COLLECT）
_SOT_ENV = "EXPECT_COLLECT_DAILY_LIMIT"
_LEGACY_ENV = "EXPECT_KEIBANET_DAILY_LIMIT"


class BudgetExhaustedError(RuntimeError):
    """Daily budget cannot afford the next job."""


def resolve_daily_limit(explicit: int | None = None) -> int:
    """SoT 解決。explicit > EXPECT_COLLECT_DAILY_LIMIT > legacy > default。"""
    if explicit is not None:
        return max(0, int(explicit))
    raw = (os.environ.get(_SOT_ENV) or "").strip()
    if raw:
        return max(0, int(raw))
    legacy = (os.environ.get(_LEGACY_ENV) or "").strip()
    if legacy:
        return max(0, int(legacy))
    return DEFAULT_DAILY_LIMIT


@dataclass
class CollectBudget:
    """
    Budget Source of Truth.

    - Scheduler.dequeue が consume（ジョブ予約）
    - Manifest は as_dict() を記録
    - KeibaNetClient は同一インスタンスを参照し、独自 used を持たない
    """

    daily_limit: int
    used: int = 0

    @classmethod
    def from_env(cls, *, daily_limit: int | None = None) -> CollectBudget:
        return cls(daily_limit=resolve_daily_limit(daily_limit))

    @property
    def remaining(self) -> int:
        return max(0, self.daily_limit - self.used)

    def can_afford(self, cost: int) -> bool:
        return int(cost) <= self.remaining

    def consume(self, cost: int) -> None:
        cost = int(cost)
        if not self.can_afford(cost):
            raise BudgetExhaustedError(
                f"budget exhausted: need {cost}, remaining {self.remaining}"
            )
        self.used += cost

    def as_dict(self) -> dict[str, int]:
        return {
            "daily_limit": self.daily_limit,
            "used": self.used,
            "remaining": self.remaining,
        }
