# -*- coding: utf-8 -*-
"""
I1 Existing Site Integration — Web facade over Single AI Version1.

Flow: Site → HTTP API → Single API → Core (read-only)

Does NOT modify: Prediction, Core, World, Consumer, Presentation, Ticket, Contract.
"""
from __future__ import annotations

from app.site_integration.config import SiteIntegrationConfig
from app.site_integration.handlers import (
    handle_health,
    handle_openapi,
    handle_site_single,
    handle_version,
    try_dispatch_get,
    try_dispatch_post,
)
from app.site_integration.openapi import openapi_document

__all__ = [
    "SiteIntegrationConfig",
    "handle_health",
    "handle_openapi",
    "handle_site_single",
    "handle_version",
    "try_dispatch_get",
    "try_dispatch_post",
    "openapi_document",
]
