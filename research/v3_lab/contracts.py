# -*- coding: utf-8 -*-
"""Version 3 Lab — Stage contracts.

P2 Representation Contract: v3-lab-representation/2.0
P3 Admission Contract: v3-lab-admission/2.0
A-03 Admission Contract: v3-lab-admission/2.1
P4 Selection Contract: v3-lab-selection/2.0
A-01 Evaluation Contract: v3-lab-evaluation/2.0
A-02 Evaluation Contract: v3-lab-evaluation/2.1 (D2; same shape, new rank_method)
(Purchase remains 1.0 stub.)
"""
from __future__ import annotations

from typing import Any, TypedDict

EVALUATION_CONTRACT_ACCEPTED = (
    "v3-lab-evaluation/2.0",
    "v3-lab-evaluation/2.1",
)

ADMISSION_CONTRACT_ACCEPTED = (
    "v3-lab-admission/2.0",
    "v3-lab-admission/2.1",
)


class RunnerRow(TypedDict, total=False):
    horse_id: str
    horse_number: int
    horse_name: str
    model_rank: int
    win_prob: float
    score: float
    features: dict[str, float]
    embedding: list[float]
    admission_band: str


class RaceContext(TypedDict, total=False):
    race_id: str
    field_size: int
    venue: str
    race_number: int
    admission_capacity_max: int
    meta: dict[str, Any]


class RepresentationOutput(TypedDict, total=False):
    race_id: str
    runners: list[RunnerRow]
    embedding_dim: int
    representation_id: str
    feature_keys: list[str]
    journal: dict[str, Any]


class AdmissionOutput(TypedDict, total=False):
    race_id: str
    candidate_pool: list[RunnerRow]
    capacity_max: int
    policy_id: str
    admission_id: str
    pool_journal: dict[str, Any]


class SelectionOutput(TypedDict, total=False):
    race_id: str
    selected: list[RunnerRow]
    policy_id: str
    selection_id: str
    selection_journal: dict[str, Any]


class EvaluationOutput(TypedDict, total=False):
    race_id: str
    ranked: list[RunnerRow]
    win_prob: list[float]
    policy_id: str
    evaluation_id: str
    eval_journal: dict[str, Any]


class PurchaseOutput(TypedDict, total=False):
    race_id: str
    purchase_plan: dict[str, Any]
    purchase_journal: dict[str, Any]


class LabBundle(TypedDict, total=False):
    """End-to-end lab artifact for one race."""

    race_id: str
    context: RaceContext
    runners_in: list[RunnerRow]
    representation: RepresentationOutput
    admission: AdmissionOutput
    selection: SelectionOutput
    evaluation: EvaluationOutput
    purchase: PurchaseOutput
    flags: dict[str, Any]
    metrics: dict[str, Any]
    debug: dict[str, Any]
    identity: bool


STAGE_ORDER = (
    "representation",
    "admission",
    "selection",
    "evaluation",
    "purchase",
)

CONTRACT_IDS = {
    "representation": "v3-lab-representation/2.0",
    "admission": "v3-lab-admission/2.0",
    "selection": "v3-lab-selection/2.0",
    "evaluation": "v3-lab-evaluation/2.0",
    "purchase": "v3-lab-purchase/1.0",
    "pipeline": "v3-lab-pipeline/1.0",
}


def validate_runners(runners: list[dict[str, Any]] | None) -> list[str]:
    errors: list[str] = []
    if runners is None:
        return ["runners is None"]
    if not isinstance(runners, list):
        return ["runners must be a list"]
    for i, row in enumerate(runners):
        if not isinstance(row, dict):
            errors.append(f"runners[{i}] not a dict")
            continue
        if row.get("horse_id") is None and row.get("horse_number") is None:
            errors.append(f"runners[{i}] missing horse_id/horse_number")
    return errors


