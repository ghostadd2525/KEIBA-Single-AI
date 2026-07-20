"""Mock / sample data loaders — Repository 優先、JSON フォールバック。"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]  # KEIBA-Single-AI/
MOCK_DIR = ROOT / "public" / "data" / "mocks"


def _use_db_catalog() -> bool:
    return (os.environ.get("EXPECT_AI_USE_DB_CATALOG") or "1").lower() in (
        "1",
        "true",
        "yes",
    )


@lru_cache(maxsize=1)
def load_races() -> dict[str, Any]:
    if _use_db_catalog():
        try:
            from ..data.repository import RaceRepository

            catalog = RaceRepository().as_catalog()
            if catalog.get("races"):
                return catalog
        except Exception:
            pass
    path = MOCK_DIR / "races.json"
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_home() -> dict[str, Any]:
    path = MOCK_DIR / "home.json"
    if not path.exists():
        return {"ok": True, "items": []}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_analysis_all() -> dict[str, Any]:
    path = MOCK_DIR / "analysis.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_bundle(race_id: str) -> dict[str, Any] | None:
    specific = MOCK_DIR / f"bundle-{race_id}.json"
    if specific.exists():
        return json.loads(specific.read_text(encoding="utf-8"))
    fallback = MOCK_DIR / "bundle-20260719_hanshin_11.json"
    if not fallback.exists():
        return None
    data = json.loads(fallback.read_text(encoding="utf-8"))
    data = dict(data)
    data["race_id"] = race_id
    if isinstance(data.get("race_info"), dict):
        info = dict(data["race_info"])
        info["race_id"] = race_id
        data["race_info"] = info
    return data


def clear_caches() -> None:
    load_races.cache_clear()
    load_home.cache_clear()
    load_analysis_all.cache_clear()


def build_view(bundle: dict[str, Any], race_id: str) -> dict[str, Any]:
    info = bundle.get("race_info") or {}
    runners = ((bundle.get("evaluation") or {}).get("runners")) or []
    honmei = next((r for r in runners if r.get("mark") == "honmei"), runners[0] if runners else None)
    conf = 80
    if honmei and honmei.get("win_prob") is not None:
        conf = int(round(float(honmei["win_prob"]) * 100))
    races = load_races().get("races") or []
    meta = next((r for r in races if r.get("race_id") == race_id), None)
    if meta:
        return {
            "title": f"{meta['venue']} {meta['race_no']}R",
            "post_time": meta.get("post_time") or "",
            "class_label": meta.get("class_label") or "",
            "ai_confidence": meta.get("ai_confidence") or conf,
            "honmei": {
                "horse_number": honmei.get("horse_number") if honmei else None,
                "horse_name": honmei.get("horse_name") if honmei else None,
                "win_prob": honmei.get("win_prob") if honmei else None,
            },
        }
    return {
        "title": f"{info.get('venue', '')} {info.get('race_no', '')}R".strip() or race_id,
        "post_time": info.get("post_time") or "",
        "class_label": info.get("class_label") or "",
        "ai_confidence": conf,
        "honmei": honmei,
    }
