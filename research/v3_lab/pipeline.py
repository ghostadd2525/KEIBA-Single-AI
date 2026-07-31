# -*- coding: utf-8 -*-
"""Version 3 Lab Pipeline.

Representation → Admission → Selection → Evaluation → Purchase

P2: Representation Feature Generator (F_V3_REPRESENTATION).
P3: Admission AP-V3-A Banded Deep (F_V3_ADMISSION).
P4: Selection SEL-V3-RO Reorder-only (F_V3_SELECTION).
A-01: Evaluation D1 Recalibrator (F_V3_RANK_D1_ENABLED).
Purchase remains stub.

When all F_V3_* are OFF (default), output is identity w.r.t. input runners
(Evaluation only sorts by existing model_rank for stability).
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import flags
from .contracts import CONTRACT_IDS, validate_lab_bundle
from .debug import build_debug_view
from .metrics import get_metrics_sink
from .stages import (
    run_admission,
    run_evaluation,
    run_purchase,
    run_representation,
    run_selection,
)


def run_lab_pipeline(
    context: dict[str, Any],
    runners: list[dict[str, Any]],
    *,
    capacity_n: int | None = None,
    metrics: Any | None = None,
) -> dict[str, Any]:
    """Run offline lab pipeline. Never touches V2 production modules."""
    sink = metrics or get_metrics_sink()
    ctx = deepcopy(context or {})
    race_id = str(ctx.get("race_id") or "")
    runners_in = deepcopy(runners or [])

    sink.emit("lab.pipeline.start", race_id=race_id)
    flag_snap = flags.snapshot_flags()
    identity = not flags.any_stage_enabled()

    representation = run_representation(ctx, runners_in)
    rep_enabled = bool(representation["journal"]["enabled"])
    sink.emit("lab.stage.representation", race_id=race_id, enabled=rep_enabled)
    sink.emit("lab.representation.enabled", race_id=race_id, value=int(rep_enabled))
    sink.emit(
        "lab.representation.feature_count",
        race_id=race_id,
        value=len(representation.get("feature_keys") or []),
    )
    sink.emit(
        "lab.representation.embedding_dim",
        race_id=race_id,
        value=int(representation.get("embedding_dim") or 0),
    )
    sink.emit(
        "lab.representation.runner_count",
        race_id=race_id,
        value=len(representation.get("runners") or []),
    )

    admission = run_admission(ctx, representation["runners"])
    adm_journal = admission.get("pool_journal") or {}
    adm_enabled = bool(adm_journal.get("enabled"))
    sink.emit("lab.stage.admission", race_id=race_id, enabled=adm_enabled)
    sink.emit("lab.admission.enabled", race_id=race_id, value=int(adm_enabled))
    sink.emit(
        "lab.admission.pool_size",
        race_id=race_id,
        value=len(admission.get("candidate_pool") or []),
    )
    sink.emit(
        "lab.admission.capacity_max",
        race_id=race_id,
        value=int(admission.get("capacity_max") or 0),
    )
    sink.emit(
        "lab.admission.admitted_count",
        race_id=race_id,
        value=int(adm_journal.get("admitted_count") or len(admission.get("candidate_pool") or [])),
    )
    sink.emit(
        "lab.admission.rejected_count",
        race_id=race_id,
        value=int(adm_journal.get("rejected_count") or 0),
    )
    sink.emit(
        "lab.admission.deep_extra",
        race_id=race_id,
        value=int(adm_journal.get("deep_extra") or 0),
    )

    selection = run_selection(ctx, admission["candidate_pool"], capacity_n=capacity_n)
    sel_journal = selection.get("selection_journal") or {}
    sel_enabled = bool(sel_journal.get("enabled"))
    sink.emit("lab.stage.selection", race_id=race_id, enabled=sel_enabled)
    sink.emit("lab.selection.enabled", race_id=race_id, value=int(sel_enabled))
    sink.emit(
        "lab.selection.selected_size",
        race_id=race_id,
        value=len(selection.get("selected") or []),
    )
    sink.emit(
        "lab.selection.pool_size",
        race_id=race_id,
        value=int(sel_journal.get("pool_size") or len(admission.get("candidate_pool") or [])),
    )
    sink.emit(
        "lab.selection.swap_count",
        race_id=race_id,
        value=int(sel_journal.get("swap_count") or 0),
    )
    sink.emit(
        "lab.selection.size_invariant",
        race_id=race_id,
        value=int(bool(sel_journal.get("size_invariant"))),
    )
    sink.emit(
        "lab.selection.pool_external_adds",
        race_id=race_id,
        value=int(sel_journal.get("pool_external_adds") or 0),
    )

    evaluation = run_evaluation(ctx, selection["selected"])
    ev_journal = evaluation.get("eval_journal") or {}
    ev_enabled = bool(ev_journal.get("enabled"))
    sink.emit("lab.stage.evaluation", race_id=race_id, enabled=ev_enabled)
    sink.emit("lab.evaluation.enabled", race_id=race_id, value=int(ev_enabled))
    sink.emit(
        "lab.evaluation.ranked_size",
        race_id=race_id,
        value=len(evaluation.get("ranked") or []),
    )

    purchase = run_purchase(ctx, evaluation["ranked"])
    sink.emit("lab.stage.purchase", race_id=race_id, enabled=purchase["purchase_journal"]["enabled"])

    if identity:
        sink.emit("lab.identity", race_id=race_id)

    bundle: dict[str, Any] = {
        "contract": CONTRACT_IDS["pipeline"],
        "race_id": race_id,
        "context": ctx,
        "runners_in": runners_in,
        "representation": representation,
        "admission": admission,
        "selection": selection,
        "evaluation": evaluation,
        "purchase": purchase,
        "flags": flag_snap,
        "metrics": sink.snapshot(),
        "identity": identity,
    }
    bundle["debug"] = build_debug_view(bundle)
    sink.emit("lab.pipeline.end", race_id=race_id, identity=identity)
    return bundle


def assert_identity_bundle(bundle: dict[str, Any], runners_in: list[dict[str, Any]]) -> list[str]:
    """Return errors if Flag-OFF path drifted from input horse set."""
    errors = validate_lab_bundle(bundle)
    if not bundle.get("identity"):
        errors.append("expected identity=True when flags OFF")
    in_ids = [str(r.get("horse_id") or r.get("horse_number")) for r in runners_in]
    out = ((bundle.get("purchase") or {}).get("purchase_plan") or {}).get("legs") or []
    out_ids = [str(x.get("horse_id") or x.get("horse_number")) for x in out]
    if sorted(in_ids) != sorted(out_ids):
        errors.append("purchase legs horse set differs from input")
    return errors


__all__ = ["run_lab_pipeline", "assert_identity_bundle"]
