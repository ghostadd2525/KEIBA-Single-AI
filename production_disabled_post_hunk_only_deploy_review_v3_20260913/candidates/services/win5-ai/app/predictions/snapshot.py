# -*- coding: utf-8 -*-
"""Prediction-time feature snapshot: canonicalize, collect, validate, hashes."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any

BUNDLE_SCHEMA = "single-prediction-bundle/2.0"
SNAPSHOT_SCHEMA = "prediction-time-features/1.0"
PREDICTION_CONTRACT_VERSION = "prediction-outputs/1.0"
FEATURE_SNAPSHOT_SCHEMA_VERSION = SNAPSHOT_SCHEMA
HEAD_TOP2 = "top2_prob"
HEAD_TOP3 = "top3_prob"
SEMANTIC_ALWAYS_KEYS = ("win_prob", "model_rank", "mark")
SEMANTIC_FUTURE_HEAD_KEYS = (HEAD_TOP2, HEAD_TOP3)
SNAPSHOT_FORBIDDEN_OUTPUT_KEYS = (HEAD_TOP2, HEAD_TOP3)

RACE_SNAPSHOT_KEYS = (
    "distance",
    "surface",
    "field_size",
    "class_label",
    "track_condition",
    "weather",
)
RUNNER_SNAPSHOT_KEYS = (
    "frame_number",
    "popularity",
    "win_odds",
    "horse_weight",
    "weight_change",
    "oikiri_time",
    "oikiri_rating",
    "sire",
    "damsire",
    "trainer",
    "history_count_before_race",
    "history_status",
)
RUNNER_COLUMN_ALIASES = {
    "frame_number": ("frame_number", "frame", "waku"),
    "popularity": ("popularity",),
    "win_odds": ("win_odds", "odds"),
    "horse_weight": ("horse_weight", "weight", "bataiju"),
    "weight_change": ("weight_change", "zogen"),
    "oikiri_time": ("oikiri_time",),
    "oikiri_rating": ("oikiri_rating",),
    "sire": ("sire",),
    "damsire": ("damsire",),
    "trainer": ("trainer",),
    "history_count_before_race": ("history_count_before_race",),
    "history_status": ("history_status",),
}
RACE_COLUMN_ALIASES = {
    "distance": ("distance",),
    "surface": ("surface",),
    "field_size": ("field_size", "horse_count"),
    "class_label": ("class_label", "race_name"),
    "track_condition": ("track_condition", "going"),
    "weather": ("weather",),
}


def canonical_json(payload: Any) -> str:
    """Key-sorted JSON. NaN / Infinity は禁止。追加の丸めはしない。"""
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_hex(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def stored_json_value(value: Any) -> Any:
    """保存 JSON と同じ dumps/loads 正規化。丸めは追加しない。"""
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    s = str(ts).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def anti_leak_ok(*, observed_at: str | None, prediction_created_at: str) -> bool:
    obs = parse_iso(observed_at)
    pred = parse_iso(prediction_created_at)
    if obs is None or pred is None:
        return False
    return obs <= pred


def accept_prediction_time_cell(
    *,
    value: Any,
    observed_at: str | None,
    prediction_created_at: str,
) -> dict[str, Any]:
    """観測時刻が予測時刻より後なら捨てる。ASOF clamp も 0 補完もしない。"""
    if value is None or value == "":
        return {
            "value": None,
            "observed_at": None,
            "missing_reason": "source_unavailable",
        }
    if not observed_at:
        return {
            "value": None,
            "observed_at": None,
            "missing_reason": "observed_at_unknown",
        }
    if not anti_leak_ok(observed_at=observed_at, prediction_created_at=prediction_created_at):
        return {
            "value": None,
            "observed_at": None,
            "missing_reason": "anti_leak_rejected",
        }
    return {
        "value": value,
        "observed_at": observed_at,
        "missing_reason": None,
    }


def persist_history_count(status: str, count: int | None) -> int | None:
    if status == "CONFIRMED_ZERO":
        return 0
    if status == "CONFIRMED_HISTORY":
        if count is None or int(count) <= 0:
            return None
        return int(count)
    return None


def explicit_confirmed_zero(obs: dict[str, Any]) -> bool:
    """count==0 だけでは CONFIRMED_ZERO にしない。明示的な complete-zero 証拠だけ。"""
    status = str(obs.get("history_status") or "").strip()
    if status == "CONFIRMED_ZERO":
        return True
    if obs.get("history_zero_confirmed") is True and obs.get("history_complete") is True:
        raw = obs.get("history_count_before_race")
        if isinstance(raw, dict):
            raw = raw.get("value")
        try:
            return int(raw) == 0
        except (TypeError, ValueError):
            return False
    return False


def resolve_history_status(obs: dict[str, Any]) -> str:
    status = str(obs.get("history_status") or "").strip()
    if status == "CONFIRMED_ZERO":
        return "CONFIRMED_ZERO" if explicit_confirmed_zero(obs) else "UNKNOWN"
    if status == "CONFIRMED_HISTORY":
        return "CONFIRMED_HISTORY"
    if status == "UNKNOWN":
        return "UNKNOWN"
    if explicit_confirmed_zero(obs):
        return "CONFIRMED_ZERO"
    return "UNKNOWN"


class NonFiniteFeatureValue(ValueError):
    """NaN / Infinity は None に畳まず拒否する。hash と推論入力を一致させる。"""


def _jsonable_scalar(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise NonFiniteFeatureValue("non_finite_feature_value")
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    if isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value
    return str(value)


def canonical_feature_load_object(
    feature_result: Any,
    *,
    race_id: str,
    core_race_id: str | None,
    race_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """実推論へ渡す FeatureLoadResult 全体の immutable 表現。"""
    if feature_result is None:
        raise ValueError("feature_result_required")
    frame = getattr(feature_result, "frame", None)
    records: list[dict[str, Any]] = []
    if frame is not None and hasattr(frame, "to_dict"):
        for rec in frame.to_dict(orient="records"):
            row = {str(k): _jsonable_scalar(v) for k, v in rec.items()}
            records.append(row)
        records.sort(
            key=lambda r: (
                int(r["horse_number"]) if str(r.get("horse_number") or "").isdigit() else 0,
                canonical_json(r),
            )
        )
    meta = getattr(feature_result, "metadata", None) or {}
    row_out = {}
    if isinstance(race_row, dict):
        row_out = {str(k): _jsonable_scalar(v) for k, v in race_row.items()}
    return {
        "race_id": str(race_id or ""),
        "core_race_id": str(core_race_id) if core_race_id else None,
        "feature_source": getattr(feature_result, "feature_source", None),
        "metadata": stored_json_value({str(k): _jsonable_scalar(v) for k, v in dict(meta).items()}),
        "frame": records,
        "race_row": stored_json_value(row_out),
    }


def source_observed_at(row: dict[str, Any] | None, *keys: str) -> str | None:
    """source の observed_at だけ。captured_at は使わない。"""
    if not row:
        return None
    for key in keys:
        raw = row.get(key)
        if raw in (None, ""):
            continue
        return str(raw)
    return None


def cell_is_filled(cell: dict[str, Any] | None) -> bool:
    if not cell:
        return False
    return cell.get("missing_reason") is None and cell.get("value") is not None


def empty_cell(reason: str = "source_unavailable") -> dict[str, Any]:
    return {"value": None, "observed_at": None, "missing_reason": reason}


def horse_number_key(value: Any) -> str | None:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    return str(n)


def runners_as_map(runners: Any) -> dict[str, dict[str, Any]]:
    if isinstance(runners, dict):
        out: dict[str, dict[str, Any]] = {}
        for raw_key, row in runners.items():
            key = horse_number_key(raw_key)
            if key is None or not isinstance(row, dict):
                continue
            out[key] = row
        return out
    if isinstance(runners, list):
        out = {}
        for row in runners:
            if not isinstance(row, dict):
                continue
            key = horse_number_key(row.get("horse_number"))
            if key is None or key in out:
                continue
            out[key] = row
        return out
    return {}


def _raw_value(raw: Any) -> Any:
    if isinstance(raw, dict) and "value" in raw:
        return raw.get("value")
    return raw


def _first_present(row: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return None


def canonical_inference_input_payload(
    *,
    race_obs: dict[str, Any] | None,
    runner_obs: list[dict[str, Any]] | dict[str, Any] | None,
) -> dict[str, Any]:
    """推論入力値のみ。時刻なし。runners は horse_number キー。"""
    race_obs = race_obs or {}
    race: dict[str, Any] = {}
    for key in RACE_SNAPSHOT_KEYS:
        race[key] = _raw_value(race_obs.get(key))
    runners_in = runners_as_map(runner_obs)
    runners: dict[str, dict[str, Any]] = {}
    for key in sorted(runners_in, key=lambda x: int(x)):
        row = runners_in[key]
        item: dict[str, Any] = {}
        for field in RUNNER_SNAPSHOT_KEYS:
            item[field] = _raw_value(row.get(field))
        runners[key] = item
    return {"race": race, "runners": runners}


def compute_input_snapshot_hash(payload: dict[str, Any]) -> str:
    return sha256_hex(payload)


def _history_cells(obs: dict[str, Any], created_at: str) -> tuple[dict[str, Any], dict[str, Any]]:
    status = resolve_history_status(obs)
    raw_count = obs.get("history_count_before_race")
    if isinstance(raw_count, dict):
        raw_count = raw_count.get("value")
    try:
        count_in = int(raw_count) if raw_count is not None and raw_count != "" else None
    except (TypeError, ValueError):
        count_in = None
    count = persist_history_count(status, count_in)
    status_cell = accept_prediction_time_cell(
        value=status,
        observed_at=obs.get("history_observed_at") or obs.get("observed_at"),
        prediction_created_at=created_at,
    )
    if status_cell["missing_reason"]:
        status_cell = {
            "value": "UNKNOWN",
            "observed_at": None,
            "missing_reason": status_cell["missing_reason"],
        }
        return status_cell, empty_cell(status_cell["missing_reason"])
    if status == "UNKNOWN":
        return status_cell, {
            "value": None,
            "observed_at": None,
            "missing_reason": "unknown_not_zero",
        }
    count_obs = obs.get("history_observed_at") or obs.get("observed_at")
    count_cell = accept_prediction_time_cell(
        value=count,
        observed_at=count_obs,
        prediction_created_at=created_at,
    )
    if status == "CONFIRMED_ZERO" and count == 0:
        count_cell = accept_prediction_time_cell(
            value=0,
            observed_at=count_obs,
            prediction_created_at=created_at,
        )
    return status_cell, count_cell


def snapshot_capture_status(race_cells: dict[str, dict], runner_cells: Any) -> str:
    runners = runners_as_map(runner_cells)
    if not runners:
        return "absent"
    needed = 0
    filled = 0
    for key in RACE_SNAPSHOT_KEYS:
        needed += 1
        if cell_is_filled(race_cells.get(key)):
            filled += 1
    for row in runners.values():
        for key in RUNNER_SNAPSHOT_KEYS:
            if key == "history_status":
                needed += 1
                st = (row.get("history_status") or {}).get("value")
                if st in ("CONFIRMED_HISTORY", "CONFIRMED_ZERO", "UNKNOWN"):
                    filled += 1
                continue
            if key == "history_count_before_race":
                needed += 1
                st = (row.get("history_status") or {}).get("value")
                count_cell = row.get("history_count_before_race") or {}
                if st == "UNKNOWN":
                    if count_cell.get("value") is None:
                        filled += 1
                elif st in ("CONFIRMED_HISTORY", "CONFIRMED_ZERO") and cell_is_filled(count_cell):
                    filled += 1
                continue
            needed += 1
            if cell_is_filled(row.get(key)):
                filled += 1
    if filled == 0:
        return "absent"
    if filled == needed:
        return "complete"
    return "partial"


def snapshot_training_coverage(race_cells: dict[str, dict], runner_cells: Any) -> str:
    """UNKNOWN / observed_at 不明は coverage に数えない。capture_status とは別。"""
    runners = runners_as_map(runner_cells)
    if not runners:
        return "absent"
    needed = 0
    covered = 0
    for key in RACE_SNAPSHOT_KEYS:
        needed += 1
        cell = race_cells.get(key) or {}
        if cell_is_filled(cell) and cell.get("observed_at"):
            covered += 1
    for row in runners.values():
        for key in RUNNER_SNAPSHOT_KEYS:
            needed += 1
            if key == "history_status":
                st = (row.get("history_status") or {}).get("value")
                cell = row.get("history_status") or {}
                if st in ("CONFIRMED_HISTORY", "CONFIRMED_ZERO") and cell_is_filled(cell) and cell.get("observed_at"):
                    covered += 1
                continue
            if key == "history_count_before_race":
                st = (row.get("history_status") or {}).get("value")
                count_cell = row.get("history_count_before_race") or {}
                if (
                    st in ("CONFIRMED_HISTORY", "CONFIRMED_ZERO")
                    and cell_is_filled(count_cell)
                    and count_cell.get("observed_at")
                ):
                    covered += 1
                continue
            cell = row.get(key) or {}
            if cell_is_filled(cell) and cell.get("observed_at"):
                covered += 1
    if covered == 0:
        return "absent"
    if covered == needed:
        return "complete"
    return "partial"


def build_prediction_time_features(
    *,
    prediction_created_at: str,
    race_obs: dict[str, Any] | None,
    runner_obs: list[dict[str, Any]] | dict[str, Any] | None,
    input_snapshot_hash: str | None = None,
) -> dict[str, Any]:
    race_obs = race_obs or {}
    runner_map = runners_as_map(runner_obs)
    input_hash = input_snapshot_hash or compute_input_snapshot_hash(
        canonical_inference_input_payload(race_obs=race_obs, runner_obs=runner_map)
    )
    race_cells: dict[str, dict[str, Any]] = {}
    race_observed = race_obs.get("observed_at")
    for key in RACE_SNAPSHOT_KEYS:
        raw = race_obs.get(key)
        if isinstance(raw, dict) and "value" in raw:
            cell_obs = raw.get("observed_at") or race_observed
            value = raw.get("value")
        else:
            value = raw
            cell_obs = race_obs.get("%s_observed_at" % key) or race_observed
        race_cells[key] = accept_prediction_time_cell(
            value=value,
            observed_at=cell_obs,
            prediction_created_at=prediction_created_at,
        )
    runners_out: dict[str, dict[str, Any]] = {}
    for key in sorted(runner_map, key=lambda x: int(x)):
        row = runner_map[key]
        observed = row.get("observed_at")
        item: dict[str, Any] = {}
        for field in RUNNER_SNAPSHOT_KEYS:
            if field in ("history_count_before_race", "history_status"):
                continue
            raw = row.get(field)
            if isinstance(raw, dict) and "value" in raw:
                value = raw.get("value")
                cell_obs = raw.get("observed_at") or observed
            else:
                value = raw
                cell_obs = row.get("%s_observed_at" % field) or observed
            item[field] = accept_prediction_time_cell(
                value=value,
                observed_at=cell_obs,
                prediction_created_at=prediction_created_at,
            )
        status_cell, count_cell = _history_cells(row, prediction_created_at)
        item["history_status"] = status_cell
        item["history_count_before_race"] = count_cell
        for forbidden in SNAPSHOT_FORBIDDEN_OUTPUT_KEYS:
            item.pop(forbidden, None)
        runners_out[key] = item
    for forbidden in SNAPSHOT_FORBIDDEN_OUTPUT_KEYS:
        race_cells.pop(forbidden, None)
    violations = 0
    for cell in race_cells.values():
        if cell.get("missing_reason") == "anti_leak_rejected":
            violations += 1
    for row in runners_out.values():
        for cell in row.values():
            if isinstance(cell, dict) and cell.get("missing_reason") == "anti_leak_rejected":
                violations += 1
    status = snapshot_capture_status(race_cells, runners_out)
    coverage = snapshot_training_coverage(race_cells, runners_out)
    return {
        "schema_version": SNAPSHOT_SCHEMA,
        "captured_at": prediction_created_at,
        "input_snapshot_hash": input_hash,
        "capture_status": status,
        "training_coverage": coverage,
        "anti_leak_violations": violations,
        "asof_clamped": False,
        "t2_used": False,
        "race": race_cells,
        "runners": runners_out,
    }


def absent_snapshot(
    prediction_created_at: str,
    reason: str,
    *,
    input_snapshot_hash: str | None = None,
) -> dict[str, Any]:
    empty_payload = canonical_inference_input_payload(race_obs={}, runner_obs={})
    return {
        "schema_version": SNAPSHOT_SCHEMA,
        "captured_at": prediction_created_at,
        "input_snapshot_hash": input_snapshot_hash or compute_input_snapshot_hash(empty_payload),
        "capture_status": "absent",
        "training_coverage": "absent",
        "anti_leak_violations": 0,
        "asof_clamped": False,
        "t2_used": False,
        "missing_reason": reason,
        "race": {k: empty_cell(reason) for k in RACE_SNAPSHOT_KEYS},
        "runners": {},
    }


def collect_prediction_time_features(
    *,
    captured_at: str,
    race_obs: dict[str, Any] | None = None,
    runner_obs: list[dict[str, Any]] | dict[str, Any] | None = None,
    collector_error: str | None = None,
    input_snapshot_hash: str | None = None,
) -> dict[str, Any]:
    if collector_error:
        return absent_snapshot(
            captured_at,
            "collector_fail_open:%s" % collector_error,
            input_snapshot_hash=input_snapshot_hash,
        )
    return build_prediction_time_features(
        prediction_created_at=captured_at,
        race_obs=race_obs,
        runner_obs=runner_obs,
        input_snapshot_hash=input_snapshot_hash,
    )


def attach_prediction_time_features_fail_open(
    bundle: dict[str, Any],
    *,
    prediction_created_at: str,
    race_obs: dict[str, Any] | None = None,
    runner_obs: list[dict[str, Any]] | dict[str, Any] | None = None,
    collector_error: str | None = None,
    input_snapshot_hash: str | None = None,
) -> dict[str, Any]:
    out = copy.deepcopy(bundle)
    out.pop("prediction_id", None)
    try:
        if collector_error:
            raise RuntimeError(collector_error)
        snap = collect_prediction_time_features(
            captured_at=prediction_created_at,
            race_obs=race_obs,
            runner_obs=runner_obs,
            input_snapshot_hash=input_snapshot_hash,
        )
        errors = validate_snapshot_only(snap)
        if errors:
            snap = absent_snapshot(
                prediction_created_at,
                "validator_fail_open:%s" % ",".join(errors),
                input_snapshot_hash=input_snapshot_hash,
            )
            warnings = list(out.get("warnings") or [])
            warnings.append("prediction_time_features_invalid")
            out["warnings"] = warnings
    except Exception as exc:
        snap = absent_snapshot(
            prediction_created_at,
            "collector_fail_open:%s" % type(exc).__name__,
            input_snapshot_hash=input_snapshot_hash,
        )
        warnings = list(out.get("warnings") or [])
        warnings.append("prediction_time_features_absent")
        out["warnings"] = warnings
    out["prediction_time_features"] = snap
    if "prediction_id" in out:
        raise RuntimeError("prediction_id_in_bundle_json_forbidden")
    return out


def _snapshot_has_forbidden_heads(snap: dict[str, Any]) -> bool:
    race = snap.get("race") or {}
    if any(k in race for k in SNAPSHOT_FORBIDDEN_OUTPUT_KEYS):
        return True
    runners = snap.get("runners")
    if isinstance(runners, dict):
        rows = runners.values()
    elif isinstance(runners, list):
        rows = runners
    else:
        rows = []
    for row in rows:
        if isinstance(row, dict) and any(k in row for k in SNAPSHOT_FORBIDDEN_OUTPUT_KEYS):
            return True
    return False


def validate_snapshot_only(snap: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(snap, dict):
        return ["snapshot_missing"]
    if snap.get("schema_version") != SNAPSHOT_SCHEMA:
        errors.append("snapshot_schema")
    if snap.get("capture_status") not in ("complete", "partial", "absent"):
        errors.append("capture_status")
    if snap.get("training_coverage") not in ("complete", "partial", "absent"):
        errors.append("training_coverage")
    if parse_iso(snap.get("captured_at")) is None:
        errors.append("captured_at")
    digest = str(snap.get("input_snapshot_hash") or "")
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        errors.append("input_snapshot_hash")
    if not isinstance(snap.get("race"), dict):
        errors.append("race_not_object")
    runners = snap.get("runners")
    if isinstance(runners, list):
        errors.append("runners_must_be_object_keyed_by_horse_number")
    elif not isinstance(runners, dict):
        errors.append("runners_not_object")
    else:
        for key, row in runners.items():
            if horse_number_key(key) != str(key):
                errors.append("runner_key_not_horse_number")
                break
            if not isinstance(row, dict):
                errors.append("runner_row_not_object")
                break
    if _snapshot_has_forbidden_heads(snap):
        errors.append("top2_top3_must_not_be_in_snapshot")
    captured = snap.get("captured_at")
    if captured:
        for cell in (snap.get("race") or {}).values():
            if not isinstance(cell, dict):
                continue
            obs = cell.get("observed_at")
            if obs and not anti_leak_ok(observed_at=obs, prediction_created_at=captured):
                errors.append("race_observed_after_captured_at")
                break
        for row in runners_as_map(runners).values():
            for cell in row.values():
                if not isinstance(cell, dict):
                    continue
                obs = cell.get("observed_at")
                if obs and not anti_leak_ok(observed_at=obs, prediction_created_at=captured):
                    errors.append("runner_observed_after_captured_at")
                    break
    return errors


def validate_prediction_time_features(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if bundle.get("schema_version") != BUNDLE_SCHEMA:
        errors.append("bundle_schema")
    snap = bundle.get("prediction_time_features")
    if not isinstance(snap, dict):
        errors.append("snapshot_missing")
        return errors
    errors.extend(validate_snapshot_only(snap))
    return errors


def _reject_duplicate_horse_numbers(runners: Any) -> None:
    seen: set[str] = set()
    rows: list[Any]
    if isinstance(runners, dict):
        rows = list(runners.values())
        for raw_key in runners:
            key = horse_number_key(raw_key)
            if key is None:
                continue
            if key in seen:
                raise ValueError("duplicate_horse_number")
            seen.add(key)
        return
    if isinstance(runners, list):
        rows = runners
    else:
        return
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = horse_number_key(row.get("horse_number"))
        if key is None:
            continue
        if key in seen:
            raise ValueError("duplicate_horse_number")
        seen.add(key)


def prediction_semantic_payload(bundle: dict[str, Any]) -> dict[str, Any]:
    """race_id + horse_number キーの win_prob / model_rank / mark。将来 head は存在時のみ。"""
    evaluation = bundle.get("evaluation") or {}
    _reject_duplicate_horse_numbers(evaluation.get("runners"))
    runners_in = runners_as_map(evaluation.get("runners"))
    runners: dict[str, dict[str, Any]] = {}
    for key in sorted(runners_in, key=lambda x: int(x)):
        row = runners_in[key]
        item: dict[str, Any] = {}
        for field in SEMANTIC_ALWAYS_KEYS:
            if field in row:
                item[field] = stored_json_value(row[field])
        for field in SEMANTIC_FUTURE_HEAD_KEYS:
            if field in row:
                item[field] = stored_json_value(row[field])
        runners[key] = item
    return {
        "race_id": stored_json_value(bundle.get("race_id")),
        "runners": runners,
    }


def compute_prediction_semantic_hash(bundle: dict[str, Any]) -> str:
    return sha256_hex(prediction_semantic_payload(bundle))


def observations_from_feature_frame(
    feature_result: Any,
    race_row: dict[str, Any] | None,
    captured_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """ピン済み FeatureLoadResult とローカル race 行から観測を作る。再取得しない。

    captured_at は観測時刻に使わない（ASOF 契約）。
    """
    _ = captured_at
    race_obs: dict[str, Any] = {}
    source_race = dict(race_row or {})
    frame = getattr(feature_result, "frame", None)
    first_row: dict[str, Any] = {}
    if frame is not None and hasattr(frame, "empty") and not frame.empty:
        first_row = {str(k): v for k, v in frame.iloc[0].to_dict().items()}
        source_race = {**first_row, **source_race}
    race_src_obs = source_observed_at(source_race, "observed_at", "race_observed_at")
    if race_src_obs:
        race_obs["observed_at"] = race_src_obs
    for key, aliases in RACE_COLUMN_ALIASES.items():
        raw = _first_present(source_race, aliases)
        if raw is not None and hasattr(raw, "item"):
            try:
                raw = raw.item()
            except Exception:
                pass
        race_obs[key] = raw
        field_obs = source_observed_at(source_race, "%s_observed_at" % key)
        if field_obs:
            race_obs["%s_observed_at" % key] = field_obs
    if race_obs.get("field_size") is None and frame is not None and hasattr(frame, "__len__"):
        try:
            n = int(len(frame))
            if n > 0:
                race_obs["field_size"] = n
        except Exception:
            pass

    runners: dict[str, dict[str, Any]] = {}
    if frame is None or getattr(frame, "empty", True):
        return race_obs, runners
    for rec in frame.to_dict(orient="records"):
        row = {str(k): v for k, v in rec.items()}
        key = horse_number_key(row.get("horse_number"))
        if key is None:
            continue
        item: dict[str, Any] = {"horse_number": int(key)}
        src_obs = source_observed_at(row, "observed_at", "runner_observed_at")
        if src_obs:
            item["observed_at"] = src_obs
        for field, aliases in RUNNER_COLUMN_ALIASES.items():
            raw = _first_present(row, aliases)
            if raw is not None and hasattr(raw, "item"):
                try:
                    raw = raw.item()
                except Exception:
                    pass
            item[field] = raw
            field_obs = source_observed_at(row, "%s_observed_at" % field)
            if field_obs:
                item["%s_observed_at" % field] = field_obs
        for flag in ("history_zero_confirmed", "history_complete"):
            if flag in row:
                item[flag] = row[flag]
        item["history_status"] = resolve_history_status(item)
        runners[key] = item
    return race_obs, runners
