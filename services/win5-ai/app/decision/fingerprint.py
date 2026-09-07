# -*- coding: utf-8 -*-
"""Prediction fingerprint helpers — Decision must not change these."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def _canon(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rank_fingerprint(horses: list[dict[str, Any]]) -> str:
    rows = sorted(
        [{"horse_id": str(h.get("horse_id") or ""), "model_rank": int(h.get("model_rank") or 999)} for h in horses],
        key=lambda r: (r["model_rank"], r["horse_id"]),
    )
    return sha256_hex(_canon(rows))


def score_fingerprint(horses: list[dict[str, Any]]) -> str:
    rows = sorted(
        [
            {
                "horse_id": str(h.get("horse_id") or ""),
                "win_prob": round(float(h.get("win_prob") or 0.0), 12),
            }
            for h in horses
        ],
        key=lambda r: r["horse_id"],
    )
    return sha256_hex(_canon(rows))


def prediction_fingerprint(race_id: str, predicted_top1: str, horses: list[dict[str, Any]]) -> str:
    payload = {
        "race_id": race_id,
        "predicted_top1": predicted_top1,
        "rank_fp": rank_fingerprint(horses),
        "score_fp": score_fingerprint(horses),
    }
    return sha256_hex(_canon(payload))
