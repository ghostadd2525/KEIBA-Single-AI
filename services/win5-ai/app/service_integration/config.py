# -*- coding: utf-8 -*-
"""A1 Service Integration — configuration (Application layer only)."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return default


@dataclass(frozen=True)
class SingleServiceConfig:
    """HTTP Application config. Does not alter Core/Consumer contracts."""

    service_name: str = "single-ai-http"
    service_version: str = "a1/1.0"
    http_enabled: bool = True
    require_api_key: bool = True
    default_locale: str = "ja"
    max_body_bytes: int = 1_048_576

    @classmethod
    def from_env(cls) -> "SingleServiceConfig":
        return cls(
            service_name=os.environ.get("SINGLE_AI_SERVICE_NAME") or "single-ai-http",
            service_version=os.environ.get("SINGLE_AI_SERVICE_VERSION") or "a1/1.0",
            http_enabled=_env_bool("SINGLE_AI_HTTP_ENABLED", True),
            require_api_key=_env_bool("SINGLE_AI_REQUIRE_API_KEY", True),
            default_locale=(os.environ.get("SINGLE_AI_DEFAULT_LOCALE") or "ja").strip() or "ja",
            max_body_bytes=int(os.environ.get("SINGLE_AI_MAX_BODY_BYTES") or "1048576"),
        )
