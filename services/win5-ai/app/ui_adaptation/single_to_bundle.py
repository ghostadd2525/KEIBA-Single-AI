# -*- coding: utf-8 -*-
"""
UI1 Existing UI Adaptation — View Mapper only.

Maps SingleResponse / core prediction → PredictionBundle 2.0 for existing UI.
Does NOT change Consumer, Core, Prediction engines, or Presentation contracts.
Does NOT render World / Near Miss / Affinity / Explanation Confidence on UI slots.
"""
from __future__ import annotations

from typing import Any, Mapping

BUNDLE_SCHEMA = "single-prediction-bundle/2.0"

# Same Product View mark mapping as single_prediction_mapper / PI BFF
_MARK_BY_RANK: dict[int, tuple[str, int]] = {
    1: ("honmei", 1),
    2: ("taikou", 1),
    3: ("ana", 1),
    4: ("chuuken", 1),
}

_INTERNAL_KEYS = frozenset(
    {
        "world",
        "sub_world",
        "world_id",
        "near_miss",
        "affinity",
        "explanation_confidence",
        "residual_class",
        "near_world",
        "decision_trace",
        "transition",
        "exclusion_reasons",
        "expected_strategy_ref",
        "natural_explanation",
        "decision_reason",
        "registry",
        "presentation",
        "ticket",
        "core_payload",
        "core_ref",
    }
)


def _as_int(v: Any) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _as_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _confidence_band(score: float | None) -> str:
    if score is None:
        return "unknown"
    s = score if score <= 1.0 else score / 100.0
    if s >= 0.85:
        return "high"
    if s >= 0.55:
        return "medium"
    return "low"


def _candidate_id(horse_number: int | None, horse_name: str | None) -> str:
    if horse_number is not None:
        return f"c{horse_number:02d}"
    return str(horse_name or "unknown")


def _extract_prediction(single_or_core: Mapping[str, Any]) -> dict[str, Any]:
    """Accept site wrapper, consumer single, or core_payload."""
    if not single_or_core:
        return {}
    # site-integration wrap
    if isinstance(single_or_core.get("single"), dict):
        single_or_core = single_or_core["single"]
    core = single_or_core.get("core_payload")
    if isinstance(core, dict) and isinstance(core.get("prediction"), dict):
        return dict(core["prediction"])
    pred = single_or_core.get("prediction")
    if isinstance(pred, dict):
        return dict(pred)
    return {}


def _extract_race_id(single_or_core: Mapping[str, Any], fallback: str | None = None) -> str:
    if isinstance(single_or_core.get("single"), dict):
        rid = single_or_core.get("race_id") or single_or_core["single"].get("race_id")
        if rid:
            return str(rid)
        single_or_core = single_or_core["single"]
    for key in ("race_id",):
        if single_or_core.get(key):
            return str(single_or_core[key])
    core = single_or_core.get("core_payload")
    if isinstance(core, dict) and core.get("race_id"):
        return str(core["race_id"])
    return str(fallback or "")


