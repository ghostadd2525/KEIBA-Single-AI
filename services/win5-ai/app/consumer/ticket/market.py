# -*- coding: utf-8 -*-
"""Market Resolver — odds/budget lookup for Ticket Policy (V109 C3).

Does not change Prediction / World / Semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol


@dataclass(frozen=True)
class MarketSnapshot:
    budget: float | None = None
    odds_by_horse: Mapping[str, float] | None = None


class MarketResolver(Protocol):
    def resolve(self, race_id: str) -> MarketSnapshot:
        """Return market facts for stake/odds annotation."""
        ...


class NullMarketResolver:
    """No market data — Ticket Resolver uses template unit stakes only."""

    def resolve(self, race_id: str) -> MarketSnapshot:
        return MarketSnapshot(budget=None, odds_by_horse=None)


class DictMarketResolver:
    """In-memory market for Shadow / tests."""

    def __init__(
        self,
        *,
        budget: float | None = None,
        odds_by_horse: Mapping[str, float] | None = None,
        by_race: Mapping[str, MarketSnapshot] | None = None,
    ) -> None:
        self._budget = budget
        self._odds = dict(odds_by_horse or {})
        self._by_race = dict(by_race or {})

    def resolve(self, race_id: str) -> MarketSnapshot:
        if race_id in self._by_race:
            return self._by_race[race_id]
        return MarketSnapshot(budget=self._budget, odds_by_horse=dict(self._odds))
