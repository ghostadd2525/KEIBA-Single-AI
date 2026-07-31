# -*- coding: utf-8 -*-
"""Version 3 Offline Lab (A-01+A-03 adopted stack · A-02 secondary).

Isolated from Version 2 Production. Import only from research/tests.
"""
from __future__ import annotations

from .a01_accuracy import build_a01_accuracy_corpus, run_a01_ab
from .a01_validation import run_a01_validation, write_validation_artifacts
from .a02_accuracy import build_a02_accuracy_corpus, run_a02_ab
from .a03_accuracy import build_a03_accuracy_corpus, run_a03_ab
from .a03_validation import run_a03_validation, write_validation_artifacts as write_a03_validation_artifacts
from .lab_configuration_freeze import (
    CANDIDATE_REGISTRY_V2,
    LAB_CONFIGURATION,
    build_lab_baseline_v2,
    write_configuration_freeze_artifacts,
)
from .accuracy_candidate_registry import (
    CANDIDATE_REGISTRY,
    build_phase1_close_snapshot,
    write_phase1_close_artifacts,
)
from .accuracy_candidate_review import run_candidate_review, write_review_artifacts
from .ab_harness import (
    build_control_corpus_fixture,
    run_ab,
    run_p2_representation_ab,
    run_p3_admission_ab,
    run_p4_selection_ab,
)
from .flags import apply_v3_lab_flags, reset_flags_to_default, snapshot_flags
from .freeze import build_lab_baseline, validate_freeze, write_lab_baseline
from .pipeline import assert_identity_bundle, run_lab_pipeline
from .registry import get_experiment, list_experiments
from .taxonomy import taxonomy_snapshot, validate_taxonomy_lock

__all__ = [
    "apply_v3_lab_flags",
    "reset_flags_to_default",
    "snapshot_flags",
    "run_lab_pipeline",
    "assert_identity_bundle",
    "run_ab",
    "run_p2_representation_ab",
    "run_p3_admission_ab",
    "run_p4_selection_ab",
    "build_control_corpus_fixture",
    "build_a01_accuracy_corpus",
    "run_a01_ab",
    "run_a01_validation",
    "write_validation_artifacts",
    "build_a02_accuracy_corpus",
    "run_a02_ab",
    "build_a03_accuracy_corpus",
    "run_a03_ab",
    "run_a03_validation",
    "write_a03_validation_artifacts",
    "LAB_CONFIGURATION",
    "CANDIDATE_REGISTRY_V2",
    "build_lab_baseline_v2",
    "write_configuration_freeze_artifacts",
    "run_candidate_review",
    "write_review_artifacts",
    "CANDIDATE_REGISTRY",
    "build_phase1_close_snapshot",
    "write_phase1_close_artifacts",
    "list_experiments",
    "get_experiment",
    "taxonomy_snapshot",
    "validate_taxonomy_lock",
    "build_lab_baseline",
    "write_lab_baseline",
    "validate_freeze",
]
