# -*- coding: utf-8 -*-
"""Localization Contract for Presentation (V109 C2).

Structured labels only — not Natural Explanation paragraphs.
"""
from __future__ import annotations

from typing import Mapping

LOCALIZATION_CONTRACT_VERSION = "presentation-i18n/v1"
SUPPORTED_LOCALES: tuple[str, ...] = ("ja", "en")
DEFAULT_LOCALE = "ja"

# label_key → {locale: display string}
# MUST: short labels for UI. MUST NOT: multi-sentence "why" prose.
_CATALOG: dict[str, dict[str, str]] = {
    "section.world": {"ja": "ワールド", "en": "World"},
    "section.near_miss": {"ja": "ニアミス", "en": "Near Miss"},
    "section.affinity": {"ja": "親和度", "en": "Affinity"},
    "section.explanation_confidence": {
        "ja": "説明確信度",
        "en": "Explanation Confidence",
    },
    "section.exclusion": {"ja": "除外理由", "en": "Exclusion Reasons"},
    "section.transition": {"ja": "遷移", "en": "Transition"},
    "world.rank7_world": {"ja": "混戦（rank7）", "en": "Chaos (rank7)"},
    "world.midhole_world": {"ja": "中穴（midhole）", "en": "Mid-hole"},
    "world.unsatisfied": {"ja": "未充足（残余）", "en": "Unsatisfied residual"},
    "world.core_world": {"ja": "能力決着（core・暫定）", "en": "Core (provisional)"},
    "world.midupper_world": {"ja": "上位帯（midupper）", "en": "Mid-upper"},
    "world.mixed_world": {"ja": "複合（mixed）", "en": "Mixed"},
    "world.bug_world": {"ja": "例外（bug）", "en": "Bug"},
    "world.unknown": {"ja": "不明ワールド", "en": "Unknown world"},
    "residual.NEAR_MISS": {"ja": "ニアミス", "en": "Near Miss"},
    "residual.PURE_RESIDUAL": {"ja": "純残余", "en": "Pure Residual"},
    "residual.unknown": {"ja": "残余区分なし", "en": "Residual unspecified"},
    "affinity_display_only": {
        "ja": "表示専用（券種・見送り判定に使わない）",
        "en": "Display only (not for ticket/skip)",
    },
    "ec.not_win_probability": {
        "ja": "勝率ではない（説明の確定度）",
        "en": "Not win probability (explanation completeness)",
    },
    "ec.axis.semantic": {"ja": "意味", "en": "Semantic"},
    "ec.axis.world": {"ja": "ワールド", "en": "World"},
    "ec.axis.near_miss": {"ja": "ニアミス", "en": "Near Miss"},
    "ec.axis.trace": {"ja": "トレース", "en": "Trace"},
    "ec.axis.bundle": {"ja": "総合", "en": "Bundle"},
    "null.value": {"ja": "なし", "en": "None"},
}


def normalize_locale(locale: str | None) -> str:
    if not locale:
        return DEFAULT_LOCALE
    loc = str(locale).strip().lower()
    if loc.startswith("en"):
        return "en"
    if loc.startswith("ja"):
        return "ja"
    return DEFAULT_LOCALE


def t(label_key: str, locale: str | None = None) -> str:
    loc = normalize_locale(locale)
    entry = _CATALOG.get(label_key)
    if not entry:
        return label_key
    return entry.get(loc) or entry.get(DEFAULT_LOCALE) or label_key


def world_label_key(world_id: str | None) -> str:
    if not world_id:
        return "world.unknown"
    key = f"world.{world_id}"
    return key if key in _CATALOG else "world.unknown"


def residual_label_key(residual_class: str | None) -> str:
    if not residual_class:
        return "residual.unknown"
    key = f"residual.{residual_class}"
    return key if key in _CATALOG else "residual.unknown"


def localization_contract() -> Mapping[str, object]:
    """Public Localization Contract document (machine-readable)."""
    return {
        "schema": LOCALIZATION_CONTRACT_VERSION,
        "supported_locales": list(SUPPORTED_LOCALES),
        "default_locale": DEFAULT_LOCALE,
        "natural_explanation": "forbidden_in_c2",
        "catalog_keys": sorted(_CATALOG.keys()),
        "rules": [
            "Labels are short UI strings only",
            "No multi-sentence Natural Explanation in this catalog",
            "EC labels must not imply win probability",
            "Affinity note is display-only",
        ],
    }
