# -*- coding: utf-8 -*-
"""ModelRegistry — PC-3 model path resolution for Core Scorer."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from demo_probability_model_logic import MODEL_PATH, load_model


class ModelRegistry:
    """Resolve and cache the ranking model used by Scorer."""

    def __init__(self) -> None:
        self._model: Any = None
        self._model_path: Path | None = None
        self._model_source: str = ""

    @staticmethod
    def resolve_model_path() -> Path:
        env = (os.environ.get("CORE_MODEL_PATH") or "").strip()
        if env:
            return Path(env)
        return MODEL_PATH

    def get_model(self) -> tuple[Any | None, str]:
        path = self.resolve_model_path()
        if self._model is not None and self._model_path == path:
            return self._model, self._model_source
        if not path.exists():
            self._model = None
            self._model_source = "missing"
            self._model_path = path
            return None, self._model_source
        self._model = load_model(path)
        self._model_path = path
        self._model_source = path.name
        return self._model, self._model_source


_default_registry = ModelRegistry()


def get_ranking_model() -> tuple[Any | None, str]:
    return _default_registry.get_model()
