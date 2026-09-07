# -*- coding: utf-8 -*-
"""Presentation package (V109 C2) — structured display only."""
from app.consumer.presentation.dto import DISPLAY_ORDER, PRESENTATION_SCHEMA, PresentationBundle
from app.consumer.presentation.localization import localization_contract
from app.consumer.presentation.mapper import map_presentation
from app.consumer.presentation.renderer import render_presentation

__all__ = [
    "DISPLAY_ORDER",
    "PRESENTATION_SCHEMA",
    "PresentationBundle",
    "localization_contract",
    "map_presentation",
    "render_presentation",
]