def validate_representation_output(rep: dict[str, Any] | None, *, expect_enabled: bool | None = None) -> list[str]:
    """Validate Representation Contract v3-lab-representation/2.0."""
    errors: list[str] = []
    if not isinstance(rep, dict):
        return ["representation must be a dict"]
    journal = rep.get("journal") if isinstance(rep.get("journal"), dict) else {}
    contract = journal.get("contract") or ""
    if contract and contract != CONTRACT_IDS["representation"]:
        errors.append(f"unexpected representation contract: {contract}")
    enabled = bool(journal.get("enabled"))
    if expect_enabled is not None and enabled != expect_enabled:
        errors.append(f"representation.enabled expected {expect_enabled}, got {enabled}")
    errors.extend(validate_runners(rep.get("runners")))
    if enabled:
        keys = rep.get("feature_keys") or journal.get("feature_keys") or []
        if not keys:
            errors.append("enabled representation missing feature_keys")
        dim = int(rep.get("embedding_dim") or 0)
        if dim <= 0:
            errors.append("enabled representation embedding_dim must be > 0")
        for i, row in enumerate(rep.get("runners") or []):
            if not isinstance(row, dict):
                continue
            feats = row.get("features")
            emb = row.get("embedding")
            if not isinstance(feats, dict) or not feats:
                errors.append(f"runners[{i}] missing features")
            if not isinstance(emb, list) or len(emb) != dim:
                errors.append(f"runners[{i}] embedding dim mismatch")
        rid = str(rep.get("representation_id") or "")
        if not rid or rid == "identity":
            errors.append("enabled representation_id must not be identity")
    else:
        if int(rep.get("embedding_dim") or 0) != 0:
            errors.append("identity representation embedding_dim must be 0")
        if str(rep.get("representation_id") or "") not in ("", "identity"):
            errors.append("identity representation_id must be identity")
    return errors


def validate_admission_output(adm: dict[str, Any] | None, *, expect_enabled: bool | None = None) -> list[str]:
    """Validate Admission Contract v3-lab-admission/2.0."""
    errors: list[str] = []
    if not isinstance(adm, dict):
        return ["admission must be a dict"]
    journal = adm.get("pool_journal") if isinstance(adm.get("pool_journal"), dict) else {}
    contract = journal.get("contract") or ""
    if contract and contract not in ADMISSION_CONTRACT_ACCEPTED:
        errors.append(f"unexpected admission contract: {contract}")
    enabled = bool(journal.get("enabled"))
    if expect_enabled is not None and enabled != expect_enabled:
        errors.append(f"admission.enabled expected {expect_enabled}, got {enabled}")
    errors.extend(validate_runners(adm.get("candidate_pool")))
    capacity_max = int(adm.get("capacity_max") if adm.get("capacity_max") is not None else -1)
    pool = adm.get("candidate_pool") or []
    if capacity_max < 0:
        errors.append("capacity_max required")
    elif len(pool) > capacity_max:
        errors.append(f"candidate_pool size {len(pool)} exceeds capacity_max {capacity_max}")
    if enabled:
        policy = str(adm.get("policy_id") or journal.get("policy_id") or "")
        if not policy or policy == "identity":
            errors.append("enabled admission policy_id must not be identity")
        aid = str(adm.get("admission_id") or journal.get("admission_id") or "")
        if not aid or aid == "identity":
            errors.append("enabled admission_id must not be identity")
        if journal.get("leak_inputs"):
            errors.append("admission leak_inputs must be False")
    else:
        if str(adm.get("policy_id") or "identity") not in ("", "identity"):
            errors.append("identity admission policy_id must be identity")
    return errors


