# -*- coding: utf-8 -*-
"""I1 Site Integration — configuration (Web layer only)."""
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
class SiteIntegrationConfig:
    """Existing-site facing Application config. Does not alter Core/Consumer."""

    service_name: str = "single-ai-site"
    api_version: str = "i1/1.0"
    http_enabled: bool = True
    require_api_key: bool = True
    default_timeout_ms: int = 12000
    max_timeout_ms: int = 30000
    default_locale: str = "ja"
    max_body_bytes: int = 1_048_576

    @classmethod
    def from_env(cls) -> "SiteIntegrationConfig":
        return cls(
            service_name=os.environ.get("SITE_SINGLE_SERVICE_NAME") or "single-ai-site",
            api_version=os.environ.get("SITE_SINGLE_API_VERSION") or "i1/1.0",
            http_enabled=_env_bool("SITE_SINGLE_HTTP_ENABLED", True),
            require_api_key=_env_bool("SITE_SINGLE_REQUIRE_API_KEY", True),
            default_timeout_ms=int(os.environ.get("SITE_SINGLE_TIMEOUT_MS") or "12000"),
            max_timeout_ms=int(os.environ.get("SITE_SINGLE_MAX_TIMEOUT_MS") or "30000"),
            default_locale=(os.environ.get("SITE_SINGLE_DEFAULT_LOCALE") or "ja").strip() or "ja",
            max_body_bytes=int(os.environ.get("SITE_SINGLE_MAX_BODY_BYTES") or "1048576"),
        )
