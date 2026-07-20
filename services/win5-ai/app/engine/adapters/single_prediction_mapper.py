"""
Single AI prediction_response → PredictionBundle (single-prediction-bundle/2.0)

契約スキーマは変更しない。Product 応答 dict を Expect 契約形へ投影するだけ。
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import domains

_VENUE_EN_TO_JA = {
    "sapporo": "札幌",
    "hakodate": "函館",
    "fukushima": "福島",
    "niigata": "新潟",
    "tokyo": "東京",
    "nakayama": "中山",
    "chukyo": "中京",
    "kyoto": "京都",
    "hanshin": "阪神",
    "kokura": "小倉",
}

_MARK_BY_RANK = {
    1: ("honmei", 1),
    2: ("taikou", 1),
    3: ("ana", 1),
    4: ("chuuken", 1),
}

_ORDERED_BETS = {"exacta", "trifecta"}


def ensure_ai_platform_path() -> bool:
    """ai_platform を import できるよう sys.path を補正する。"""
    return locate_ai_platform_root() is not None


def locate_ai_platform_root() -> Path | None:
    """Return platform root that contains ai_platform/, or None."""
    if "ai_platform" in sys.modules:
        mod = sys.modules["ai_platform"]
        root = Path(getattr(mod, "__file__", "")).resolve().parent.parent
        if (root / "ai_platform").is_dir():
            return root
    candidates: list[Path] = []
    env_root = (os.environ.get("AI_PLATFORM_ROOT") or "").strip()
    if env_root:
        candidates.append(Path(env_root))
    here = Path(__file__).resolve()
    for idx in (6, 5, 4, 3):
        if idx < len(here.parents):
            candidates.append(here.parents[idx])
    cwd = Path.cwd()
    candidates.extend([cwd, cwd.parent, cwd.parent.parent])
    for root in candidates:
        if (root / "ai_platform").is_dir():
            s = str(root)
            if s not in sys.path:
                sys.path.insert(0, s)
            return root
    return None


def classify_feature_availability(core_race_id: str) -> str | None:
    """
    Core race の特徴量有無を分類。
    Returns None if loadable; otherwise a fallback_reason code.
    """
    root = locate_ai_platform_root()
    if root is None:
        return "platform_missing"
    data = root / "data"
    candidates = (
        data / "demo_daily_outputs" / str(core_race_id)[:10] / "demo_runners_pace_market_features.csv",
        data / "demo_daily_outputs" / str(core_race_id)[:10] / "Demo_runners_pace_market_features.csv",
        data / "demo_runners_pace_market_features.csv",
        data / "Demo_runners_pace_market_features.csv",
        data / "runners_pace_market_features.csv",
        data / "Runners_pace_market_features.csv",
    )
    existing = [p for p in candidates if p.exists()]
    if not existing:
        return "feature_csv_missing"
    try:
        import csv

        for path in existing:
            with path.open(encoding="utf-8-sig", newline="") as fh:
                for row in csv.DictReader(fh):
                    if str(row.get("race_id") or "") == str(core_race_id):
                        return None
        # ファイルはあるが当該 race 行が無い → market features 不足
        return "market_feature_missing"
    except Exception:
        return "feature_missing"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _band(score: float | None) -> str:
    if score is None:
        return "unknown"
    if score >= 0.85:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def _parse_expect_slug(race_id: str) -> tuple[str, str, int] | None:
    """20260719_hanshin_11 → (2026-07-19, hanshin, 11)"""
    m = re.fullmatch(r"(\d{8})_([A-Za-z0-9]+)_(\d+)", str(race_id or "").strip())
    if not m:
        return None
    raw_date, venue_key, race_no = m.group(1), m.group(2).lower(), int(m.group(3))
    date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
    return date, venue_key, race_no


def _core_resolvable(race_id: str) -> bool:
    try:
        from ai_platform.core.facade import predict_ranking

        return predict_ranking(race_id) is not None
    except Exception:
        return False


def resolve_core_race_id(race_id: str, race_meta: dict[str, Any] | None = None) -> str | None:
    """
    Expect / Core 双方の race_id を Core が解決できる ID に寄せる。
    解決不能なら None（呼び出し側で Mock フォールバック）。
    """
    rid = str(race_id or "").strip()
    if not rid:
        return None
    if _core_resolvable(rid):
        return rid

    from ai_platform.race_data import get_race_by_keys, list_races

    date = ""
    venue = ""
    race_no: int | None = None
    meta = race_meta or {}
    if meta.get("date"):
        date = str(meta["date"])
    if meta.get("venue"):
        venue = str(meta["venue"])
    if meta.get("race_no") is not None:
        race_no = _as_int(meta.get("race_no"))

    parsed = _parse_expect_slug(rid)
    if parsed:
        date = date or parsed[0]
        venue = venue or _VENUE_EN_TO_JA.get(parsed[1], parsed[1])
        race_no = race_no if race_no is not None else parsed[2]

    if date and venue and race_no is not None:
        row = get_race_by_keys(date, venue, race_no)
        if row and row.get("race_id") and _core_resolvable(str(row["race_id"])):
            return str(row["race_id"])
        constructed = f"{date}-{venue}-{race_no}"
        if _core_resolvable(constructed):
            return constructed

    if date:
        for row in list_races(date=date, venue=venue or None, race_no=race_no, limit=50):
            cid = str(row.get("race_id") or "")
            if not cid:
                continue
            if venue and str(row.get("venue") or "") != venue and venue not in cid:
                continue
            if race_no is not None and _as_int(row.get("race_no")) != race_no:
                continue
            if _core_resolvable(cid):
                return cid

    # 明示マップ: AI_RACE_ID_MAP='{"20260719_hanshin_11":"2026-07-19-04-11"}'
    raw_map = (os.environ.get("AI_RACE_ID_MAP") or "").strip()
    if raw_map:
        import json

        try:
            mapping = json.loads(raw_map)
            mapped = mapping.get(rid)
            if mapped and _core_resolvable(str(mapped)):
                return str(mapped)
        except json.JSONDecodeError:
            pass

    return None


def _candidate_id(horse_number: int | None, horse_name: str) -> str:
    if horse_number is not None:
        return f"c{horse_number:02d}"
    return horse_name or "unknown"


def _runners_from_ranking(ranking: list[dict[str, Any]]) -> list[dict[str, Any]]:
    runners: list[dict[str, Any]] = []
    for row in ranking or []:
        horse_number = _as_int(row.get("horse_number"))
        horse_name = str(row.get("horse_name") or "")
        rank = _as_int(row.get("rank"))
        score = _as_float(row.get("score"))
        mark, mark_rank = _MARK_BY_RANK.get(rank or 0, ("none", None))
        runner: dict[str, Any] = {
            "candidate_id": _candidate_id(horse_number, horse_name),
            "horse_number": horse_number if horse_number is not None else 0,
            "horse_name": horse_name or None,
            "model_rank": rank,
            "win_prob": score,
            "mark": mark,
        }
        if mark_rank is not None:
            runner["mark_rank"] = mark_rank
        runners.append(runner)
    runners.sort(key=lambda r: (r.get("model_rank") is None, r.get("model_rank") or 999))
    return runners


def _race_info(
    public_race_id: str,
    core_race_id: str,
    race_meta: dict[str, Any] | None,
) -> dict[str, Any]:
    from ai_platform.race_data import get_race

    meta = dict(race_meta or {})
    core_row = get_race(core_race_id) or {}
    date = str(meta.get("date") or core_row.get("date") or "")
    venue = str(meta.get("venue") or core_row.get("venue") or "")
    race_no = _as_int(meta.get("race_no") if meta.get("race_no") is not None else core_row.get("race_no"))
    surface_raw = meta.get("surface") or core_row.get("surface")
    surface = None
    if surface_raw is not None:
        s = str(surface_raw)
        if s in ("芝", "turf"):
            surface = "turf"
        elif s in ("ダ", "ダート", "dirt"):
            surface = "dirt"
        else:
            surface = s
    distance = meta.get("distance")
    if distance is None:
        distance = _as_int(core_row.get("distance"))
    else:
        distance = _as_int(distance) if not isinstance(distance, (int, float)) else distance

    meeting_id = meta.get("meeting_id") or core_row.get("meeting_id")
    if not meeting_id and date and venue:
        meeting_id = f"{date.replace('-', '')}_{venue}"

    return {
        "race_id": public_race_id,
        "date": date or "unknown",
        "venue": venue or "unknown",
        "meeting_id": meeting_id,
        "race_no": race_no if race_no is not None else 1,
        "post_time": meta.get("post_time"),
        "distance": distance,
        "surface": surface,
        "course": meta.get("course"),
        "class_label": meta.get("class_label") or core_row.get("race_name"),
        "grade": meta.get("badge") or meta.get("grade"),
        "field_size": _as_int(meta.get("field_size") or core_row.get("field_size")),
        "race_status": meta.get("status") or core_row.get("status") or "scheduled",
        "date_label": meta.get("date_label"),
        "date_full": meta.get("date_full"),
        "bg": meta.get("bg"),
    }


def _items_from_slips(
    slips: list[dict[str, Any]],
    runners: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    by_num = {
        r["horse_number"]: r
        for r in runners
        if isinstance(r.get("horse_number"), int) and r["horse_number"] > 0
    }
    items: list[dict[str, Any]] = []
    by_bet_type: dict[str, list[str]] = {}
    for idx, slip in enumerate(slips or [], start=1):
        bet_type = str(slip.get("BetType") or "unknown")
        struct = slip.get("selection_struct") or []
        legs: list[dict[str, Any]] = []
        for pos, token in enumerate(struct, start=1):
            hn = _as_int(token)
            if hn is None:
                continue
            runner = by_num.get(hn) or {}
            legs.append(
                {
                    "position": pos,
                    "horse_number": hn,
                    "candidate_id": runner.get("candidate_id") or _candidate_id(hn, ""),
                }
            )
        if not legs:
            continue
        rec_id = f"{bet_type}-{idx}"
        ordered = bet_type in _ORDERED_BETS
        item = {
            "recommendation_id": rec_id,
            "bet_type": bet_type,
            "combination": {
                "schema_version": "single-combination/1.0",
                "selection_mode": "exact_order" if ordered else "combination",
                "is_ordered": ordered,
                "cardinality": len(legs),
                "legs": legs,
            },
            "recommendation_rank": idx,
            "recommendation_score": _as_float(slip.get("Confidence")),
            "score_unit": "normalized",
            "comment": slip.get("Reason"),
            "legs_display": slip.get("Selection"),
            "derived_from": {
                "strategy_type": slip.get("strategy_type"),
                "formation": slip.get("formation"),
                "builder_version": slip.get("builder_version"),
            },
        }
        items.append(item)
        by_bet_type.setdefault(bet_type, []).append(rec_id)
    return items, by_bet_type


def prediction_response_to_bundle(
    response: dict[str, Any],
    *,
    public_race_id: str,
    core_race_id: str,
    race_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """ai_platform.single.models.prediction_response dict → PredictionBundle."""
    ranking = list(response.get("ranking") or [])
    confidence = dict(response.get("confidence") or {})
    runners = _runners_from_ranking(ranking)
    overall = _as_float(confidence.get("overall"))
    factors = [str(f) for f in (confidence.get("factors") or [])]
    items, by_bet_type = _items_from_slips(list(response.get("items") or []), runners)

    top = runners[:3]
    narrative_bits = []
    if top:
        names = "・".join(
            f"{r.get('horse_number')}{r.get('horse_name') or ''}" for r in top if r.get("horse_number")
        )
        narrative_bits.append(f"上位評価: {names}")
    if overall is not None:
        narrative_bits.append(f"総合確信度 {overall:.3f}")
    narrative = "。".join(narrative_bits) if narrative_bits else "Single AI 推論結果"

    reasons = []
    for r in top:
        bullets = []
        if r.get("model_rank") == 1:
            bullets.append("モデル順位1位")
        if isinstance(r.get("win_prob"), (int, float)):
            bullets.append(f"スコア {float(r['win_prob']):.3f}")
        if factors:
            bullets.append(factors[0])
        reasons.append(
            {
                "candidate_id": r.get("candidate_id"),
                "horse_number": r.get("horse_number"),
                "bullets": bullets or ["評価上位"],
            }
        )

    warnings = [str(w) for w in (response.get("warnings") or [])]
    if core_race_id != public_race_id:
        warnings.append(f"core_race_id={core_race_id}")

    bundle = {
        "schema_version": domains.BUNDLE_SCHEMA,
        "race_id": public_race_id,
        "generated_at": response.get("GeneratedAt") or _now(),
        "model_version": response.get("ModelVersion") or "core-delegated",
        "core_version": response.get("CoreVersion"),
        "product_version": response.get("ProductVersion"),
        "status": "ok",
        "warnings": warnings,
        "race_info": _race_info(public_race_id, core_race_id, race_meta),
        "evaluation": {
            "status": "ok",
            "world": None,
            "sub_world": None,
            "runners": runners,
        },
        "ai_confidence": {
            "schema_version": "single-ai-confidence/1.0",
            "status": "ok",
            "score": overall,
            "score_unit": "normalized",
            "band": _band(overall),
            "inputs_ref": {
                "schema_version": "single-confidence-inputs-ref/1.0",
                "core_race_id": core_race_id,
                "used_channels": ["single_ai_prediction"],
            },
            "factors": factors,
            "component_scores": {},
            "notes": "mapped from Single AI prediction_response",
            "computed_at": response.get("GeneratedAt") or _now(),
        },
        "explain": {
            "meta": {
                "core_race_id": core_race_id,
                "confidence_band": _band(overall),
                "product_version": response.get("ProductVersion"),
            },
            "reasons": reasons,
            "narrative": narrative,
        },
        "betting_recommendations": {
            "schema_version": "single-betting-recommendations/1.0",
            "race_id": public_race_id,
            "generated_at": response.get("GeneratedAt") or _now(),
            "strategy_id": "single-ai-bet-builder",
            "status": "ok" if items else "empty",
            "items": items,
            "by_bet_type": by_bet_type,
        },
    }
    return domains.normalize_prediction_bundle(bundle, public_race_id)


def run_single_prediction(core_race_id: str) -> dict[str, Any] | None:
    """Single AI 公開入口 get_prediction を呼び、エラー応答なら None。"""
    resp, _reason = run_single_prediction_detailed(core_race_id)
    return resp


def run_single_prediction_detailed(
    core_race_id: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Returns (response, fallback_reason_if_failed).
    fallback_reason is None on success.
    """
    try:
        from ai_platform.single.api import get_prediction
    except Exception:
        return None, "model_not_loaded"

    try:
        resp = get_prediction(core_race_id)
    except TimeoutError:
        return None, "timeout"
    except Exception:
        return None, "exception"

    if not isinstance(resp, dict):
        return None, "prediction_failed"
    if resp.get("error_code"):
        code = str(resp.get("error_code") or "")
        if code in ("race_not_resolved", "missing_race_id"):
            return None, "race_not_found"
        return None, "prediction_failed"
    return resp, None