def validate_selection_output(
    sel: dict[str, Any] | None,
    *,
    pool: list[dict[str, Any]] | None = None,
    expect_enabled: bool | None = None,
) -> list[str]:
    """Validate Selection Contract v3-lab-selection/2.0 (Reorder-only)."""
    errors: list[str] = []
    if not isinstance(sel, dict):
        return ["selection must be a dict"]
    journal = sel.get("selection_journal") if isinstance(sel.get("selection_journal"), dict) else {}
    contract = journal.get("contract") or ""
    if contract and contract != CONTRACT_IDS["selection"]:
        errors.append(f"unexpected selection contract: {contract}")
    enabled = bool(journal.get("enabled"))
    if expect_enabled is not None and enabled != expect_enabled:
        errors.append(f"selection.enabled expected {expect_enabled}, got {enabled}")
    selected = sel.get("selected") or []
    errors.extend(validate_runners(selected))
    if enabled:
        policy = str(sel.get("policy_id") or journal.get("policy_id") or "")
        if not policy or policy == "identity":
            errors.append("enabled selection policy_id must not be identity")
        sid = str(sel.get("selection_id") or journal.get("selection_id") or "")
        if not sid or sid == "identity":
            errors.append("enabled selection_id must not be identity")
        if journal.get("leak_inputs"):
            errors.append("selection leak_inputs must be False")
        if int(journal.get("pool_external_adds") or 0) != 0:
            errors.append("selection must not add pool-external horses (Rescue forbidden)")
        if journal.get("rescue_forbidden") is False:
            errors.append("rescue_forbidden must be True")
        if pool is not None:
            pool_keys = {
                str(r.get("horse_id") or r.get("horse_number") or "")
                for r in pool
            }
            for i, row in enumerate(selected):
                key = str(row.get("horse_id") or row.get("horse_number") or "")
                if key not in pool_keys:
                    errors.append(f"selected[{i}] not in candidate pool (Rescue)")
            if journal.get("size_invariant") and len(selected) != len(pool):
                errors.append("size_invariant claimed but selected size != pool size")
    else:
        if str(sel.get("policy_id") or "identity") not in ("", "identity"):
            errors.append("identity selection policy_id must be identity")
    return errors


def validate_evaluation_output(ev: dict[str, Any] | None, *, expect_enabled: bool | None = None) -> list[str]:
    """Validate Evaluation Contract v3-lab-evaluation/2.0–2.1."""
    errors: list[str] = []
    if not isinstance(ev, dict):
        return ["evaluation must be a dict"]
    journal = ev.get("eval_journal") if isinstance(ev.get("eval_journal"), dict) else {}
    contract = journal.get("contract") or ""
    if contract and contract not in EVALUATION_CONTRACT_ACCEPTED:
        errors.append(f"unexpected evaluation contract: {contract}")
    enabled = bool(journal.get("enabled"))
    if expect_enabled is not None and enabled != expect_enabled:
        errors.append(f"evaluation.enabled expected {expect_enabled}, got {enabled}")
    errors.extend(validate_runners(ev.get("ranked")))
    if enabled:
        policy = str(ev.get("policy_id") or journal.get("policy_id") or "")
        if not policy or policy == "identity":
            errors.append("enabled evaluation policy_id must not be identity")
        if journal.get("leak_inputs"):
            errors.append("evaluation leak_inputs must be False")
        if journal.get("temperature_knob"):
            errors.append("temperature_knob must be False (CE-V2-A forbidden)")
        if not journal.get("calibration_id"):
            errors.append("enabled evaluation missing calibration_id")
    else:
        if str(ev.get("policy_id") or "identity") not in ("", "identity"):
            errors.append("identity evaluation policy_id must be identity")
    return errors


def validate_lab_bundle(bundle: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    if not isinstance(bundle, dict):
        return ["bundle must be a dict"]
    if not bundle.get("race_id"):
        errors.append("race_id required")
    errors.extend(validate_runners(bundle.get("runners_in")))
    for stage in STAGE_ORDER:
        if stage not in bundle:
            errors.append(f"missing stage output: {stage}")
    if "representation" in (bundle or {}):
        errors.extend(validate_representation_output(bundle.get("representation")))
    if "admission" in (bundle or {}):
        errors.extend(validate_admission_output(bundle.get("admission")))
    if "selection" in (bundle or {}):
        pool = ((bundle.get("admission") or {}).get("candidate_pool"))
        errors.extend(validate_selection_output(bundle.get("selection"), pool=pool))
    if "evaluation" in (bundle or {}):
        errors.extend(validate_evaluation_output(bundle.get("evaluation")))
    return errors


__all__ = [
    "RunnerRow",
    "RaceContext",
    "RepresentationOutput",
    "AdmissionOutput",
    "SelectionOutput",
    "EvaluationOutput",
    "PurchaseOutput",
    "LabBundle",
    "STAGE_ORDER",
    "CONTRACT_IDS",
    "EVALUATION_CONTRACT_ACCEPTED",
    "ADMISSION_CONTRACT_ACCEPTED",
    "validate_runners",
    "validate_representation_output",
    "validate_admission_output",
    "validate_selection_output",
    "validate_evaluation_output",
    "validate_lab_bundle",
]
