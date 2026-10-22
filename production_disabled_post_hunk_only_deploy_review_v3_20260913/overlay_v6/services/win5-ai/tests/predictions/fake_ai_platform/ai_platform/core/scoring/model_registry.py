# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path


class ModelRegistry:
    @staticmethod
    def resolve_model_path() -> Path:
        env = (os.environ.get("CORE_MODEL_PATH") or "").strip()
        return Path(env) if env else Path("missing-model.bin")