def diagnose_inference(
    public_race_id: str,
    race_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    実推論診断。成功時 engine_source=real_ai、失敗時は fallback_reason 付き。
    """
    out: dict[str, Any] = {
        "race_id": public_race_id,
        "ok": False,
        "engine_source": "mock_fallback",
        "fallback_reason": "unknown",
        "core_race_id": None,
        "detail": None,
        "bundle": None,
    }
    if locate_ai_platform_root() is None:
        out["fallback_reason"] = "platform_missing"
        out["detail"] = "ai_platform not found on sys.path / AI_PLATFORM_ROOT"
        return out

    try:
        core_id = resolve_core_race_id(public_race_id, race_meta)
    except Exception as exc:
        out["fallback_reason"] = "exception"
        out["detail"] = f"resolve_core_race_id: {exc}"
        return out

    if not core_id:
        out["fallback_reason"] = "race_not_found"
        out["detail"] = "no resolvable core race_id"
        return out

    out["core_race_id"] = core_id
    feat_reason = classify_feature_availability(core_id)
    if feat_reason:
        out["fallback_reason"] = feat_reason
        out["detail"] = f"features unavailable for {core_id}"
        return out

    try:
        response, fail_reason = run_single_prediction_detailed(core_id)
        if not response:
            out["fallback_reason"] = fail_reason or "prediction_failed"
            out["detail"] = f"get_prediction failed for {core_id}"
            return out
        bundle = prediction_response_to_bundle(
            response,
            public_race_id=public_race_id,
            core_race_id=core_id,
            race_meta=race_meta,
        )
        out.update(
            {
                "ok": True,
                "engine_source": "real_ai",
                "fallback_reason": None,
                "detail": None,
                "bundle": bundle,
            }
        )
        return out
    except Exception as exc:
        out["fallback_reason"] = "exception"
        out["detail"] = str(exc)
        return out
