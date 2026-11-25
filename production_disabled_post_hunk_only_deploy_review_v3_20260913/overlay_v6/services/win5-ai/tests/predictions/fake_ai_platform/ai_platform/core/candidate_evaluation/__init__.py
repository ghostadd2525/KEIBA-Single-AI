# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from ai_platform.core.features import FeatureLoader


class CorePipeline:
    def __init__(self, *, loader: FeatureLoader | None = None) -> None:
        self.loader = loader or FeatureLoader()

    def evaluate(self, race_id: str) -> dict[str, Any] | None:
        loaded = self.loader.load(str(race_id))
        if loaded is None:
            return None
        return {
            "ok": True,
            "context": {
                "feature_source": loaded.feature_source,
                "row_count": len(loaded.frame),
            },
        }
