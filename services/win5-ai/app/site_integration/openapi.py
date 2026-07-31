# -*- coding: utf-8 -*-
"""I1 OpenAPI for Existing Site Integration."""
from __future__ import annotations

from typing import Any

from app.site_integration.config import SiteIntegrationConfig


def openapi_document(cfg: SiteIntegrationConfig | None = None) -> dict[str, Any]:
    cfg = cfg or SiteIntegrationConfig.from_env()
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Single AI — Existing Site Integration (I1)",
            "version": cfg.api_version,
            "description": (
                "Web Integration facade: Site → HTTP → Single API → Core (read-only). "
                "Does not modify Prediction/Core/Consumer/Presentation/Ticket/Contract. "
                "core_payload required until Core PROMOTE Gate."
            ),
        },
        "paths": {
            "/v1/site/health": {
                "get": {
                    "summary": "Site integration health",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/v1/site/version": {
                "get": {
                    "summary": "API / platform version",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/v1/site/openapi.json": {
                "get": {
                    "summary": "OpenAPI document",
                    "responses": {"200": {"description": "OpenAPI 3 JSON"}},
                }
            },
            "/v1/site/single": {
                "post": {
                    "summary": "Call Single AI by race_id (+ core_payload)",
                    "parameters": [
                        {
                            "name": "X-AI-Key",
                            "in": "header",
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "X-Request-Timeout-Ms",
                            "in": "header",
                            "schema": {"type": "integer"},
                        },
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["race_id", "core_payload"],
                                    "properties": {
                                        "race_id": {"type": "string"},
                                        "core_payload": {"type": "object"},
                                        "options": {"type": "object"},
                                        "force": {"type": "boolean"},
                                        "timeout_ms": {"type": "integer"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "site-integration/single/v1"},
                        "400": {"description": "Validation"},
                        "401": {"description": "Unauthorized"},
                        "503": {"description": "Disabled / Consumer OFF"},
                        "504": {"description": "Timeout"},
                    },
                }
            },
            "/v1/site/single/{race_id}": {
                "post": {
                    "summary": "Same as POST /v1/site/single with race_id in path",
                    "parameters": [
                        {
                            "name": "race_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            },
        },
        "components": {
            "securitySchemes": {
                "AiKey": {"type": "apiKey", "in": "header", "name": "X-AI-Key"}
            }
        },
    }
