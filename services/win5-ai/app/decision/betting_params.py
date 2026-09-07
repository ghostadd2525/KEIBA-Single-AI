# -*- coding: utf-8 -*-
"""Betting policy parameters (V93). Decision Layer only. ADR-008 unchanged."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from app.decision.policy_params import RECOMMENDED_RANK7, Rank7PolicyParams

AllocName = Literal["equal", "decay", "top_heavy", "mass_prop"]
SkipName = Literal["none", "ev_neg", "mass_lt_08", "mass_lt_10", "field_gt_16"]


@dataclass(frozen=True)
class BettingPolicyParams:
    """Betting-only knobs on top of a fixed V92 Decision structure."""

    # Structural baseline from V92 (coverage)
    decision: Rank7PolicyParams = RECOMMENDED_RANK7
    # How many of decision.ticket_top_n horses to actually buy
    buy_legs: int = 5
    alloc: AllocName = "decay"
    skip: SkipName = "none"
    budget_scale: float = 1.0
    # ticket type: win only in Shadow (no place odds/results)
    ticket_type: str = "win"

    def id(self) -> str:
        d = self.decision
        return (
            f"bet_L{self.buy_legs}_{self.alloc}_{self.skip}_b{self.budget_scale:g}"
            f"__dec_T{d.ticket_top_n}P{d.pool_size}"
        )

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["decision"] = self.decision.to_dict()
        out["id"] = self.id()
        return out


# V92 baseline betting (decay Top5 / Pool7 / no skip) — V92 default ticket behavior
V92_BASELINE_BETTING = BettingPolicyParams(
    decision=RECOMMENDED_RANK7,
    buy_legs=5,
    alloc="decay",
    skip="none",
    budget_scale=1.0,
)

# V93 Shadow winner: Coverage≥V92 floor ∩ rank7 Ticket ROI max
RECOMMENDED_BETTING = BettingPolicyParams(
    decision=RECOMMENDED_RANK7,
    buy_legs=1,
    alloc="equal",
    skip="field_gt_16",
    budget_scale=0.5,
)


def allocation_weights(n: int, alloc: AllocName, masses: list[float] | None = None) -> list[float]:
    if n <= 0:
        return []
    if n == 1:
        return [1.0]
    if alloc == "equal":
        return [1.0 / n] * n
    if alloc == "top_heavy":
        if n == 2:
            return [0.75, 0.25]
        if n == 3:
            return [0.70, 0.20, 0.10]
        if n == 4:
            return [0.60, 0.20, 0.12, 0.08]
        # n==5
        return [0.55, 0.20, 0.12, 0.08, 0.05]
    if alloc == "mass_prop":
        m = masses or [1.0] * n
        m = [max(1e-9, float(x)) for x in m[:n]]
        s = sum(m)
        return [x / s for x in m]
    # decay (V92 default family)
    from app.decision.policy_params import stake_weights

    return stake_weights(n)


def betting_search_grid() -> list[BettingPolicyParams]:
    """Coverage-preserving structure: V92 Top5+Pool7; vary betting knobs."""
    out: list[BettingPolicyParams] = []
    for legs in (1, 2, 3, 4, 5):
        for alloc in ("equal", "decay", "top_heavy", "mass_prop"):
            for skip in ("none", "ev_neg", "mass_lt_08", "mass_lt_10", "field_gt_16"):
                for bud in (0.5, 1.0):
                    out.append(
                        BettingPolicyParams(
                            decision=RECOMMENDED_RANK7,
                            buy_legs=legs,
                            alloc=alloc,  # type: ignore[arg-type]
                            skip=skip,  # type: ignore[arg-type]
                            budget_scale=bud,
                        )
                    )
    return out
