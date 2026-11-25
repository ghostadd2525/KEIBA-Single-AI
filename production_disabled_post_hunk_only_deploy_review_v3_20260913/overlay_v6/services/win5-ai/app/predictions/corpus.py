# -*- coding: utf-8 -*-
"""Read-only corpus: eligible predictions JOIN race_results ON race_id."""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from ..data.db import connect
from .provenance import PERSIST_SOURCE_SITE_PREDICTION_RUN, training_auto_adopt
from .raeval84_holdout import (
    assert_raeval84_not_in_train_or_val,
    load_raeval84_holdout,
)
from .snapshot import horse_number_key, parse_iso

JOIN_SQL = """
SELECT
  p.id AS prediction_id,
  p.race_id,
  p.persist_source,
  p.engine_source,
  p.fallback_reason,
  p.model_version,
  p.bundle_json,
  p.input_snapshot_hash,
  p.prediction_semantic_hash,
  p.created_at,
  r.race_date,
  r.field_size AS result_field_size,
  r.winner_horse_number,
  r.result_json,
  r.source AS result_source,
  r.finalized_at
FROM predictions p
INNER JOIN race_results r ON r.race_id = p.race_id
ORDER BY p.race_id ASC, p.id ASC
"""

CHRONOLOGY_BEFORE = "BEFORE"
CHRONOLOGY_EQUAL = "EQUAL"
CHRONOLOGY_AFTER = "AFTER"
CHRONOLOGY_MISSING = "MISSING"
CHRONOLOGY_INVALID = "INVALID"
CHRONOLOGY_POLICY = "prediction-unit"
HOLDOUT_POLICY = "race_id"

OFFICIAL_STARTER_KEYS = (
    "expected_starters",
    "official_starters",
    "starters",
    "declared_starters",
)


def coerce_field_size(raw: Any) -> int | None:
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _result_payload(result_json: Any) -> dict[str, Any]:
    if isinstance(result_json, str) and result_json:
        try:
            loaded = json.loads(result_json)
            if isinstance(loaded, dict):
                return loaded
        except json.JSONDecodeError:
            return {}
    if isinstance(result_json, dict):
        return result_json
    return {}


def _unique_horse_list(raw: Any) -> list[int] | None:
    """不正・重複・空は None（fail-closed）。"""
    if not isinstance(raw, list) or not raw:
        return None
    out: list[int] = []
    seen: set[int] = set()
    for item in raw:
        key = horse_number_key(item)
        if key is None:
            return None
        n = int(key)
        if n in seen:
            return None
        seen.add(n)
        out.append(n)
    return out


def parse_official_finish_order(result_json: Any) -> tuple[list[int], str]:
    """winner_horse_number fallback は使わない。"""
    payload = _result_payload(result_json)
    raw = payload.get("finish_order")
    if raw is None:
        raw = payload.get("chakujun")
    if isinstance(raw, list) and raw:
        parsed = _unique_horse_list(raw)
        if parsed is not None:
            return parsed, "order"
        return [], "invalid"
    by_number = payload.get("by_number")
    if isinstance(by_number, dict) and by_number:
        pairs: list[tuple[int, int]] = []
        seen: set[int] = set()
        for hn, place in by_number.items():
            key = horse_number_key(hn)
            try:
                plc = int(place)
            except (TypeError, ValueError):
                return [], "invalid"
            if key is None:
                return [], "invalid"
            n = int(key)
            if n in seen:
                return [], "invalid"
            seen.add(n)
            pairs.append((plc, n))
        pairs.sort()
        return [hn for _, hn in pairs], "by_number"
    return [], "absent"


def parse_official_expected_starters(result_json: Any) -> list[int] | None:
    """result_json 上の公式出走集合だけ。bundle / snapshot は使わない。"""
    payload = _result_payload(result_json)
    declared = False
    for key in OFFICIAL_STARTER_KEYS:
        if key not in payload:
            continue
        declared = True
        parsed = _unique_horse_list(payload.get(key))
        if parsed is None:
            return None
        return parsed
    _ = declared
    return None


def inspect_bundle_runners(bundle: dict[str, Any] | None) -> tuple[list[int] | None, str]:
    """1行でも不正・欠落・重複なら numbers=None。"""
    if not isinstance(bundle, dict):
        return None, "bundle_not_object"
    runners = (bundle.get("evaluation") or {}).get("runners") if isinstance(bundle.get("evaluation"), dict) else None
    if runners is None:
        return None, "runners_missing"
    if isinstance(runners, dict):
        if not runners:
            return None, "runners_empty"
        out: list[int] = []
        seen: set[int] = set()
        for raw_key, row in runners.items():
            if not isinstance(row, dict):
                return None, "runner_row_not_object"
            key = horse_number_key(row.get("horse_number"))
            map_key = horse_number_key(raw_key)
            if key is None or map_key is None or key != map_key:
                return None, "horse_number_invalid"
            n = int(key)
            if n in seen:
                return None, "horse_number_duplicate"
            seen.add(n)
            out.append(n)
        return out, "ok"
    if isinstance(runners, list):
        if not runners:
            return None, "runners_empty"
        out = []
        seen = set()
        for row in runners:
            if not isinstance(row, dict):
                return None, "runner_row_not_object"
            key = horse_number_key(row.get("horse_number"))
            if key is None:
                return None, "horse_number_invalid"
            n = int(key)
            if n in seen:
                return None, "horse_number_duplicate"
            seen.add(n)
            out.append(n)
        return out, "ok"
    return None, "runners_type_invalid"


