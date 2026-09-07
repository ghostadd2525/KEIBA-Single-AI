# -*- coding: utf-8 -*-
"""Presentation Mapper — Core Semantic → Presentation DTO (V109 C2).

Read-only. Does not change Policy, Ticket, Prediction, or Semantic meaning.
"""
from __future__ import annotations

from typing import Any, Mapping

from app.consumer.presentation.dto import (
    AffinityDisplay,
    ExclusionDisplay,
    ExplanationConfidenceDisplay,
    NearMissDisplay,
    PresentationBundle,
    TransitionDisplay,
    WorldDisplay,
)
from app.consumer.presentation.localization import (
    normalize_locale,
    residual_label_key,
    t,
    world_label_key,
)


def _f(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def map_world(core: Mapping[str, Any], locale: str) -> WorldDisplay:
    wid = core.get("world_id")
    wid_s = str(wid) if wid is not None else None
    key = world_label_key(wid_s)
    return WorldDisplay(world_id=wid_s, label=t(key, locale), label_key=key)


def map_near_miss(core: Mapping[str, Any], locale: str) -> NearMissDisplay:
    nm = core.get("near_miss")
    if not isinstance(nm, Mapping):
        return NearMissDisplay(
            present=False,
            residual_class=None,
            residual_label=None,
            near_world=None,
            near_world_label=None,
        )
    residual = nm.get("residual_class")
    residual_s = str(residual) if residual is not None else None
    near = nm.get("near_world")
    near_s = str(near) if near is not None else None
    near_worlds_raw = nm.get("near_worlds") or []
    near_worlds = tuple(str(x) for x in near_worlds_raw) if isinstance(near_worlds_raw, (list, tuple)) else ()
    rkey = residual_label_key(residual_s)
    nkey = world_label_key(near_s) if near_s else None
    return NearMissDisplay(
        present=True,
        residual_class=residual_s,
        residual_label=t(rkey, locale),
        near_world=near_s,
        near_world_label=t(nkey, locale) if nkey else None,
        near_worlds=near_worlds,
    )


def map_affinity(core: Mapping[str, Any], locale: str) -> AffinityDisplay:
    aff = core.get("affinity")
    if not isinstance(aff, Mapping):
        return AffinityDisplay(present=False)
    values: list[tuple[str, float]] = []
    definition = aff.get("definition")
    for k, v in aff.items():
        if k == "definition":
            continue
        fv = _f(v)
        if fv is None:
            continue
        values.append((str(k), fv))
    values.sort(key=lambda x: (-x[1], x[0]))
    return AffinityDisplay(
        present=True,
        values=tuple(values),
        definition=str(definition) if definition is not None else None,
        note_key="affinity_display_only",
    )


def map_explanation_confidence(core: Mapping[str, Any], locale: str) -> ExplanationConfidenceDisplay:
    ec = core.get("explanation_confidence")
    if not isinstance(ec, Mapping):
        return ExplanationConfidenceDisplay(present=False)
    return ExplanationConfidenceDisplay(
        present=True,
        semantic_confidence=_f(ec.get("semantic_confidence")),
        world_confidence=_f(ec.get("world_confidence")),
        near_miss_confidence=_f(ec.get("near_miss_confidence")),
        trace_confidence=_f(ec.get("trace_confidence")),
        explanation_confidence=_f(ec.get("explanation_confidence")),
        definition_version=str(ec.get("definition_version")) if ec.get("definition_version") is not None else None,
        not_win_probability=True,
        display_kind="explanation_confidence",
    )


def map_exclusion(core: Mapping[str, Any], locale: str) -> ExclusionDisplay:
    ex = core.get("exclusion_reasons")
    if not isinstance(ex, Mapping) or not ex:
        return ExclusionDisplay(present=False)
    items: list[tuple[str, tuple[str, ...]]] = []
    for world, reasons in ex.items():
        if isinstance(reasons, (list, tuple)):
            rs = tuple(str(r) for r in reasons)
        elif reasons is None:
            rs = ()
        else:
            rs = (str(reasons),)
        items.append((str(world), rs))
    items.sort(key=lambda x: x[0])
    return ExclusionDisplay(present=True, by_world=tuple(items))


def map_transition(core: Mapping[str, Any], locale: str) -> TransitionDisplay:
    tr = core.get("transition")
    tp = core.get("trigger_path")
    present = tr is not None or tp is not None
    return TransitionDisplay(
        present=present,
        transition=str(tr) if tr is not None else None,
        trigger_path=str(tp) if tp is not None else None,
    )


def map_presentation(
    core: Mapping[str, Any],
    *,
    locale: str | None = None,
) -> PresentationBundle:
    """Map Core → PresentationBundle. Does not mutate ``core``."""
    loc = normalize_locale(locale)
    warnings: list[str] = []
    if core.get("prediction") is not None:
        # Prediction may exist on Core but is intentionally excluded from Presentation DTO
        warnings.append("prediction_excluded_from_presentation")

    return PresentationBundle(
        locale=loc,
        world=map_world(core, loc),
        near_miss=map_near_miss(core, loc),
        affinity=map_affinity(core, loc),
        explanation_confidence=map_explanation_confidence(core, loc),
        exclusion=map_exclusion(core, loc),
        transition=map_transition(core, loc),
        natural_explanation=None,
        warnings=tuple(warnings),
    )