def _runners_from_prediction(
    prediction: Mapping[str, Any],
    *,
    base_runners: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    ranks = prediction.get("ranks") or []
    scores = prediction.get("scores") or []
    if not isinstance(ranks, list):
        ranks = []
    if not isinstance(scores, list):
        scores = []

    base_by_num: dict[int, dict[str, Any]] = {}
    base_by_name: dict[str, dict[str, Any]] = {}
    for br in base_runners or []:
        n = _as_int(br.get("horse_number"))
        if n is not None:
            base_by_num[n] = br
        name = br.get("horse_name")
        if name:
            base_by_name[str(name)] = br

    runners: list[dict[str, Any]] = []
    for i, raw in enumerate(ranks):
        rank = i + 1
        mark, mark_rank = _MARK_BY_RANK.get(rank, ("none", None))
        horse_number = _as_int(raw)
        horse_name: str | None
        if horse_number is not None:
            horse_name = None
            base = base_by_num.get(horse_number)
            if base and base.get("horse_name"):
                horse_name = str(base["horse_name"])
        else:
            horse_name = str(raw) if raw is not None else None
            horse_number = 0
            base = base_by_name.get(horse_name or "")
            if base:
                n2 = _as_int(base.get("horse_number"))
                if n2 is not None:
                    horse_number = n2

        win_prob = _as_float(scores[i]) if i < len(scores) else None
        if win_prob is not None and win_prob > 1.0:
            win_prob = win_prob / 100.0

        runner: dict[str, Any] = {
            "candidate_id": _candidate_id(horse_number if horse_number else None, horse_name),
            "horse_number": horse_number,
            "horse_name": horse_name,
            "model_rank": rank,
            "win_prob": win_prob,
            "mark": mark,
        }
        if mark_rank is not None:
            runner["mark_rank"] = mark_rank

        # Reuse ability_scores from existing Product View when horse matches
        base = base_by_num.get(horse_number) if horse_number else None
        if base is None and horse_name:
            base = base_by_name.get(horse_name)
        if base and isinstance(base.get("ability_scores"), dict):
            runner["ability_scores"] = dict(base["ability_scores"])

        runners.append(runner)

    runners.sort(key=lambda r: (r.get("model_rank") is None, r.get("model_rank") or 999))
    return runners


def _default_race_info(race_id: str, overlay: Mapping[str, Any] | None) -> dict[str, Any]:
    info = {
        "race_id": race_id or "unknown",
        "date": "unknown",
        "venue": "unknown",
        "race_no": 1,
        "post_time": None,
        "distance": None,
        "surface": None,
        "course": None,
        "class_label": None,
        "grade": None,
        "field_size": None,
        "race_status": None,
        "race_name": None,
    }
    if overlay:
        for k, v in overlay.items():
            if k in _INTERNAL_KEYS:
                continue
            if v is not None:
                info[k] = v
        info["race_id"] = race_id or str(overlay.get("race_id") or info["race_id"])
    # ExpectContractGuard: race_info.venue/date string, race_no number
    info["race_id"] = str(info.get("race_id") or race_id or "unknown")
    if not isinstance(info.get("date"), str) or not str(info.get("date") or "").strip():
        info["date"] = "unknown"
    else:
        info["date"] = str(info["date"])
    if not isinstance(info.get("venue"), str) or not str(info.get("venue") or "").strip():
        info["venue"] = "unknown"
    else:
        info["venue"] = str(info["venue"])
    try:
        info["race_no"] = int(info["race_no"])
    except (TypeError, ValueError):
        info["race_no"] = 1
    return info


def _ai_confidence_from_base(base: Mapping[str, Any] | None) -> dict[str, Any]:
    """UI confidence slot = Bundle ai_confidence only. Never EC."""
    if base and isinstance(base.get("ai_confidence"), dict):
        ac = dict(base["ai_confidence"])
        # Strip any accidental EC-shaped keys
        ac.pop("explanation_confidence", None)
        ac.pop("near_miss_confidence", None)
        if "score" not in ac:
            ac["score"] = None
        elif ac.get("score") is not None and not isinstance(ac.get("score"), (int, float)):
            try:
                ac["score"] = float(ac["score"])
            except (TypeError, ValueError):
                ac["score"] = None
        return ac
    return {
        "schema_version": "ai-confidence/1.0",
        "status": "unknown",
        "score": None,
        "score_unit": "normalized",
        "band": "unknown",
        "inputs_ref": None,
        "factors": [],
        "component_scores": {},
        "notes": None,
        "computed_at": None,
    }


def _explain_from_base(base: Mapping[str, Any] | None) -> dict[str, Any]:
    """Keep existing explain for UI; strip world/sub_world from meta."""
    if base and isinstance(base.get("explain"), dict):
        ex = dict(base["explain"])
        meta = dict(ex.get("meta") or {})
        meta["world"] = None
        meta["sub_world"] = None
        ex["meta"] = meta
        if not isinstance(ex.get("narrative"), str):
            ex["narrative"] = ""
        if not isinstance(ex.get("reasons"), list):
            ex["reasons"] = []
        return ex
    return {
        "meta": {"world": None, "sub_world": None, "strategy_id": None, "confidence_band": None},
        "reasons": [],
        "narrative": "",
    }


def ensure_prediction_bundle_contract(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """UI3 — satisfy ExpectContractGuard.validatePredictionBundle."""
    out = dict(bundle)
    rid = out.get("race_id")
    if not isinstance(rid, str) or not rid.strip():
        ri0 = out.get("race_info") if isinstance(out.get("race_info"), dict) else {}
        rid = str((ri0 or {}).get("race_id") or "unknown")
    out["race_id"] = rid
    out["schema_version"] = BUNDLE_SCHEMA
    out["race_info"] = _default_race_info(rid, out.get("race_info") if isinstance(out.get("race_info"), dict) else None)

    ev = out.get("evaluation") if isinstance(out.get("evaluation"), dict) else {}
    out["evaluation"] = {
        "status": ev.get("status") or "unknown",
        "world": ev.get("world"),
        "sub_world": ev.get("sub_world"),
        "runners": list(ev.get("runners") or []) if isinstance(ev.get("runners"), list) else [],
    }
    out["ai_confidence"] = _ai_confidence_from_base({"ai_confidence": out.get("ai_confidence")})
    out["explain"] = _explain_from_base({"explain": out.get("explain")})
    bets = out.get("betting_recommendations")
    if not isinstance(bets, dict):
        bets = {"schema_version": "betting-recommendations/1.0", "items": []}
    else:
        bets = dict(bets)
        if not isinstance(bets.get("items"), list):
            bets["items"] = []
    out["betting_recommendations"] = bets
    return out


def sanitize_bundle_for_existing_ui(bundle: dict[str, Any]) -> dict[str, Any]:
    """Ensure internal Core terms are not carried into UI-facing Product View fields."""
    out = dict(bundle)
    ev = dict(out.get("evaluation") or {})
    ev["world"] = None
    ev["sub_world"] = None
    out["evaluation"] = ev

    ex = dict(out.get("explain") or {})
    meta = dict(ex.get("meta") or {})
    meta["world"] = None
    meta["sub_world"] = None
    ex["meta"] = meta
    out["explain"] = ex

    # Never attach presentation / registry onto Bundle
    for k in (
        "presentation",
        "registry",
        "near_miss",
        "affinity",
        "explanation_confidence",
        "ticket",
        "core_payload",
        "natural_explanation",
        "decision_reason",
    ):
        out.pop(k, None)
    return out


def map_single_to_prediction_bundle(
    single_or_core: Mapping[str, Any],
    *,
    race_id: str | None = None,
    race_info: Mapping[str, Any] | None = None,
    base_bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    View Mapper: Single/Core prediction → PredictionBundle 2.0.

    - Marks / ranks from core prediction
    - ai_confidence / ability_scores / explain / bets preserved from base_bundle when provided
      (existing Product View supply) — never from Explanation Confidence
    - Internal terms nulled on UI-facing fields
    """
    rid = race_id or _extract_race_id(single_or_core)
    prediction = _extract_prediction(single_or_core)
    base = dict(base_bundle) if base_bundle else {}
    base_runners = []
    if isinstance(base.get("evaluation"), dict):
        runners = base["evaluation"].get("runners")
        if isinstance(runners, list):
            base_runners = [dict(r) for r in runners if isinstance(r, dict)]

    runners = _runners_from_prediction(prediction, base_runners=base_runners)
    if not runners and base_runners:
        # Fallback: keep existing runners if Single had empty prediction (should be rare)
        runners = base_runners

    info_overlay = race_info or (base.get("race_info") if isinstance(base.get("race_info"), dict) else None)
    race_info_out = _default_race_info(rid, info_overlay)
    if runners and race_info_out.get("field_size") is None:
        race_info_out["field_size"] = len(runners)

    bets = base.get("betting_recommendations")
    if not isinstance(bets, dict):
        bets = {"schema_version": "betting-recommendations/1.0", "items": []}
    elif not isinstance(bets.get("items"), list):
        bets = {**bets, "items": []}

    bundle: dict[str, Any] = {
        "schema_version": BUNDLE_SCHEMA,
        "race_id": rid,
        "race_info": race_info_out,
        "evaluation": {
            "status": "ok" if runners else "partial",
            "world": None,
            "sub_world": None,
            "runners": runners,
        },
        "ai_confidence": _ai_confidence_from_base(base),
        "explain": _explain_from_base(base),
        "betting_recommendations": bets,
        "warnings": list(base.get("warnings") or []),
        "model_version": base.get("model_version"),
        "generated_at": base.get("generated_at"),
    }
    return ensure_prediction_bundle_contract(sanitize_bundle_for_existing_ui(bundle))


def assert_no_internal_terms_leaked(bundle: Mapping[str, Any]) -> list[str]:
    """Test helper: UI-facing fields must not expose internal labels as values to show."""
    leaks: list[str] = []
    ev = bundle.get("evaluation") or {}
    if ev.get("world") not in (None, ""):
        leaks.append("evaluation.world")
    if ev.get("sub_world") not in (None, ""):
        leaks.append("evaluation.sub_world")
    for k in ("near_miss", "affinity", "explanation_confidence", "presentation", "registry"):
        if k in bundle and bundle.get(k) is not None:
            leaks.append(k)
    meta = (bundle.get("explain") or {}).get("meta") or {}
    if meta.get("world") not in (None, ""):
        leaks.append("explain.meta.world")
    return leaks
