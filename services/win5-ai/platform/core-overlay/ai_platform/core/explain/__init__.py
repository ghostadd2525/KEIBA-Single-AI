# -*- coding: utf-8 -*-
"""Core explain_payload builder — Version 2 Explainability Phase 1–2.

Contract: docs/releases/v2-explainability-design-review.md §5.1 / §10
Feature Flag: WIN5_EXPLAIN_V2_ENABLED (default OFF → omit payload)
Phase 2: Product journal → product_stages + decision_trace merge
"""
from __future__ import annotations

import os
from typing import Any

from .product import (
    build_product_stages,
    extract_journals_from_meta,
    merge_product_into_trace,
)

WIN5_EXPLAIN_V2_ENABLED = False

LABELS_JA: dict[str, str] = {
    "ce_rank1": "CE 評価 1 位",
    "ce_rank1_gap_lead": "CE 1 位・2 位差最大",
    "midupper_world": "中上位世界",
    "midupper_route": "中上位ルート型",
    "core_world": "中核世界",
    "ability": "能力差レース",
    "strong_spread": "展開分散が必要",
    "gap12": "1–2 位差",
    "entropy": "混戦度",
    "field_size": "頭数",
    "top1_prob": "1 位勝率",
    "top2_sum": "上位2頭合計",
    "candidate_pool": "候補 Pool",
    "entry": "Entry",
    "repick": "RePick",
    "pe_insert": "Pool 挿入",
    "rp_displaced": "RePick 入替",
}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def apply_win5_explain_v2_flags(enabled: bool | None = None) -> dict[str, Any]:
    """Toggle Core explain v2 flag. None → read env against current default."""
    global WIN5_EXPLAIN_V2_ENABLED
    if enabled is None:
        enabled = _env_bool("WIN5_EXPLAIN_V2_ENABLED", WIN5_EXPLAIN_V2_ENABLED)
    WIN5_EXPLAIN_V2_ENABLED = bool(enabled)
    return {"WIN5_EXPLAIN_V2_ENABLED": WIN5_EXPLAIN_V2_ENABLED}


def is_explain_v2_enabled() -> bool:
    return bool(WIN5_EXPLAIN_V2_ENABLED) or _env_bool("WIN5_EXPLAIN_V2_ENABLED", False)


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def _i(v: Any, default: int = 0) -> int:
    try:
        if v is None:
            return default
        return int(v)
    except Exception:
        return default


def _label(code: str) -> str:
    return LABELS_JA.get(str(code), str(code))


def _pct(prob: float) -> str:
    return f"{round(prob * 1000) / 10}%"


def _select_decision_key(
    *,
    model_rank: int,
    win_prob: float,
    gap12: float,
    world: str,
    sub_world: str,
) -> dict[str, Any]:
    """Phase 1 priority: ce_rank1_gap_lead > ce_rank1 > route."""
    if model_rank == 1 and gap12 > 0:
        return {
            "key": "ce_rank1_gap_lead",
            "kind": "candidate_evaluation",
            "label": _label("ce_rank1_gap_lead"),
            "text": "2 位との勝率差が最も大きい",
            "evidence": {
                "model_rank": model_rank,
                "win_prob": round(win_prob, 6),
                "gap12": round(gap12, 6),
            },
        }
    if model_rank == 1:
        return {
            "key": "ce_rank1",
            "kind": "candidate_evaluation",
            "label": _label("ce_rank1"),
            "evidence": {
                "model_rank": model_rank,
                "win_prob": round(win_prob, 6),
            },
        }
    route_code = sub_world or world or "route"
    return {
        "key": f"route_{route_code}" if route_code else "route_midupper",
        "kind": "route",
        "label": _label(route_code) if route_code in LABELS_JA else "ルート型",
        "evidence": {"world": world, "sub_world": sub_world},
    }


def _confidence_components(confidence: dict[str, Any]) -> list[dict[str, Any]]:
    """Derive contribution/weight from ConfidenceBuilder formula."""
    meta = dict(confidence.get("meta") or {})
    top1 = _f(meta.get("top1_prob"))
    gap12 = _f(meta.get("gap12"))
    entropy = _f(meta.get("entropy"))
    field_size = _i(meta.get("field_size"))
    top2_sum = _f(meta.get("top2_sum"))
    uncertainty = _f(meta.get("uncertainty"))

    gap_factor = min(1.0, max(0.0, gap12 / max(top1, 1e-6))) if top1 > 0 else 0.0
    spread_factor = 1.0 - min(max(uncertainty, 0.0), 1.0)

    base_part = top1 * 0.55
    gap_part = top1 * 0.25 * gap_factor
    spread_part = top1 * 0.20 * spread_factor
    total = base_part + gap_part + spread_part
    if total <= 0:
        total = 1.0

    def contrib(part: float) -> float:
        return round(part / total, 6)

    components: list[dict[str, Any]] = [
        {
            "key": "top1_prob",
            "value": round(top1, 6),
            "weight": 0.55,
            "contribution": contrib(base_part),
        },
        {
            "key": "gap12",
            "value": round(gap12, 6),
            "weight": 0.25,
            "contribution": contrib(gap_part),
        },
        {
            "key": "entropy",
            "value": round(entropy, 6),
            "weight": 0.20,
            "contribution": contrib(spread_part),
        },
        {
            "key": "top2_sum",
            "value": round(top2_sum, 6),
            "contribution": 0.0,
        },
        {
            "key": "field_size",
            "value": field_size,
            "contribution": 0.0,
        },
    ]
    return components


