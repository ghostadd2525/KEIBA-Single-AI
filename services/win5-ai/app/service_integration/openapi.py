# -*- coding: utf-8 -*-
"""A1 OpenAPI document for Single AI HTTP Application."""
from __future__ import annotations

from typing import Any

from app.service_integration.config import SingleServiceConfig


def openapi_document(cfg: SingleServiceConfig | None = None) -> dict[str, Any]:
    cfg = cfg or SingleServiceConfig.from_env()
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Single AI HTTP API",
            "version": cfg.service_version,
            "description": (
                "Application facade over Single AI Version1 Consumer library. "
                "Does not modify Core / Prediction / Contract."
            ),
        },
        "paths": {
            "/v1/single/health": {
                "get": {
                    "summary": "Single AI service health",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/v1/single/metrics": {
                "get": {
                    "summary": "In-process request metrics",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/v1/single/openapi.json": {
                "get": {
                    "summary": "OpenAPI document",
                    "responses": {"200": {"description": "OpenAPI 3 JSON"}},
                }
            },
            "/v1/single/response": {
                "post": {
                    "summary": "Build Single Consumer response (Shadow/Staging via flags)",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["core_payload"],
                                    "properties": {
                                        "race_id": {"type": "string"},
                                        "core_payload": {"type": "object"},
                                        "options": {
                                            "type": "object",
                                            "properties": {
                                                "include_tickets": {"type": "boolean"},
                                                "include_presentation": {"type": "boolean"},
                                                "locale": {"type": "string"},
                                            },
                                        },
                                        "force": {
                                            "type": "boolean",
                                            "description": "Shadow harness only",
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Consumer response envelope"},
                        "400": {"description": "Validation error"},
                        "401": {"description": "Unauthorized"},
                        "503": {"description": "HTTP facade disabled"},
                    },
                }
            },
        },
        "components": {
            "securitySchemes": {
                "AiKey": {"type": "apiKey", "in": "header", "name": "X-AI-Key"}
            }
        },
    }
