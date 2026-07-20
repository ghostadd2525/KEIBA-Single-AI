"""AI source adapters — swap mock → real model without changing /v1 contracts."""

from .analysis_adapter import AnalysisAdapter, get_analysis
from .kaoba_adapter import KaobaAdapter, generate_reply
from .prediction_adapter import (
    PredictionAdapter,
    get_bundle,
    get_with_meta,
    list_bundles,
    list_with_meta,
)

__all__ = [
    "PredictionAdapter",
    "AnalysisAdapter",
    "KaobaAdapter",
    "list_bundles",
    "get_bundle",
    "list_with_meta",
    "get_with_meta",
    "get_analysis",
    "generate_reply",
]
