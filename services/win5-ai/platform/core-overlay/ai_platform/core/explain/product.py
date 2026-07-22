# -*- coding: utf-8 -*-
"""Product journal → decision_trace stages (Explainability Phase 2).

Maps Pool+Entry / RePick journals into DecisionTraceStage shape.
Does not import Accuracy modules — journal dict contract only.
Design: docs/releases/v2-explainability-design-review.md §3.5 / §10 Phase 2
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _status_from_journal(j: dict[str, Any] | None, *, applied_when: str) -> str:
    """Map journal enabled/fired/reason → applied | skipped | not_applied."""
    if not j or not isinstance(j, dict):
        return "not_applied"
    if not j.get("enabled"):
        return "not_applied"
    reason = str(j.get("reason") or "")
    if reason == "disabled":
        return "not_applied"
    if applied_when == "fired" and j.get("fired"):
        return "applied"
    if applied_when == "inserted" and j.get("inserted"):
        return "applied"
    if applied_when == "displaced" and (j.get("displaced") or reason in {"ok", "displaced"}):
        return "applied"
    # Enabled but did not act
    return "skipped"


def map_pool_entry_journal(
    journal: dict[str, Any] | None,
    *,
    timestamp: str | None = None,
) -> list[dict[str, Any]]:
    """PE journal → candidate_pool + entry stages."""
    if not journal or not isinstance(journal, dict):
        return []
    ts = timestamp or journal.get("timestamp") or _utc_now_iso()
    facet = str(journal.get("facet") or "PE-V2-A")
    reason = str(journal.get("reason") or "")
    cand = str(journal.get("cand_name") or "")
    cand_rank = journal.get("cand_rank")
    before_n = journal.get("pool_size_before")
    after_n = journal.get("pool_size_after")

    pool_status = _status_from_journal(journal, applied_when="fired")
    if pool_status == "applied":
        pool_summary = (
            f"Pool+Entry ({facet}): rank{cand_rank} {cand} を Pool に追加"
            if cand
            else f"Pool+Entry ({facet}): Pool 更新"
        )
    elif pool_status == "skipped":
        pool_summary = f"Pool+Entry ({facet}): 未発火（{reason or 'skipped'}）"
    else:
        pool_summary = f"Product Pool 未適用（{reason or 'disabled'}）"

    entry_status = _status_from_journal(journal, applied_when="inserted")
    if entry_status == "applied":
        entry_summary = (
            f"Entry ({facet}): {cand}（rank{cand_rank}）を Entry 登録"
            if cand
            else f"Entry ({facet}): 候補を Entry 登録"
        )
    elif entry_status == "skipped":
        entry_summary = f"Entry ({facet}): 未登録（{reason or 'skipped'}）"
    else:
        entry_summary = f"Product Entry 未適用（{reason or 'disabled'}）"

    reason_codes = [facet.lower().replace("-", "_"), f"pe_{reason}"] if reason else [facet.lower()]

    pool_stage: dict[str, Any] = {
        "stage": "candidate_pool",
        "status": pool_status,
        "timestamp": ts,
        "delta": {
            "summary": pool_summary,
            "reason_codes": reason_codes,
            "before": {"pool_size": before_n},
            "after": {"pool_size": after_n},
            "inputs": {
                "facet": facet,
                "cand_name": cand,
                "cand_rank": cand_rank,
                "cand_route_score": journal.get("cand_route_score"),
            },
            "outputs": {
                "fired": bool(journal.get("fired")),
                "inserted": bool(journal.get("inserted")),
            },
        },
    }
    entry_stage: dict[str, Any] = {
        "stage": "entry",
        "status": entry_status,
        "timestamp": ts,
        "delta": {
            "summary": entry_summary,
            "reason_codes": reason_codes,
            "before": {"pool_size": before_n},
            "after": {"pool_size": after_n, "inserted": bool(journal.get("inserted"))},
            "inputs": {
                "facet": facet,
                "cand_name": cand,
                "cand_rank": cand_rank,
            },
            "outputs": {"inserted": bool(journal.get("inserted"))},
        },
    }
    return [pool_stage, entry_stage]


def map_repick_journal(
    journal: dict[str, Any] | None,
    *,
    timestamp: str | None = None,
) -> list[dict[str, Any]]:
    """RP journal → repick stage (design §3.5)."""
    if not journal or not isinstance(journal, dict):
        return []
    ts = timestamp or journal.get("timestamp") or _utc_now_iso()
    facet = str(journal.get("facet") or "RP-V2-A")
    reason = str(journal.get("reason") or "")
    cand = str(journal.get("cand_name") or "")
    cand_rank = journal.get("cand_rank")
    surv = journal.get("cand_surv_pos")
    victim = str(journal.get("victim_name") or "")
    victim_rank = journal.get("victim_rank")
    n = journal.get("repick_n")
    before_n = journal.get("repick_size_before")
    after_n = journal.get("repick_size_after")

    status = _status_from_journal(journal, applied_when="displaced")
    if status == "applied":
        summary = (
            f"NEAR rescue: rank{cand_rank} {cand} → repick membership"
            if cand
            else f"RePick ({facet}): membership 更新"
        )
        if victim:
            summary += f"（displace {victim}）"
    elif status == "skipped":
        summary = f"RePick ({facet}): 未実行（{reason or 'skipped'}）"
    else:
        summary = f"RePick 未適用（{reason or 'disabled'}）"

    reason_codes = ["rv2_near", facet.lower().replace("-", "_"), f"rp_{reason}"]

    stage: dict[str, Any] = {
        "stage": "repick",
        "status": status,
        "timestamp": ts,
        "delta": {
            "summary": summary,
            "reason_codes": reason_codes,
            "before": {
                "in_repick": 0 if status == "applied" else None,
                "surv_pos": surv,
                "repick_size": before_n,
            },
            "after": {
                "in_repick": 1 if status == "applied" else 0,
                "repick_size": after_n,
                "displaced": bool(journal.get("displaced")),
            },
            "inputs": {
                "N": n,
                "cand_name": cand,
                "cand_rank": cand_rank,
                "victim_rank": victim_rank,
                "facet": facet,
            },
            "outputs": {
                "displaced": bool(journal.get("displaced")),
                "fired": bool(journal.get("fired")),
                "actuator_ok": bool(journal.get("actuator_ok")),
            },
        },
    }
    return [stage]


def build_product_stages(
    *,
    pool_entry: dict[str, Any] | None = None,
    repick: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> list[dict[str, Any]]:
    """Build product_stages list from journals. Empty if no journals."""
    stages: list[dict[str, Any]] = []
    stages.extend(map_pool_entry_journal(pool_entry, timestamp=timestamp))
    stages.extend(map_repick_journal(repick, timestamp=timestamp))
    return stages


def merge_product_into_trace(
    base_stages: list[dict[str, Any]],
    product_stages: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Replace matching stage keys with product journal stages (pass-through delta)."""
    if not product_stages:
        return list(base_stages or [])
    by_stage = {s.get("stage"): s for s in (base_stages or []) if s.get("stage")}
    for p in product_stages:
        key = p.get("stage")
        if key:
            by_stage[key] = p
    # Preserve base order; append any unknown product stages
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for s in base_stages or []:
        key = s.get("stage")
        if key and key in by_stage:
            ordered.append(by_stage[key])
            seen.add(str(key))
        else:
            ordered.append(s)
    for p in product_stages:
        key = str(p.get("stage") or "")
        if key and key not in seen:
            ordered.append(p)
            seen.add(key)
    return ordered


def extract_journals_from_meta(meta: dict[str, Any] | None) -> dict[str, Any]:
    """Pull known journal keys from race meta (WIN5 product path)."""
    meta = meta or {}
    out: dict[str, Any] = {}
    pe = meta.get("_win5_pool_entry_v2_journal") or meta.get("pool_entry_journal")
    rp = meta.get("_win5_repick_v2_journal") or meta.get("repick_journal")
    if pe:
        out["pool_entry"] = pe
    if rp:
        out["repick"] = rp
    if meta.get("product_journal_timestamp"):
        out["timestamp"] = meta.get("product_journal_timestamp")
    return out


__all__ = [
    "build_product_stages",
    "merge_product_into_trace",
    "map_pool_entry_journal",
    "map_repick_journal",
    "extract_journals_from_meta",
]
