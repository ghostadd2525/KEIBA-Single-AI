# -*- coding: utf-8 -*-
"""AI Core feature generation migrated from the existing probability path.

This module is a boundary adapter only.  It delegates to the functions used by
``demo_win5_probability_calculator.py`` and does not introduce feature logic.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from demo_probability_feature_utils import (
    enrich_stable_features,
    ensure_style_count_features,
)
from demo_probability_model_logic import (
    FEATURES_JSON_PATH,
    load_feature_meta,
    prepare_feature_matrix,
)


class FeatureGenerator:
    """Build the frozen model feature matrix without changing its values."""

    def build_feature_matrix(
        self,
        runners: list[dict[str, Any]] | pd.DataFrame,
        feature_schema: dict[str, Any] | None = None,
        race_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return the existing 28-column matrix and its source-frame context."""
        frame = runners.copy() if isinstance(runners, pd.DataFrame) else pd.DataFrame(runners)
        if race_context:
            for key, value in race_context.items():
                if key not in frame.columns:
                    frame[key] = value

        frame = enrich_stable_features(frame)
        frame = ensure_style_count_features(frame)
        schema = feature_schema or load_feature_meta()
        feature_names = [str(v) for v in schema.get("feature_names", [])]
        matrix, missing_count = prepare_feature_matrix(frame, feature_names)

        race_id = ""
        if not frame.empty and "race_id" in frame.columns:
            race_id = str(frame["race_id"].iloc[0])
        candidate_ids = (
            frame.get("horse_name", pd.Series([""] * len(frame), index=frame.index))
            .fillna("")
            .astype(str)
            .tolist()
        )
        return {
            "race_id": race_id,
            "candidate_ids": candidate_ids,
            "feature_names": list(matrix.columns),
            "X": matrix,
            "feature_meta": {
                "missing_feature_count": int(missing_count),
                "schema_source": str(Path(FEATURES_JSON_PATH)),
            },
            "_source_frame": frame,
        }


__all__ = ["FeatureGenerator"]

from ai_platform.core.features.feature_loader import (  # noqa: E402
    FeatureLoadResult,
    FeatureLoader,
    get_last_failure_reason,
    register_db_provider,
)

__all__ += ["FeatureLoadResult", "FeatureLoader", "get_last_failure_reason", "register_db_provider"]
