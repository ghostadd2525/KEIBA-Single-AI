# -*- coding: utf-8 -*-
"""Collector package — contracts through Production Readiness (C-8)."""
from __future__ import annotations

from .contracts.availability import (
    AFTER_DRAW,
    AVAILABILITY_CONTRACT,
    AvailabilityContext,
    ArtifactAvailability,
    RACE_DAY,
    WEEKDAY,
    available_enqueueable_artifacts,
    get_availability,
    is_available,
)
from .contracts.dynamic import (
    DYNAMIC_ARTIFACT_TYPES,
    get_dynamic_contract,
    is_dynamic_artifact,
    list_dynamic_contracts,
)
from .contracts.retry import (
    DEFAULT_RETRY_POLICY,
    RetryPolicy,
    compute_retry_after,
    next_business_day,
)
from .contracts.weekday_distribution import (
    plan_scheduled_dates,
    summarize_distribution,
    weekday_window_for_week,
)
from .contracts.manifest import MANIFEST_SCHEMA_VERSION, assert_valid_manifest, load_schema
from .contracts.targets import CollectTarget, PlannerContract, validate_collect_target
from .repository import (
    CollectArtifactRepository,
    CollectJobRepository,
    CollectRunRepository,
    CollectTargetRepository,
    JobIdempotencyError,
)
from .budget import (
    DEFAULT_DAILY_LIMIT,
    CollectBudget,
    BudgetExhaustedError,
    resolve_daily_limit,
)
from .collector import CollectJobResult, CollectJobNotSupportedError, KeibaNetCollector
from .contracts.calendar import RaceCalendar, expand_calendar_targets
from .friday_gate import FridayGate, FridayGateResult, run_friday_gate
from .manifest_store import manifest_path_for_week, read_manifest
from .ops_monitor import (
    COMPLETE_READY,
    DYNAMIC_READY,
    DYNAMIC_REFRESHING,
    NOT_READY,
    PREDICTION_READY,
    STATIC_READY,
    CollectOpsState,
    classify_dynamic_state,
    classify_ops_state,
    evaluate_collect_ops,
)
from .planner import CollectPlanner, PlannerResult
from .queue import CollectQueue, QueueEnqueueResult
from .readiness import WeekReadiness, evaluate_week_readiness
from .retry import CollectRetry, RetryResult
from .scheduler import CollectScheduler, DynamicRefreshResult, SchedulerResult
from .validator import (
    ValidationResult,
    validate_entries_core,
    validate_odds,
    validate_race_meta,
    validate_track,
)
from . import state

__all__ = [
    "AFTER_DRAW",
    "AVAILABILITY_CONTRACT",
    "AvailabilityContext",
    "ArtifactAvailability",
    "COMPLETE_READY",
    "DEFAULT_DAILY_LIMIT",
    "DEFAULT_RETRY_POLICY",
    "DYNAMIC_ARTIFACT_TYPES",
    "DYNAMIC_READY",
    "DYNAMIC_REFRESHING",
    "MANIFEST_SCHEMA_VERSION",
    "NOT_READY",
    "PREDICTION_READY",
    "STATIC_READY",
    "RACE_DAY",
    "WEEKDAY",
    "CollectArtifactRepository",
    "CollectJobRepository",
    "CollectOpsState",
    "CollectRunRepository",
    "CollectTarget",
    "CollectTargetRepository",
    "JobIdempotencyError",
    "PlannerContract",
    "BudgetExhaustedError",
    "CollectBudget",
    "CollectJobNotSupportedError",
    "CollectJobResult",
    "CollectPlanner",
    "CollectQueue",
    "CollectRetry",
    "CollectScheduler",
    "DynamicRefreshResult",
    "FridayGate",
    "FridayGateResult",
    "KeibaNetCollector",
    "PlannerResult",
    "QueueEnqueueResult",
    "RaceCalendar",
    "RetryPolicy",
    "RetryResult",
    "SchedulerResult",
    "ValidationResult",
    "WeekReadiness",
    "assert_valid_manifest",
    "available_enqueueable_artifacts",
    "classify_dynamic_state",
    "classify_ops_state",
    "compute_retry_after",
    "evaluate_collect_ops",
    "evaluate_week_readiness",
    "expand_calendar_targets",
    "get_availability",
    "get_dynamic_contract",
    "is_available",
    "is_dynamic_artifact",
    "list_dynamic_contracts",
    "load_schema",
    "manifest_path_for_week",
    "next_business_day",
    "plan_scheduled_dates",
    "read_manifest",
    "resolve_daily_limit",
    "run_friday_gate",
    "state",
    "summarize_distribution",
    "validate_collect_target",
    "validate_entries_core",
    "validate_odds",
    "validate_race_meta",
    "validate_track",
    "weekday_window_for_week",
]
