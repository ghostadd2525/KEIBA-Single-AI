# -*- coding: utf-8 -*-
"""AI Core scoring — PC-3: ModelRegistry + field-size temperature softmax."""
from __future__ import annotations

import os
from typing import Any

import numpy as np
import pandas as pd

from demo_probability_adjustment_logic import apply_grade_distance_style_adjustment
from demo_probability_context_logic import attach_probability_context_columns
from demo_probability_model_logic import (
    build_base_probability_scores,
    build_probability_from_adjusted_score,
    ensure_non_tied_scores,
    model_predict_score,
    race_softmax,
)

from ai_platform.core.scoring.model_registry import get_ranking_model


def _field_size_temperature(field_size: int) -> float:
    """
    PC-3: soften softmax for large fields (reduces probability flattening).
    Override via CORE_SOFTMAX_TEMP_BASE (default 1.0) and CORE_SOFTMAX_TEMP_SLOPE (0.04).
    CE-V2 Facet A: when WIN5_CE_V2_ENABLED, use fixed CE_V2_A_TEMP (see v2_ce_v2).
    """
    try:
        from v2_ce_v2 import WIN5_CE_V2_ENABLED, CE_V2_A_TEMP

        if WIN5_CE_V2_ENABLED:
            return float(CE_V2_A_TEMP)
    except Exception:
        pass
    base = float(os.environ.get("CORE_SOFTMAX_TEMP_BASE") or "1.0")
    slope = float(os.environ.get("CORE_SOFTMAX_TEMP_SLOPE") or "0.04")
    threshold = int(float(os.environ.get("CORE_SOFTMAX_FIELD_THRESHOLD") or "12"))
    if field_size <= threshold:
        return base
    return base + (field_size - threshold) * slope


def _temperature_softmax(
    adjusted_score: pd.Series,
    race_ids: pd.Series,
    field_size: int,
) -> pd.Series:
    temp = _field_size_temperature(field_size)
    if temp <= 1.0 + 1e-9:
        return race_softmax(adjusted_score, race_ids)
    scaled = adjusted_score.astype(float) / temp
    return race_softmax(scaled, race_ids)


class Scorer:
    """Produce base, adjusted and race-softmax scores with PC-3 enhancements."""

    def score_candidates(
        self,
        feature_matrix: dict[str, Any],
        model: Any = None,
        adjustment_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        frame = feature_matrix["_source_frame"].copy()
        matrix = feature_matrix["X"]
        field_size = int(len(frame))

        registry_model, registry_source = get_ranking_model()
        active_model = model if model is not None else registry_model

        if active_model is None:
            info = build_base_probability_scores(frame, verbose=False)
            base_score = pd.to_numeric(info["base_score"], errors="coerce").fillna(0.0)
            predict_mode = str(info.get("predict_mode", ""))
            model_source = str(info.get("model_source", ""))
        else:
            base_score, predict_mode = model_predict_score(active_model, matrix)
            model_source = registry_source or type(active_model).__name__

        context_frame = attach_probability_context_columns(frame, overwrite=False)
        adjusted_score, diagnostic = apply_grade_distance_style_adjustment(
            context_frame, base_score
        )
        base_score, adjusted_score, predict_mode, tie_detail = ensure_non_tied_scores(
            context_frame,
            base_score,
            adjusted_score,
            predict_mode,
        )

        win_prob = _temperature_softmax(
            adjusted_score,
            context_frame["race_id"],
            field_size,
        )
        _, model_rank = build_probability_from_adjusted_score(
            context_frame, adjusted_score
        )

        return {
            "race_id": feature_matrix.get("race_id", ""),
            "candidate_ids": list(feature_matrix.get("candidate_ids", [])),
            "base_model_score": base_score,
            "adjusted_model_score": adjusted_score,
            "win_prob": win_prob,
            "_source_frame": context_frame,
            "_predict_mode": predict_mode,
            "_model_source": model_source,
            "_diagnostic": diagnostic,
            "_tie_detail": tie_detail,
            "_field_size_temperature": _field_size_temperature(field_size),
        }


__all__ = ["Scorer", "get_ranking_model"]
