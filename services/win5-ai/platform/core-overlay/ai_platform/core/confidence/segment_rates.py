# -*- coding: utf-8 -*-
"""会場×芝ダ×距離の◎的中率ルックアップ（285R コーパス）。"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

MODEL_WEIGHT = 0.6
SEGMENT_WEIGHT = 0.4
MIN_SEGMENT_SAMPLES = 3
DISTANCE_BUCKETS = (1200, 1600, 2000, 2400)

_DEFAULT_TABLE: dict[str, Any] = {
    "overall_hit_rate": 218 / 285,
    "min_samples": MIN_SEGMENT_SAMPLES,
    "segments": {},
}


def _repo_rates_path() -> Path | None:
    root = os.environ.get("EXPECT_REPO_ROOT", "").strip()
    if root:
        candidate = Path(root) / "fixtures" / "stats" / "segment-hit-rates.json"
        if candidate.is_file():
            return candidate
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "fixtures" / "stats" / "segment-hit-rates.json"
        if candidate.is_file():
            return candidate
    env_path = os.environ.get("SEGMENT_HIT_RATES_PATH", "").strip()
    if env_path and Path(env_path).is_file():
        return Path(env_path)
    return None


def load_segment_hit_rates() -> dict[str, Any]:
    path = _repo_rates_path()
    if path is None:
        return dict(_DEFAULT_TABLE)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return dict(_DEFAULT_TABLE)


def surface_ja(surface: Any) -> str:
    s = str(surface or "").lower()
    if "turf" in s or s == "芝":
        return "芝"
    if "dirt" in s or s in {"ダ", "ダート"}:
        return "ダ"
    return "芝"


def distance_bucket(distance: Any) -> int:
    try:
        d = int(distance)
    except (TypeError, ValueError):
        return 1600
    if d <= 0:
        return 1600
    best = DISTANCE_BUCKETS[0]
    diff = abs(d - best)
    for bucket in DISTANCE_BUCKETS[1:]:
        nd = abs(d - bucket)
        if nd < diff:
            diff = nd
            best = bucket
    return best


def segment_key(venue: str, surface: str, bucket: int) -> str:
    return f"{venue.strip()}|{surface}|{bucket}"


def lookup_segment_hit_rate(meta: dict[str, Any] | None, table: dict[str, Any] | None = None) -> dict[str, Any]:
    data = table or load_segment_hit_rates()
    overall = float(data.get("overall_hit_rate") or _DEFAULT_TABLE["overall_hit_rate"])
    min_n = int(data.get("min_samples") or MIN_SEGMENT_SAMPLES)
    segments = data.get("segments") or {}
    ctx = meta or {}
    venue = str(ctx.get("venue") or ctx.get("course") or "").strip()
    surf = surface_ja(ctx.get("surface") or ctx.get("target_surface"))
    bucket = distance_bucket(ctx.get("distance") or ctx.get("target_distance"))

    if not venue:
        return {"hit_rate": overall, "key": None, "n": 0, "scope": "overall"}

    full_key = segment_key(venue, surf, bucket)
    full = segments.get(full_key)
    if isinstance(full, dict) and int(full.get("n") or 0) >= min_n:
        return {
            "hit_rate": float(full["hit_rate"]),
            "key": full_key,
            "n": int(full["n"]),
            "scope": "venue_surface_distance",
        }

    prefix = f"{venue}|{surf}|"
    venue_surf_sum = 0.0
    venue_surf_n = 0
    for key, row in segments.items():
        if not str(key).startswith(prefix):
            continue
        n = int((row or {}).get("n") or 0)
        if n <= 0:
            continue
        venue_surf_sum += float((row or {}).get("hit_rate") or 0) * n
        venue_surf_n += n
    if venue_surf_n >= min_n:
        return {
            "hit_rate": venue_surf_sum / venue_surf_n,
            "key": f"{venue}|{surf}|*",
            "n": venue_surf_n,
            "scope": "venue_surface",
        }

    venue_sum = 0.0
    venue_n = 0
    venue_prefix = f"{venue}|"
    for key, row in segments.items():
        if not str(key).startswith(venue_prefix):
            continue
        n = int((row or {}).get("n") or 0)
        if n <= 0:
            continue
        venue_sum += float((row or {}).get("hit_rate") or 0) * n
        venue_n += n
    if venue_n >= min_n:
        return {
            "hit_rate": venue_sum / venue_n,
            "key": f"{venue}|*",
            "n": venue_n,
            "scope": "venue",
        }

    return {"hit_rate": overall, "key": None, "n": 0, "scope": "overall"}


def blend_confidence_score(model_score: float | None, segment_hit_rate: float) -> float | None:
    if model_score is None:
        return None
    model = float(model_score)
    if model > 1:
        model /= 100.0
    segment = float(segment_hit_rate)
    blended = MODEL_WEIGHT * model + SEGMENT_WEIGHT * segment
    return min(max(blended, 0.0), 1.0)


__all__ = [
    "MODEL_WEIGHT",
    "SEGMENT_WEIGHT",
    "blend_confidence_score",
    "distance_bucket",
    "load_segment_hit_rates",
    "lookup_segment_hit_rate",
    "segment_key",
    "surface_ja",
]
