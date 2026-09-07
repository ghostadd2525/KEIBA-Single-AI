# -*- coding: utf-8 -*-
"""Decision Layer policy parameters (V92). Architecture / ADR-008 unchanged."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Rank7PolicyParams:
    """rank7 Decision parameters only."""

    ticket_top_n: int = 3  # Top2..Top5
    pool_size: int = 5  # Pool4..Pool7
    # Risk: total stake multiplier (1.0 = UNIT)
    stake_scale: float = 1.0
    # Explanation template suffix tag (policy id)
    explain_variant: str = "melee_default"

    def id(self) -> str:
        return f"rank7_Top{self.ticket_top_n}_Pool{self.pool_size}_s{self.stake_scale:g}"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["id"] = self.id()
        return d


# M1 Shadow default (V91) — code default for compatibility
M1_RANK7 = Rank7PolicyParams(ticket_top_n=3, pool_size=5, stake_scale=1.0)

# V92 Pareto balanced candidate (Shadow推奨。コード既定は M1 のまま)
RECOMMENDED_RANK7 = Rank7PolicyParams(ticket_top_n=5, pool_size=7, stake_scale=1.0)


def stake_weights(top_n: int) -> list[float]:
    """Weights summing to 1.0 for TopN win tickets."""
    if top_n <= 1:
        return [1.0]
    if top_n == 2:
        return [0.60, 0.40]
    if top_n == 3:
        return [0.50, 0.30, 0.20]
    if top_n == 4:
        return [0.40, 0.30, 0.20, 0.10]
    if top_n == 5:
        return [0.35, 0.25, 0.20, 0.12, 0.08]
    # fallback: decreasing
    raw = [1.0 / (i + 1) for i in range(top_n)]
    s = sum(raw)
    return [x / s for x in raw]


def search_grid() -> list[Rank7PolicyParams]:
    """User V92 grid: Top2..5 × Pool4..7."""
    out: list[Rank7PolicyParams] = []
    for top_n in (2, 3, 4, 5):
        for pool in (4, 5, 6, 7):
            out.append(Rank7PolicyParams(ticket_top_n=top_n, pool_size=pool, stake_scale=1.0))
    return out
