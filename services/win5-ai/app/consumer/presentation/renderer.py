# -*- coding: utf-8 -*-
"""Presentation Renderer — ordered display sections (V109 C2).

No Natural Explanation generation.
"""
from __future__ import annotations

from typing import Any, Mapping

from app.consumer.presentation.dto import (
    DISPLAY_ORDER,
    LabeledValue,
    PresentationBundle,
)
from app.consumer.presentation.localization import t
from app.consumer.presentation.mapper import map_presentation


def render_sections(bundle: PresentationBundle) -> tuple[LabeledValue, ...]:
    """Build ordered LabeledValue sections for UI."""
    loc = bundle.locale
    sections: list[LabeledValue] = []

    for name in bundle.display_order or DISPLAY_ORDER:
        if name == "world" and bundle.world is not None:
            sections.append(
                LabeledValue(
                    key="world",
                    label=t("section.world", loc),
                    value={
                        "world_id": bundle.world.world_id,
                        "label": bundle.world.label,
                    },
                    kind="map",
                )
            )
        elif name == "near_miss" and bundle.near_miss is not None:
            nm = bundle.near_miss
            sections.append(
                LabeledValue(
                    key="near_miss",
                    label=t("section.near_miss", loc),
                    value=None
                    if not nm.present
                    else {
                        "residual_class": nm.residual_class,
                        "residual_label": nm.residual_label,
                        "near_world": nm.near_world,
                        "near_world_label": nm.near_world_label,
                        "near_worlds": list(nm.near_worlds),
                    },
                    kind="map" if nm.present else "null",
                )
            )
        elif name == "affinity" and bundle.affinity is not None:
            aff = bundle.affinity
            sections.append(
                LabeledValue(
                    key="affinity",
                    label=t("section.affinity", loc),
                    value=None
                    if not aff.present
                    else {
                        "values": [{"world_id": w, "score": s} for w, s in aff.values],
                        "definition": aff.definition,
                        "note": t(aff.note_key, loc),
                    },
                    kind="map" if aff.present else "null",
                )
            )
        elif name == "explanation_confidence" and bundle.explanation_confidence is not None:
            ec = bundle.explanation_confidence
            sections.append(
                LabeledValue(
                    key="explanation_confidence",
                    label=t("section.explanation_confidence", loc),
                    value=None
                    if not ec.present
                    else {
                        "semantic_confidence": ec.semantic_confidence,
                        "world_confidence": ec.world_confidence,
                        "near_miss_confidence": ec.near_miss_confidence,
                        "trace_confidence": ec.trace_confidence,
                        "explanation_confidence": ec.explanation_confidence,
                        "definition_version": ec.definition_version,
                        "display_kind": ec.display_kind,
                        "not_win_probability": True,
                        "disclaimer": t("ec.not_win_probability", loc),
                        "axis_labels": {
                            "semantic": t("ec.axis.semantic", loc),
                            "world": t("ec.axis.world", loc),
                            "near_miss": t("ec.axis.near_miss", loc),
                            "trace": t("ec.axis.trace", loc),
                            "bundle": t("ec.axis.bundle", loc),
                        },
                    },
                    kind="map" if ec.present else "null",
                )
            )
        elif name == "exclusion" and bundle.exclusion is not None:
            ex = bundle.exclusion
            sections.append(
                LabeledValue(
                    key="exclusion",
                    label=t("section.exclusion", loc),
                    value=None
                    if not ex.present
                    else {
                        "by_world": [
                            {"world_id": w, "reasons": list(rs)} for w, rs in ex.by_world
                        ]
                    },
                    kind="map" if ex.present else "null",
                )
            )
        elif name == "transition" and bundle.transition is not None:
            tr = bundle.transition
            sections.append(
                LabeledValue(
                    key="transition",
                    label=t("section.transition", loc),
                    value=None
                    if not tr.present
                    else {
                        "transition": tr.transition,
                        "trigger_path": tr.trigger_path,
                    },
                    kind="map" if tr.present else "null",
                )
            )
    return tuple(sections)


def render_presentation(
    core: Mapping[str, Any],
    *,
    locale: str | None = None,
) -> PresentationBundle:
    """Map + attach ordered sections. No NL generation."""
    bundle = map_presentation(core, locale=locale)
    sections = render_sections(bundle)
    return PresentationBundle(
        schema=bundle.schema,
        locale=bundle.locale,
        display_order=bundle.display_order,
        world=bundle.world,
        near_miss=bundle.near_miss,
        affinity=bundle.affinity,
        explanation_confidence=bundle.explanation_confidence,
        exclusion=bundle.exclusion,
        transition=bundle.transition,
        natural_explanation=None,
        sections=sections,
        warnings=bundle.warnings,
    )
