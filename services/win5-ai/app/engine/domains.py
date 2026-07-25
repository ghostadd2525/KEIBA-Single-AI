"""PredictionBundle contract + projections for sibling services."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

BUNDLE_SCHEMA = "single-prediction-bundle/2.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def score_percent(ai_confidence: dict[str, Any] | None) -> int | None:
    c = ai_confidence or {}
    if isinstance(c.get("score_percent"), (int, float)):
        return int(round(c["score_percent"]))
    score = c.get("score")
    if isinstance(score, (int, float)):
        return int(round(score * 100)) if score <= 1 else int(round(score))
    return None


def normalize_prediction_bundle(raw: dict[str, Any], race_id: str | None = None) -> dict[str, Any]:
    rid = race_id or raw.get("race_id") or (raw.get("race_info") or {}).get("race_id")
    info = dict(raw.get("race_info") or {})
    if rid:
        info["race_id"] = rid
    return {
        **raw,
        "schema_version": BUNDLE_SCHEMA,
        "race_id": rid,
        "race_info": info,
        "status": raw.get("status") or "ok",
        "warnings": raw.get("warnings") if isinstance(raw.get("warnings"), list) else [],
        "evaluation": raw.get("evaluation") or {"status": "unknown", "runners": []},
        "ai_confidence": raw.get("ai_confidence")
        or {
            "schema_version": "single-ai-confidence/1.0",
            "status": "unknown",
            "score": None,
            "band": "unknown",
        },
        "explain": raw.get("explain") or {"narrative": "", "reasons": [], "meta": {}},
        "betting_recommendations": raw.get("betting_recommendations")
        or {
            "schema_version": "single-betting-recommendations/1.0",
            "race_id": rid,
            "status": "unknown",
            "items": [],
        },
    }


def catalog_to_prediction_bundle(race: dict[str, Any], base: dict[str, Any] | None = None) -> dict[str, Any]:
    race_id = str(race.get("race_id") or race.get("public_race_id") or "").strip()
    if not race_id:
        raise KeyError("race_id")
    hint = race.get("ai_confidence")
    base_n = normalize_prediction_bundle(base, race_id) if base else None
    band = "unknown"
    if isinstance(hint, (int, float)):
        band = "high" if hint >= 85 else "medium" if hint >= 70 else "low"
    date = str(race.get("date") or "")
    venue = str(race.get("venue") or "")
    bundle = {
        "schema_version": BUNDLE_SCHEMA,
        "race_id": race_id,
        "generated_at": (base_n or {}).get("generated_at") or _now(),
        "model_version": (base_n or {}).get("model_version") or "list-projection",
        "core_version": (base_n or {}).get("core_version") or "list-projection",
        "product_version": (base_n or {}).get("product_version") or "expect-ui-0.1.0",
        "status": "ok",
        "warnings": [],
        "race_info": {
            "race_id": race_id,
            "date": race.get("date"),
            "venue": race.get("venue"),
            "meeting_id": f"{date.replace('-', '')}_{venue.lower()}",
            "race_no": race.get("race_no"),
            "post_time": race.get("post_time"),
            "distance": race.get("distance"),
            "surface": race.get("surface"),
            "course": ((base_n or {}).get("race_info") or {}).get("course"),
            "class_label": race.get("class_label"),
            "grade": race.get("badge"),
            "field_size": race.get("field_size"),
            "race_status": race.get("status") or "scheduled",
            "date_label": race.get("date_label"),
            "date_full": race.get("date_full"),
            "bg": race.get("bg"),
        },
        "evaluation": (base_n or {}).get("evaluation")
        or {"status": "list", "world": None, "sub_world": None, "runners": []},
        "ai_confidence": {
            "schema_version": "single-ai-confidence/1.0",
            "status": "ok",
            "score": (float(hint) / 100.0) if isinstance(hint, (int, float)) else None,
            "score_unit": "normalized",
            "band": band,
            "factors": [],
            "component_scores": {},
            "notes": "list projection",
            "computed_at": _now(),
        },
        "explain": (base_n or {}).get("explain") or {"meta": {}, "reasons": [], "narrative": ""},
        "betting_recommendations": (base_n or {}).get("betting_recommendations")
        or {
            "schema_version": "single-betting-recommendations/1.0",
            "race_id": race_id,
            "status": "list",
            "items": [],
            "by_bet_type": {},
        },
    }
    return normalize_prediction_bundle(bundle, race_id)


def project_confidence(bundle: dict[str, Any]) -> dict[str, Any]:
    b = normalize_prediction_bundle(bundle)
    c = b.get("ai_confidence") or {}
    return {
        "schema_version": "expect-confidence/1.0",
        "race_id": b.get("race_id"),
        "status": c.get("status") or "ok",
        "score": c.get("score"),
        "score_percent": score_percent(c),
        "score_unit": c.get("score_unit") or "normalized",
        "band": c.get("band") or "unknown",
        "factors": c.get("factors") or [],
        "component_scores": c.get("component_scores") or {},
        "notes": c.get("notes") or "",
        "computed_at": c.get("computed_at"),
    }


def project_tickets(bundle: dict[str, Any]) -> dict[str, Any]:
    b = normalize_prediction_bundle(bundle)
    br = b.get("betting_recommendations") or {}
    return {
        "schema_version": "expect-tickets/1.0",
        "race_id": b.get("race_id"),
        "status": br.get("status") or "ok",
        "strategy_id": br.get("strategy_id"),
        "generated_at": br.get("generated_at"),
        "items": br.get("items") or [],
        "by_bet_type": br.get("by_bet_type") or {},
    }


def to_analysis(row: dict[str, Any], race_id: str) -> dict[str, Any]:
    return {
        "schema_version": "expect-analysis/1.0",
        "race_id": race_id or row.get("race_id"),
        "charts": row.get("charts") or [],
        "overall": row.get("overall"),
        "narrative": row.get("narrative") or "",
    }


def kaoba_reply(body: dict[str, Any]) -> dict[str, Any]:
    """
    Kaoba rule fallback（Conversation 不通時）。
    同じ定型を連発せず、質問意図ごとに返す。race_id の「（対象: …）」は付けない。
    """
    message = str(body.get("message") or "")
    race_id = str(body.get("race_id") or "")
    ctx = body.get("context") or {}
    mode = str(ctx.get("mode") or body.get("mode") or "").lower()
    ctx_type = str(ctx.get("type") or "")
    has_strategy = ctx.get("ui") == "strategy" or ctx_type in (
        "strategy_review",
        "consult",
    )
    is_explain = mode in ("explain", "explain_pick") or ctx_type in (
        "honmei_reason",
        "explain_pick",
    )

    if is_explain or any(k in message for k in ("理由", "なぜ", "根拠", "どうして", "本命")):
        reply = (
            "本命（◎）にした理由は、総合評価の分離とコース適性・展開適性のバランスだよ。"
            "上位候補との差は「安定した再現性」側で見ているよ。"
            "印や順位は変えず、レース画面の説明タブもあわせて確認してね。"
        )
        if any(k in message for k in ("対抗", "差", "比較")):
            reply = (
                "対抗との差は、本命の方が総合スコアと位置取り想定で一貫している点だよ。"
                "対抗は展開が噛み合えば伸びる余地があるから、差し込みのリスクは残るよ。"
            )
        emotion = "joy"
        suggestions = ["対抗との差は？", "信頼度の根拠は？", "展開を詳しく"]
    elif any(k in message for k in ("リスク", "危険", "不安", "弱点")):
        reply = (
            "リスクは展開の崩れと相手関係の入れ替わりだよ。"
            "ペースが想定と違うと軸の位置取りが苦しくなるから、発走前後の気配も見ておこう。"
            "点数は抑えめにして、主軸→保険の順が安心だよ。"
        )
        emotion = "fun"
        suggestions = ["保険の入れ方は？", "点数を抑える案", "展開を詳しく"]
    elif has_strategy or any(k in message for k in ("戦略", "買い目", "評価して", "相談")):
        if any(k in message for k in ("リスク", "危険")):
            reply = (
                "この戦略のリスクは点数の広がりと展開依存だよ。"
                "軸は維持しつつ、相手は絞って保険を厚くするのがおすすめ。"
            )
        else:
            reply = (
                "戦略内容は受け取ったよ。軸は明確でいいね。"
                "点数は抑えめにして、主軸→保険→一発の順で入れると破綻しにくいよ。"
                "改善するなら相手頭数を減らして、保険側の再現性を確認しよう。"
            )
        emotion = "joy"
        suggestions = ["リスクはどこ？", "点数を抑える案", "軸を見直す"]
    elif any(k in message for k in ("買い目", "戦略")):
        reply = "買い目は軸1頭流しで点数を抑えるのがおすすめ！相手は最大3頭までにしてみよう。"
        emotion = "joy"
        suggestions = ["展開予想を教えて", "リスクを教えて", "血統について教えて"]
    elif any(k in message for k in ("展開", "ペース")):
        reply = "データ上は差し馬の評価が伸びてるよ。中盤でペースが上がる想定だね。"
        emotion = "fun"
        suggestions = ["本命を教えて", "買い目を提案して", "血統について教えて"]
    elif "血統" in message:
        reply = "血統面ではコース適性が高い産駒が目立ってるよ。"
        emotion = "fun"
        suggestions = ["展開予想を教えて", "本命を教えて", "買い目を提案して"]
    else:
        reply = (
            "内容は受け取ったよ。もう少し具体的に「理由」「リスク」「展開」のどれかで聞いてくれると答えやすいよ。"
        )
        emotion = "joy"
        suggestions = ["本命の理由は？", "リスクはどこ？", "展開を詳しく"]

    # race_id は referenced_race_id のみ。吹き出しに（対象: …）は出さない。
    return {
        "schema_version": "expect-kaoba/1.0",
        "reply": reply,
        "emotion": emotion,
        "suggestions": suggestions,
        "referenced_race_id": race_id or None,
        "provider": "rule",
        "live2d": {
            "motion": "talk_happy" if emotion == "joy" else "talk_idle",
            "expression": "smile" if emotion == "joy" else "neutral",
        },
    }


# backward-compatible aliases used by older imports
def to_prediction(bundle: dict[str, Any], race_id: str) -> dict[str, Any]:
    return normalize_prediction_bundle(bundle, race_id)


def to_confidence(bundle: dict[str, Any], race_id: str) -> dict[str, Any]:
    return project_confidence(normalize_prediction_bundle(bundle, race_id))


def to_tickets(bundle: dict[str, Any], race_id: str) -> dict[str, Any]:
    return project_tickets(normalize_prediction_bundle(bundle, race_id))


def to_prediction_summary(race: dict[str, Any]) -> dict[str, Any]:
    b = catalog_to_prediction_bundle(race)
    return {"race_id": b["race_id"], "confidence_hint": score_percent(b.get("ai_confidence"))}
