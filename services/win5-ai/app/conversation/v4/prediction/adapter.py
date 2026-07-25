# -*- coding: utf-8 -*-
"""
Conversation Prediction Adapter — Official Prediction 投影（非破壊）。

bundle / meta を ReviewContext.prediction 用に投影する。
Ranking / Confidence / Purchase を変更しない。mutated は常に false。
"""
from __future__ import annotations

from typing import Any

from .connector import OfficialPredictionFetch

FAIL_OPEN_MESSAGE = (
    "いま公式 Prediction を取得できないよ。"
    "Conversation はそのまま使えるから、レース画面で確認するか、少ししてからもう一度試してみてね。"
)


def project_official_prediction(fetch: OfficialPredictionFetch) -> dict[str, Any] | None:
    """
    Official Prediction の読取専用投影。
    入力 bundle を in-place 変更しない。
    """
    if not fetch.ok or not isinstance(fetch.bundle, dict):
        return None

    bundle = fetch.bundle
    meta = fetch.api_meta if isinstance(fetch.api_meta, dict) else {}

    summary_src = bundle.get("summary") if isinstance(bundle.get("summary"), dict) else {}
    runners_src = bundle.get("runners") or bundle.get("top_runners") or []
    if not isinstance(runners_src, list):
        runners_src = []

    top_runners: list[dict[str, Any]] = []
    for r in runners_src[:12]:
        if not isinstance(r, dict):
            continue
        top_runners.append(
            {
                "umaban": r.get("umaban") or r.get("horse_number") or r.get("number"),
                "name": r.get("name") or r.get("horse_name"),
                "mark": r.get("mark") or r.get("print"),
                "rank": r.get("rank") or r.get("order"),
                "score": r.get("score"),
            }
        )

    explain = bundle.get("explain") if isinstance(bundle.get("explain"), dict) else {}
    reason = explain.get("reason") if isinstance(explain.get("reason"), dict) else {}

    engine = meta.get("engine_source") or bundle.get("engine_source")
    item = meta.get("item")
    if not engine and isinstance(item, dict):
        engine = item.get("engine_source")
    provenance = meta.get("provenance")
    if not engine and isinstance(provenance, dict):
        engine = provenance.get("engine_source")

    # 新しい dict のみ返す（bundle 非破壊）
    return {
        "race_id": fetch.race_id or bundle.get("race_id"),
        "prediction_available": True,
        "engine_source": engine or "official",
        "official": True,
        "summary": {
            "honmei": summary_src.get("honmei") or bundle.get("honmei"),
            "confidence": summary_src.get("confidence") or bundle.get("confidence"),
            "axis": summary_src.get("axis"),
            "marks": summary_src.get("marks"),
        },
        "top_runners": top_runners,
        "explain_summary": reason.get("summary")
        or explain.get("summary")
        or bundle.get("explain_summary"),
        "schema_version": bundle.get("schema_version"),
    }


def build_prediction_meta(
    fetch: OfficialPredictionFetch,
    *,
    official: dict[str, Any] | None,
) -> dict[str, Any]:
    """prediction_meta — mutated は常に False。"""
    if fetch.ok and official:
        return {
            "used": True,
            "mutated": False,
            "connected": True,
            "source": "prediction_api",
            "official": True,
            "prediction_available": True,
            "engine_source": official.get("engine_source"),
            "race_id": fetch.race_id,
            "fail_open": False,
            "error": None,
        }
    return {
        "used": False,
        "mutated": False,
        "connected": False,
        "source": "prediction_api",
        "official": False,
        "prediction_available": False,
        "engine_source": None,
        "race_id": fetch.race_id,
        "fail_open": True,
        "error": fetch.error or "prediction_unavailable",
    }


class ConversationPredictionAdapter:
    """Connector 結果 → Official Prediction + meta。"""

    def adapt(self, fetch: OfficialPredictionFetch) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        official = project_official_prediction(fetch)
        meta = build_prediction_meta(fetch, official=official)
        # 不変条件
        meta["mutated"] = False
        return official, meta
