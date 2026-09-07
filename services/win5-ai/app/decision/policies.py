# -*- coding: utf-8 -*-
"""World → Decision policies (V88/V89). Rank/Score never mutated."""
from __future__ import annotations

from typing import Any

from app.decision.dto import (
    ConfidenceDisplayDTO,
    DecisionDTO,
    ExplanationDTO,
    PredictionView,
    RiskDisplayDTO,
    TicketLeg,
)

UNIT = 100.0
BLOCKED = frozenset({"core_world", "midupper_world", "mixed_world", "bug_world"})


def win_prob_mass(horses: tuple[dict[str, Any], ...] | list[dict[str, Any]], horse_id: str) -> float:
    s = sum(max(0.0, float(h.get("win_prob") or 0.0)) for h in horses)
    if s <= 0:
        return 1.0 / max(1, len(horses))
    for h in horses:
        if str(h.get("horse_id") or "") == horse_id:
            return max(0.0, float(h.get("win_prob") or 0.0)) / s
    return 1.0 / max(1, len(horses))


def legacy_decision(view: PredictionView, flag_snapshot: dict[str, bool]) -> DecisionDTO:
    """Decision OFF / Flag OFF — Legacy compatible baseline."""
    top1 = view.predicted_top1
    mass = win_prob_mass(view.horses, top1)
    return DecisionDTO(
        mode="OFF",
        action="BUY",
        world_id=view.world_id,
        tickets=(TicketLeg(type="win", horse_id=top1, stake=UNIT),),
        pool=(top1,),
        explanation=ExplanationDTO(
            template="generic_baseline",
            text="標準予測に基づく本命購入。",
            world_tag=None,
        ),
        confidence_display=ConfidenceDisplayDTO(
            value=mass,
            label="standard",
            suppressed=False,
            world_tag=None,
        ),
        risk_display=RiskDisplayDTO(budget=UNIT, level="standard", skip=False),
        prediction_fingerprint=view.prediction_fingerprint,
        flag_snapshot=flag_snapshot,
    )


from app.decision.policy_params import M1_RANK7, Rank7PolicyParams, stake_weights
from app.decision.betting_params import BettingPolicyParams, allocation_weights


def _top1_mass(view: PredictionView) -> float:
    return win_prob_mass(view.horses, view.predicted_top1)


def _should_skip_betting(view: PredictionView, bet: BettingPolicyParams, planned_ev: float) -> bool:
    mass = _top1_mass(view)
    if bet.skip == "none":
        return False
    if bet.skip == "ev_neg":
        return planned_ev < 0.0
    if bet.skip == "mass_lt_08":
        return mass < 0.08
    if bet.skip == "mass_lt_10":
        return mass < 0.10
    if bet.skip == "field_gt_16":
        return int(view.field_size) > 16
    return False


def _ticket_ev(view: PredictionView, horse_id: str, stake: float) -> float:
    """Approx EV using win_prob mass × odds − stake."""
    p = win_prob_mass(view.horses, horse_id)
    odds = 0.0
    for h in view.horses:
        if str(h.get("horse_id") or "") == horse_id:
            odds = float(h.get("odds") or 0.0)
            break
    if odds <= 0:
        return -stake
    return stake * (p * odds - 1.0)


