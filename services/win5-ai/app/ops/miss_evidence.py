# -*- coding: utf-8 -*-
"""Miss Evidence — Production 書き出し専用（改善分析は行わない）。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

SCHEMA = "expect-miss-evidence/1.0"


def classify_miss(*, hit_at_1: bool, hit_at_3: bool, hit_at_5: bool) -> str | None:
    if hit_at_1:
        return None
    if hit_at_3:
        return "miss_top1"
    if hit_at_5:
        return "miss_top3"
    return "miss_top5"


def build_miss_evidence(
    *,
    race_id: str,
    bundle: dict[str, Any],
    meta: dict[str, Any],
    winner_horse_number: int | None,
    winner_name: str | None,
    hit_at_1: bool,
    hit_at_3: bool,
    hit_at_5: bool,
    timestamp: str | None = None,
) -> dict[str, Any] | None:
    category = classify_miss(hit_at_1=hit_at_1, hit_at_3=hit_at_3, hit_at_5=hit_at_5)
    if not category:
        return None

    runners = ((bundle.get("evaluation") or {}).get("runners")) or []
    ordered = sorted(runners, key=lambda r: int(r.get("model_rank") or 999))
    candidate_pool = ordered[:8]

    conf = (bundle.get("ai_confidence") or {}).get("score")
    if isinstance(conf, (int, float)) and conf <= 1:
        conf_pct = round(float(conf) * 100, 2)
    elif isinstance(conf, (int, float)):
        conf_pct = round(float(conf), 2)
    else:
        conf_pct = None

    explain = bundle.get("explain") or {}
    bets = bundle.get("betting_recommendations") or {}
    model_version = (
        meta.get("model_version")
        or bundle.get("model_version")
        or ((bundle.get("explain") or {}).get("meta") or {}).get("model_version")
    )
    ts = timestamp or datetime.now(timezone.utc).isoformat()

    return {
        "schema_version": SCHEMA,
        "race_id": race_id,
        "timestamp": ts,
        "winner": {
            "horse_number": winner_horse_number,
            "horse_name": winner_name,
        },
        "prediction_bundle": {
            "race_id": bundle.get("race_id") or race_id,
            "race_info": bundle.get("race_info"),
            "evaluation": {"runners": candidate_pool},
            "ai_confidence": bundle.get("ai_confidence"),
        },
        "candidate_pool": candidate_pool,
        "repick": bets.get("items") or bets.get("by_bet_type"),
        "delete": None,
        "confidence": conf_pct,
        "engine_source": meta.get("engine_source"),
        "feature_source": meta.get("feature_source")
        or ((explain.get("meta") or {}).get("feature_source")),
        "fallback_reason": meta.get("fallback_reason"),
        "miss_category": category,
        "explain": {
            "narrative": explain.get("narrative"),
            "reasons": (explain.get("reasons") or [])[:5],
        },
        "model_version": model_version,
        "version": {
            "model_version": model_version,
            "core_version": bundle.get("core_version"),
            "schema_version": bundle.get("schema_version"),
        },
    }


def winner_name_from_result(result_json: Any) -> str | None:
    if not result_json:
        return None
    if isinstance(result_json, str):
        try:
            result_json = json.loads(result_json)
        except json.JSONDecodeError:
            return None
    if isinstance(result_json, dict):
        return result_json.get("winner_name")
    return None


def hit_flags_from_runners(
    runners: list[dict[str, Any]],
    winner_horse_number: int | None,
) -> tuple[bool, bool, bool]:
    """model_rank ベースの Top1/3/5 Hit 判定。"""
    if winner_horse_number is None:
        return False, False, False
    ordered = sorted(runners, key=lambda r: int(r.get("model_rank") or 999))
    nums = []
    for r in ordered:
        n = r.get("horse_number")
        try:
            nums.append(int(n))
        except (TypeError, ValueError):
            continue
    win = int(winner_horse_number)
    hit_at_1 = bool(nums and nums[0] == win)
    hit_at_3 = win in nums[:3]
    hit_at_5 = win in nums[:5]
    return hit_at_1, hit_at_3, hit_at_5