def _decision_trace_stages(
    *,
    honmei: dict[str, Any],
    world: str,
    sub_world: str,
    meta: dict[str, Any],
    win_prob: float,
) -> list[dict[str, Any]]:
    horse_number = honmei.get("HorseNumber")
    horse_name = str(honmei.get("CandidateID") or "")
    num_txt = f"{horse_number} 番" if horse_number is not None else ""
    repick_flag = meta.get("observer_repick_ready_flag")
    stages: list[dict[str, Any]] = [
        {
            "stage": "candidate_evaluation",
            "status": "applied",
            "delta": {
                "summary": f"CE 1 位: {num_txt}{horse_name}（勝率 {_pct(win_prob)}）".strip(),
                "outputs": {
                    "model_rank": 1,
                    "horse_number": horse_number,
                    "win_prob": round(win_prob, 6),
                },
            },
        },
        {
            "stage": "world_classification",
            "status": "applied",
            "delta": {
                "summary": f"{world} / {sub_world}",
                "outputs": {"world": world, "sub_world": sub_world},
            },
        },
        {
            "stage": "candidate_pool",
            "status": "not_applied",
            "delta": {"summary": "Product Pool 未配線（PI CE 経路）"},
        },
        {
            "stage": "entry",
            "status": "not_applied",
            "delta": {"summary": "Product Entry 未配線（PI CE 経路）"},
        },
        {
            "stage": "repick",
            "status": "not_applied",
            "delta": {
                "summary": (
                    f"RePick 未実行（observer_repick_ready={repick_flag})"
                    if repick_flag is not None
                    else "RePick 未実行（Product 未配線）"
                ),
                "inputs": {"observer_repick_ready_flag": repick_flag},
            },
        },
        {
            "stage": "purchase",
            "status": "not_applied",
            "delta": {"summary": "Purchase 未配線（PI CE 経路）"},
        },
        {
            "stage": "delete",
            "status": "locked",
            "delta": {"summary": "Delete Boundary — 変更禁止"},
        },
        {
            "stage": "mark_assignment",
            "status": "applied",
            "delta": {
                "summary": "Rank1 → ◎（honmei）",
                "before": {"mark": None},
                "after": {"mark": "honmei"},
            },
        },
    ]
    return stages


def build_explain_payload(
    *,
    candidates: list[dict[str, Any]],
    world: dict[str, Any] | str,
    confidence: dict[str, Any],
    meta: dict[str, Any] | None = None,
    core_version: str = "ai-core-migrated/1.0-phase1",
    product_journals: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Build core-explain-payload/1.0. Returns None when Flag OFF.

    Phase 2: pass product_journals={pool_entry, repick, timestamp?}
    or embed journals under meta._win5_*_journal keys.
    """
    if not is_explain_v2_enabled():
        return None

    conf_meta = dict(confidence.get("meta") or {})
    meta = {**conf_meta, **dict(meta or {})}
    world_code = world.get("world", "") if isinstance(world, dict) else str(world or "")
    sub_world = (
        world.get("sub_world", "") if isinstance(world, dict) else str(meta.get("sub_world") or "")
    )
    if not sub_world and isinstance(world, dict):
        sub_world = str(world.get("sub_world") or "")

    honmei = None
    for c in candidates or []:
        if _i(c.get("Rank"), 999) == 1:
            honmei = c
            break
    if honmei is None and candidates:
        honmei = candidates[0]
    if honmei is None:
        return None

    win_prob = _f(honmei.get("Confidence"))
    gap12 = _f(meta.get("gap12"))
    decision_key = _select_decision_key(
        model_rank=1,
        win_prob=win_prob,
        gap12=gap12,
        world=world_code,
        sub_world=sub_world,
    )

    required_role = {
        "race_required_pick": meta.get("race_required_pick"),
        "spread_need_label": meta.get("spread_need_label"),
        "race_type_label": meta.get("race_type_label"),
        "rank7_9_pick_required_flag": meta.get("rank7_9_pick_required_flag"),
    }

    base_stages = _decision_trace_stages(
        honmei=honmei,
        world=world_code,
        sub_world=sub_world,
        meta=meta,
        win_prob=win_prob,
    )

    journals = {**extract_journals_from_meta(meta), **dict(product_journals or {})}
    product_stages = build_product_stages(
        pool_entry=journals.get("pool_entry"),
        repick=journals.get("repick"),
        timestamp=journals.get("timestamp"),
    )
    stages = merge_product_into_trace(base_stages, product_stages or None)
    pipeline = (
        "ai-core-migrated/1.0-phase2"
        if product_stages
        else core_version
    )

    return {
        "schema_version": "core-explain-payload/1.0",
        "honmei_candidate_id": str(honmei.get("CandidateID") or ""),
        "decision_key": decision_key,
        "ranking_evidence": {
            "rank": 1,
            "win_prob": round(win_prob, 6),
            "gap_to_next": round(gap12, 6),
            "horse_number": honmei.get("HorseNumber"),
        },
        "world": {"world": world_code, "sub_world": sub_world},
        "confidence_meta": {
            "gap12": meta.get("gap12"),
            "entropy": meta.get("entropy"),
            "top1_prob": meta.get("top1_prob"),
            "top2_sum": meta.get("top2_sum"),
            "field_size": meta.get("field_size"),
            "uncertainty": meta.get("uncertainty"),
        },
        "confidence_components": _confidence_components(confidence),
        "confidence_band": confidence.get("band"),
        "overall_confidence": confidence.get("overall"),
        "decision_trace_stages": stages,
        "required_role": required_role,
        "product_stages": product_stages or None,
        "pipeline_version": pipeline,
    }


__all__ = [
    "WIN5_EXPLAIN_V2_ENABLED",
    "apply_win5_explain_v2_flags",
    "is_explain_v2_enabled",
    "build_explain_payload",
    "build_product_stages",
    "merge_product_into_trace",
    "LABELS_JA",
]