def world_decision(
    view: PredictionView,
    flag_snapshot: dict[str, bool],
    *,
    rank7_params: Rank7PolicyParams | None = None,
    betting_params: BettingPolicyParams | None = None,
) -> DecisionDTO:
    """Full Decision ON policy (all sub-features conceptually ON for Shadow)."""
    w = view.world_id
    top1 = view.predicted_top1
    by_rank = view.horses_by_rank
    mass = win_prob_mass(view.horses, top1)
    base = legacy_decision(view, flag_snapshot)
    r7 = rank7_params or (betting_params.decision if betting_params else None) or M1_RANK7

    if w in BLOCKED:
        return DecisionDTO(
            mode="ON",
            action="SKIP",
            world_id=w,
            tickets=(),
            pool=(top1,),
            explanation=ExplanationDTO(
                template="blocked_provisional",
                text=f"World={w} は自動 Decision 対象外（標本不足/例外）。見送り。",
                world_tag=w,
            ),
            confidence_display=ConfidenceDisplayDTO(
                value=mass,
                label="no_high_confidence",
                suppressed=True,
                world_tag=w,
            ),
            risk_display=RiskDisplayDTO(budget=0.0, level="skip", skip=True),
            prediction_fingerprint=view.prediction_fingerprint,
            flag_snapshot=flag_snapshot,
        )

    if w == "rank7_world":
        n_avail = len(by_rank)
        struct_top = max(1, min(int(r7.ticket_top_n), n_avail))
        pool_n = max(struct_top, min(int(r7.pool_size), n_avail))
        pool = tuple(str(h.get("horse_id") or "") for h in by_rank[:pool_n])

        bet = betting_params
        if bet is None:
            # V92 structural default ticket behavior
            top_n = struct_top
            ids = [str(h.get("horse_id") or "") for h in by_rank[:top_n]]
            weights = stake_weights(top_n)
            budget = UNIT * float(r7.stake_scale)
            tickets = tuple(
                TicketLeg(type="win", horse_id=hid, stake=budget * wt) for hid, wt in zip(ids, weights)
            )
            return DecisionDTO(
                mode="ON",
                action="BUY",
                world_id=w,
                tickets=tickets,
                pool=pool,
                explanation=ExplanationDTO(
                    template="rank7_melee",
                    text=f"展開・混戦寄り。Top{top_n}分散 / Pool{pool_n}。（policy={r7.id()}）",
                    world_tag=w,
                ),
                confidence_display=ConfidenceDisplayDTO(
                    value=mass,
                    label="melee_caution",
                    suppressed=True,
                    world_tag=w,
                ),
                risk_display=RiskDisplayDTO(budget=budget, level="medium", skip=False),
                prediction_fingerprint=view.prediction_fingerprint,
                flag_snapshot=flag_snapshot,
            )

        # V93 betting overlay (structure from bet.decision / r7)
        buy_n = max(1, min(int(bet.buy_legs), struct_top, n_avail))
        cand = list(by_rank[:struct_top])[:buy_n]
        ids = [str(h.get("horse_id") or "") for h in cand]
        masses = [win_prob_mass(view.horses, hid) for hid in ids]
        weights = allocation_weights(buy_n, bet.alloc, masses)
        budget = UNIT * float(bet.budget_scale) * float(r7.stake_scale)
        raw_tickets = [
            TicketLeg(type=bet.ticket_type, horse_id=hid, stake=budget * wt)
            for hid, wt in zip(ids, weights)
        ]
        planned_ev = sum(_ticket_ev(view, t.horse_id, t.stake) for t in raw_tickets)
        if _should_skip_betting(view, bet, planned_ev):
            return DecisionDTO(
                mode="ON",
                action="SKIP",
                world_id=w,
                tickets=(),
                pool=pool,
                explanation=ExplanationDTO(
                    template="rank7_melee_skip",
                    text=f"Betting Skip ({bet.skip}). Pool{pool_n} は維持。（{bet.id()}）",
                    world_tag=w,
                ),
                confidence_display=ConfidenceDisplayDTO(
                    value=mass,
                    label="melee_caution",
                    suppressed=True,
                    world_tag=w,
                ),
                risk_display=RiskDisplayDTO(budget=0.0, level="skip_betting", skip=True),
                prediction_fingerprint=view.prediction_fingerprint,
                flag_snapshot=flag_snapshot,
            )

        return DecisionDTO(
            mode="ON",
            action="BUY",
            world_id=w,
            tickets=tuple(raw_tickets),
            pool=pool,
            explanation=ExplanationDTO(
                template="rank7_melee_bet",
                text=(
                    f"Betting L{buy_n}/{bet.alloc}/b{bet.budget_scale:g}; "
                    f"Pool{pool_n}。（{bet.id()}）"
                ),
                world_tag=w,
            ),
            confidence_display=ConfidenceDisplayDTO(
                value=mass,
                label="melee_caution",
                suppressed=True,
                world_tag=w,
            ),
            risk_display=RiskDisplayDTO(budget=budget, level="medium", skip=False),
            prediction_fingerprint=view.prediction_fingerprint,
            flag_snapshot=flag_snapshot,
        )

    if w == "unsatisfied":
        return DecisionDTO(
            mode="ON",
            action="BUY",
            world_id=w,
            tickets=base.tickets,
            pool=base.pool,
            explanation=ExplanationDTO(
                template="unsatisfied_residual",
                text="特定 World 未充足（残余）。独自勝ち筋を主張しない。",
                world_tag=w,
            ),
            confidence_display=ConfidenceDisplayDTO(
                value=mass,
                label="generic",
                suppressed=False,
                world_tag=w,
            ),
            risk_display=RiskDisplayDTO(budget=UNIT, level="standard", skip=False),
            prediction_fingerprint=view.prediction_fingerprint,
            flag_snapshot=flag_snapshot,
        )

    if w == "midhole_world":
        hist_sorted = sorted(
            list(view.horses),
            key=lambda h: float(h.get("history_score") or 0.0),
            reverse=True,
        )
        pool_ids: list[str] = []
        for h in by_rank[:3]:
            pool_ids.append(str(h.get("horse_id") or ""))
        for h in hist_sorted[:2]:
            hid = str(h.get("horse_id") or "")
            if hid and hid not in pool_ids:
                pool_ids.append(hid)
        return DecisionDTO(
            mode="ON",
            action="BUY",
            world_id=w,
            tickets=(TicketLeg(type="win", horse_id=top1, stake=UNIT * 0.7),),
            pool=tuple(pool_ids),
            explanation=ExplanationDTO(
                template="midhole",
                text="中位帯開放。上位能力一本を相対的に弱く読む。",
                world_tag=w,
            ),
            confidence_display=ConfidenceDisplayDTO(
                value=mass,
                label="winprob_suppressed",
                suppressed=True,
                world_tag=w,
            ),
            risk_display=RiskDisplayDTO(budget=UNIT * 0.7, level="modest", skip=False),
            prediction_fingerprint=view.prediction_fingerprint,
            flag_snapshot=flag_snapshot,
        )

    # Unknown world → legacy ticket + tagged explanation
    return DecisionDTO(
        mode="ON",
        action=base.action,
        world_id=w,
        tickets=base.tickets,
        pool=base.pool,
        explanation=ExplanationDTO(
            template="generic_baseline",
            text=base.explanation.text if base.explanation else "",
            world_tag=w,
        ),
        confidence_display=base.confidence_display,
        risk_display=base.risk_display,
        prediction_fingerprint=view.prediction_fingerprint,
        flag_snapshot=flag_snapshot,
    )