def _bundle_horse_numbers(bundle: dict[str, Any]) -> list[int] | None:
    numbers, _reason = inspect_bundle_runners(bundle)
    return numbers


def finish_scope(
    bundle_horse_numbers: list[int] | None,
    finish_order: list[int],
    expected_starters: list[int] | None = None,
    result_field_size: int | None = None,
    *,
    finish_is_winner_fallback: bool = False,
) -> str:
    """FULL_FIELD は公式期待出走集合と結果集合と bundle の厳密一致。

    expected_starters は独立した公式集合だけ。未確定なら fail-closed。
    winner_horse_number 1頭 fallback は FULL_FIELD に使わない。
    """
    if bundle_horse_numbers is None:
        return "UNLABELABLE"
    try:
        nums = [int(n) for n in bundle_horse_numbers]
    except (TypeError, ValueError):
        return "UNLABELABLE"
    if not nums or len(nums) != len(set(nums)) or any(n <= 0 for n in nums):
        return "UNLABELABLE"
    if finish_is_winner_fallback:
        return "UNLABELABLE"
    try:
        finish = [int(n) for n in finish_order]
    except (TypeError, ValueError):
        return "UNLABELABLE"
    if not finish or len(finish) != len(set(finish)) or any(n <= 0 for n in finish):
        return "UNLABELABLE"
    field = coerce_field_size(result_field_size)
    if expected_starters is None:
        if field is None:
            return "UNLABELABLE"
        if len(finish) != field:
            return "PARTIAL_RESULT"
        expected = list(finish)
    else:
        try:
            expected = [int(n) for n in expected_starters]
        except (TypeError, ValueError):
            return "UNLABELABLE"
        if not expected or len(expected) != len(set(expected)) or any(n <= 0 for n in expected):
            return "UNLABELABLE"
    if field is not None:
        if len(expected) != field or len(finish) != field or len(nums) != field:
            return "PARTIAL_RESULT"
    if set(expected) == set(finish) == set(nums):
        return "FULL_FIELD"
    return "PARTIAL_RESULT"


def prediction_result_chronology(created_at: Any, finalized_at: Any) -> str:
    """prediction が結果確定前であること。同時刻・欠落・不正は fail-closed。"""
    if created_at in (None, "") or finalized_at in (None, ""):
        return CHRONOLOGY_MISSING
    pred = parse_iso(str(created_at))
    fin = parse_iso(str(finalized_at))
    if pred is None or fin is None:
        return CHRONOLOGY_INVALID
    if pred < fin:
        return CHRONOLOGY_BEFORE
    if pred == fin:
        return CHRONOLOGY_EQUAL
    return CHRONOLOGY_AFTER


def chronology_ok(status: str) -> bool:
    return status == CHRONOLOGY_BEFORE


def _fingerprint_status(bundle: dict[str, Any]) -> str | None:
    prov = bundle.get("persist_provenance") if isinstance(bundle.get("persist_provenance"), dict) else {}
    return prov.get("fingerprint_status")


def _row_from_join(raw: dict[str, Any]) -> dict[str, Any]:
    try:
        bundle = json.loads(raw.get("bundle_json") or "{}")
    except json.JSONDecodeError:
        bundle = {}
    if not isinstance(bundle, dict):
        bundle = {}
    snap = bundle.get("prediction_time_features") if isinstance(bundle.get("prediction_time_features"), dict) else None
    finish, finish_kind = parse_official_finish_order(raw.get("result_json"))
    horses, runner_reason = inspect_bundle_runners(bundle)
    expected = parse_official_expected_starters(raw.get("result_json"))
    field = coerce_field_size(raw.get("result_field_size"))
    if field is None:
        field = coerce_field_size(_result_payload(raw.get("result_json")).get("field_size"))
    scope = finish_scope(
        horses,
        finish,
        expected,
        field,
        finish_is_winner_fallback=False,
    )
    if finish_kind == "invalid" or runner_reason != "ok":
        scope = "UNLABELABLE"
    chrono = prediction_result_chronology(raw.get("created_at"), raw.get("finalized_at"))
    eligible = training_auto_adopt(
        persist_source=raw.get("persist_source"),
        engine_source=raw.get("engine_source"),
        fallback_reason=raw.get("fallback_reason"),
        snapshot=snap,
        fingerprint_status=_fingerprint_status(bundle),
        model_version=raw.get("model_version"),
    )
    return {
        "prediction_id": raw.get("prediction_id"),
        "race_id": raw.get("race_id"),
        "persist_source": raw.get("persist_source"),
        "engine_source": raw.get("engine_source"),
        "fallback_reason": raw.get("fallback_reason"),
        "model_version": raw.get("model_version"),
        "input_snapshot_hash": raw.get("input_snapshot_hash"),
        "prediction_semantic_hash": raw.get("prediction_semantic_hash"),
        "created_at": raw.get("created_at"),
        "finalized_at": raw.get("finalized_at"),
        "chronology_status": chrono,
        "chronology_ok": chronology_ok(chrono),
        "race_date": raw.get("race_date"),
        "result_source": raw.get("result_source"),
        "result_field_size": field,
        "finish_order": finish,
        "finish_scope": scope,
        "training_eligible": eligible,
        "capture_status": (snap or {}).get("capture_status"),
        "bundle": bundle,
    }


