# -*- coding: utf-8 -*-
"""RAEVAL84_V1 84 race_id holdout. train/val に入れない。"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

EXPECTED_COUNT = 84
EXPECTED_RACE_ID_LIST_SHA256 = "6f586357d69e554c559fb43bd3520a2d04849787328b40dc12bdbb2f67a94dd3"
SOURCE_TRIPLE_SHA256 = "3ffb188d2e1a64c56134dd311e3de8f31e920107736e4bcfb07cad029db3081d"
DEFAULT_HOLDOUT_PATH = Path(__file__).resolve().parent / "data" / "raeval84_v1_holdout_race_ids.txt"

CHRONOLOGY_POLICY = "prediction-unit"
HOLDOUT_POLICY = "race_id"


class HoldoutContractError(RuntimeError):
    """holdout 成果物が読めない / SHA不一致 / 件数不正。学習を止める。"""


def canonical_race_id_payload(race_ids: list[str]) -> bytes:
    return ("\n".join(race_ids) + ("\n" if race_ids else "")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_raeval84_holdout(
    path: Path | str | None = None,
    *,
    expected_sha: str | None = None,
    expected_count: int = EXPECTED_COUNT,
) -> frozenset[str]:
    """固定 84 race_id。SHA / 件数 / 重複 / 読込不能は fail-closed。"""
    target = Path(path) if path is not None else DEFAULT_HOLDOUT_PATH
    want_sha = str(expected_sha or EXPECTED_RACE_ID_LIST_SHA256)
    try:
        raw = target.read_bytes()
    except OSError as exc:
        raise HoldoutContractError("raeval84_holdout_unreadable:%s" % target) from exc
    digest = sha256_hex(raw)
    if digest != want_sha:
        raise HoldoutContractError("raeval84_holdout_sha_mismatch")
    lines = [ln.strip() for ln in raw.decode("utf-8").splitlines() if ln.strip()]
    if len(lines) != expected_count:
        raise HoldoutContractError("raeval84_holdout_count_%s" % len(lines))
    if len(set(lines)) != len(lines):
        raise HoldoutContractError("raeval84_holdout_duplicate_race_id")
    if lines != sorted(lines):
        raise HoldoutContractError("raeval84_holdout_not_sorted")
    if canonical_race_id_payload(lines) != raw:
        raise HoldoutContractError("raeval84_holdout_canonical_mismatch")
    return frozenset(lines)


def holdout_metrics(race_split: dict[str, str], holdout: frozenset[str] | None = None) -> dict[str, Any]:
    races = holdout if holdout is not None else load_raeval84_holdout()
    in_train_or_val = [
        rid
        for rid, split in race_split.items()
        if rid in races and split in ("train", "val")
    ]
    count = len(in_train_or_val)
    return {
        "RAEVAL84_IN_TRAIN_OR_VAL": count,
        "RAEVAL84_IN_TRAIN_OR_VAL_COUNT": count,
        "RAEVAL84_HOLDOUT_RACE_COUNT": len(races),
        "RAEVAL84_HOLDOUT_SHA256": EXPECTED_RACE_ID_LIST_SHA256,
        "RAEVAL84_SOURCE_TRIPLE_SHA256": SOURCE_TRIPLE_SHA256,
        "CHRONOLOGY_POLICY": CHRONOLOGY_POLICY,
        "RAEVAL84_HOLDOUT_POLICY": HOLDOUT_POLICY,
    }


def assert_raeval84_not_in_train_or_val(race_split: dict[str, str], holdout: frozenset[str] | None = None) -> int:
    metrics = holdout_metrics(race_split, holdout)
    if int(metrics["RAEVAL84_IN_TRAIN_OR_VAL_COUNT"]) != 0:
        raise HoldoutContractError(
            "RAEVAL84_IN_TRAIN_OR_VAL_COUNT=%s" % metrics["RAEVAL84_IN_TRAIN_OR_VAL_COUNT"]
        )
    return 0