def merge_by_subflags(
    legacy: DecisionDTO,
    full: DecisionDTO,
    *,
    ticket: bool,
    pool: bool,
    explain: bool,
    risk: bool,
    conf: bool,
) -> DecisionDTO:
    """Compose Decision ON output from sub-flags; unused axes keep Legacy."""
    if full.action == "SKIP" and risk:
        # Risk skip requires risk flag; if risk OFF, fall back to legacy buy
        action = "SKIP"
        tickets = () if ticket else legacy.tickets
        risk_dto = full.risk_display
    else:
        action = legacy.action
        tickets = full.tickets if ticket else legacy.tickets
        risk_dto = full.risk_display if risk else legacy.risk_display
        if full.action == "SKIP" and not risk:
            action = legacy.action
            tickets = legacy.tickets
            risk_dto = legacy.risk_display

    return DecisionDTO(
        mode="ON" if (ticket or pool or explain or risk or conf) else "OFF",
        action=action if ticket or risk else legacy.action,
        world_id=full.world_id,
        tickets=tickets if ticket else legacy.tickets,
        pool=full.pool if pool else legacy.pool,
        explanation=full.explanation if explain else legacy.explanation,
        confidence_display=full.confidence_display if conf else legacy.confidence_display,
        risk_display=risk_dto if risk else legacy.risk_display,
        prediction_fingerprint=legacy.prediction_fingerprint,
        flag_snapshot=full.flag_snapshot,
    )