def iter_joined_predictions() -> list[dict[str, Any]]:
    """全 predictions ⋈ race_results。学習 canon は latest-by-time ではない。"""
    conn = connect()
    try:
        rows = [dict(r) for r in conn.execute(JOIN_SQL).fetchall()]
    finally:
        conn.close()
    return [_row_from_join(r) for r in rows]


def iter_eligible_joined() -> list[dict[str, Any]]:
    """site_prediction_run かつ training_auto_adopt を満たす行のみ。"""
    out: list[dict[str, Any]] = []
    for row in iter_joined_predictions():
        if row.get("persist_source") != PERSIST_SOURCE_SITE_PREDICTION_RUN:
            continue
        if not row.get("training_eligible"):
            continue
        out.append(row)
    return out


def races_excluded_as_partial(items: list[dict[str, Any]]) -> set[str]:
    bad: set[str] = set()
    for row in items:
        if row.get("finish_scope") != "FULL_FIELD":
            bad.add(str(row["race_id"]))
    return bad


def holdout_eval_rows(
    items: list[dict[str, Any]] | None = None,
    *,
    holdout_path: Any = None,
    holdout_sha: str | None = None,
) -> list[dict[str, Any]]:
    """RAEVAL84 race の行。test/validation 用に保持可。train/val には使わない。"""
    holdout = load_raeval84_holdout(holdout_path, expected_sha=holdout_sha)
    rows = items if items is not None else iter_eligible_joined()
    return [row for row in rows if str(row.get("race_id") or "") in holdout]


def training_rows(
    items: list[dict[str, Any]] | None = None,
    *,
    holdout_path: Any = None,
    holdout_sha: str | None = None,
) -> list[dict[str, Any]]:
    """学習 train/val 宇宙。split 前に RAEVAL84 race_id を除外する。

    時系列は prediction 単位（推奨）。PARTIAL_RESULT は race 単位除外。
    holdout 成果物の破損は学習停止。
    """
    holdout = load_raeval84_holdout(holdout_path, expected_sha=holdout_sha)
    rows = items if items is not None else iter_eligible_joined()
    excluded = races_excluded_as_partial(rows)
    out: list[dict[str, Any]] = []
    for row in rows:
        rid = str(row["race_id"])
        if rid in holdout:
            continue
        if not chronology_ok(str(row.get("chronology_status") or "")):
            continue
        if rid in excluded:
            continue
        if row.get("finish_scope") != "FULL_FIELD":
            continue
        out.append(row)
    return out


def assign_race_level_split(
    race_dates: list[tuple[str, str]],
    *,
    train_until: str,
    val_until: str,
    holdout_race_ids: frozenset[str] | None = None,
    holdout_path: Any = None,
    holdout_sha: str | None = None,
) -> dict[str, str]:
    """分割単位は race_id。同一レースの全予測が同じ bucket。

    RAEVAL84 84 race_id は train/val に入らず holdout に固定する。
    """
    holdout = (
        holdout_race_ids
        if holdout_race_ids is not None
        else load_raeval84_holdout(holdout_path, expected_sha=holdout_sha)
    )
    assigned: dict[str, str] = {}
    for race_id, date in race_dates:
        rid = str(race_id)
        if rid in holdout:
            split = "holdout"
        elif date <= train_until:
            split = "train"
        elif date <= val_until:
            split = "val"
        else:
            split = "test"
        if rid in assigned and assigned[rid] != split:
            raise RuntimeError("same_race_split_conflict")
        assigned[rid] = split
    assert_raeval84_not_in_train_or_val(assigned, holdout)
    return assigned


def predictions_share_race_split(
    prediction_rows: list[dict[str, Any]],
    race_split: dict[str, str],
) -> bool:
    by_race: dict[str, set[str]] = defaultdict(set)
    for row in prediction_rows:
        rid = str(row["race_id"])
        by_race[rid].add(race_split[rid])
    return all(len(splits) == 1 for splits in by_race.values())
