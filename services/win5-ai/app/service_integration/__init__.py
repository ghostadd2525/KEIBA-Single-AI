# -*- coding: utf-8 -*-
"""
A1 Service Integration — Single AI Version1 as HTTP Application.

Owns: HTTP routes, validation, serialization, OpenAPI, health, metrics,
logging, error handling, configuration.

Does NOT own: Prediction, Core, Consumer logic, Presentation, Ticket,
Decision semantics, Contract changes. Production Deploy = separate gate.
"""
from __future__ import annotations

from app.service_integration.config import SingleServiceConfig
from app.service_integration.handlers import (
    handle_health,
    handle_metrics,
    handle_openapi,
    handle_single_response,
    try_dispatch_get,
    try_dispatch_post,
)
from app.service_integration.openapi import openapi_document

__all__ = [
    "SingleServiceConfig",
    "handle_health",
    "handle_metrics",
    "handle_openapi",
    "handle_single_response",
    "try_dispatch_get",
    "try_dispatch_post",
    "openapi_document",
]
