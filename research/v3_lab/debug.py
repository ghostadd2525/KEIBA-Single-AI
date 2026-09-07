# -*- coding: utf-8 -*-
"""Version 3 Lab — debug projection (offline only)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_debug_view(bundle: dict[str, Any]) -> dict[str, Any]:
    """Compact debug dict safe for JSON dumps."""
    flags = bundle.get("flags") or {}
    rep = bundle.get("representation") or {}
    adm = bundle.get("admission") or {}
    sel = bundle.get("selection") or {}
    runners = rep.get("runners") or []
    sample_features = None
    sample_embedding = None
    if runners:
        sample_features = (runners[0].get("features") if isinstance(runners[0], dict) else None)
        sample_embedding = (runners[0].get("embedding") if isinstance(runners[0], dict) else None)
    adm_journal = adm.get("pool_journal") or {}
    sel_journal = sel.get("selection_journal") or {}
    ev = bundle.get("evaluation") or {}
    ev_journal = ev.get("eval_journal") or {}
    return {
        "race_id": bundle.get("race_id"),
        "identity": bool(bundle.get("identity")),
        "flags": flags,
        "representation": {
            "enabled": ((rep.get("journal") or {}).get("enabled")),
            "representation_id": rep.get("representation_id"),
            "contract": ((rep.get("journal") or {}).get("contract")),
            "feature_keys": rep.get("feature_keys") or ((rep.get("journal") or {}).get("feature_keys")),
            "embedding_dim": rep.get("embedding_dim"),
            "sample_features": sample_features,
            "sample_embedding": sample_embedding,
        },
        "admission": {
            "enabled": adm_journal.get("enabled"),
            "policy_id": adm.get("policy_id") or adm_journal.get("policy_id"),
            "admission_id": adm.get("admission_id") or adm_journal.get("admission_id"),
            "contract": adm_journal.get("contract"),
            "capacity_max": adm.get("capacity_max"),
            "pool_size": len(adm.get("candidate_pool") or []),
            "admitted": adm_journal.get("admitted"),
            "rejected_reason": adm_journal.get("rejected_reason"),
            "deep_extra": adm_journal.get("deep_extra"),
            "used_representation": adm_journal.get("used_representation"),
        },
        "selection": {
            "enabled": sel_journal.get("enabled"),
            "policy_id": sel.get("policy_id") or sel_journal.get("policy_id"),
            "selection_id": sel.get("selection_id") or sel_journal.get("selection_id"),
            "contract": sel_journal.get("contract"),
            "selected_size": len(sel.get("selected") or []),
            "pool_size": sel_journal.get("pool_size"),
            "swap_count": sel_journal.get("swap_count"),
            "swaps": sel_journal.get("swaps"),
            "size_invariant": sel_journal.get("size_invariant"),
            "rescue_forbidden": sel_journal.get("rescue_forbidden"),
            "pool_external_adds": sel_journal.get("pool_external_adds"),
            "order_before": sel_journal.get("order_before"),
            "order_after": sel_journal.get("order_after"),
        },
        "evaluation": {
            "enabled": ev_journal.get("enabled"),
            "policy_id": ev.get("policy_id") or ev_journal.get("policy_id"),
            "evaluation_id": ev.get("evaluation_id") or ev_journal.get("evaluation_id"),
            "contract": ev_journal.get("contract"),
            "rank_method": ev_journal.get("rank_method"),
            "calibration_id": ev_journal.get("calibration_id"),
            "mode": ev_journal.get("mode"),
            "field_crowding": ev_journal.get("field_crowding"),
            "ranked_size": len(ev.get("ranked") or []),
            "top_pick": ((ev.get("ranked") or [{}])[0].get("horse_id") if ev.get("ranked") else None),
        },
        "pool_size": len(adm.get("candidate_pool") or []),
        "selected_size": len(sel.get("selected") or []),
        "ranked_size": len(ev.get("ranked") or []),
        "stage_journals": {
            "representation": ((bundle.get("representation") or {}).get("journal")),
            "admission": adm_journal,
            "selection": sel_journal,
            "evaluation": ev_journal,
            "purchase": ((bundle.get("purchase") or {}).get("purchase_journal")),
        },
    }


def write_debug_json(bundle: dict[str, Any], path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(build_debug_view(bundle), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out


__all__ = ["build_debug_view", "write_debug_json"]
