# -*- coding: utf-8 -*-
"""Decision Service package (V109 C4) — Composer, not Reasoner."""
from app.consumer.decision_service.composer import CompositionValidationError, compose
from app.consumer.decision_service.dto import SINGLE_RESPONSE_SCHEMA, SingleResponseDTO
from app.consumer.decision_service.service import (
    DecisionService,
    DecisionServiceDisabledError,
    consumer_dict_from_single_response,
)

__all__ = [
    "SINGLE_RESPONSE_SCHEMA",
    "CompositionValidationError",
    "DecisionService",
    "DecisionServiceDisabledError",
    "SingleResponseDTO",
    "compose",
    "consumer_dict_from_single_response",
]
