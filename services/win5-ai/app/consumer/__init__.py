# -*- coding: utf-8 -*-
"""Consumer package (ADR-011 / V109 Phase C1).

Single AI entry over Core Platform v1 (read-only).
"""
from app.consumer.core_client import CoreNotFoundError, InMemoryCoreClient, get_core_payload
from app.consumer.decision_service import DecisionService, compose
from app.consumer.presentation import render_presentation
from app.consumer.registry import resolve_policy
from app.consumer.single_api import (
    CONSUMER_SCHEMA,
    ConsumerDisabledError,
    build_single_response,
)
from app.consumer.ticket import resolve_ticket

__all__ = [
    "CONSUMER_SCHEMA",
    "CoreNotFoundError",
    "ConsumerDisabledError",
    "DecisionService",
    "InMemoryCoreClient",
    "build_single_response",
    "compose",
    "get_core_payload",
    "render_presentation",
    "resolve_policy",
    "resolve_ticket",
]
