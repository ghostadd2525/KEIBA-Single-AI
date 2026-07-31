# -*- coding: utf-8 -*-
"""A-05 Shadow Comparator — Control vs Shadow race diff."""
from __future__ import annotations

from typing import Any


def classify_diff(record: dict[str, Any]) -> str:
    """Classify a labeled shadow race record."""
    c_hit = record.get("control_hit")
    s_hit = record.get("shadow_hit")
    if c_hit is None or s_hit is None:
        if record.get("pick_changed"):
            return "pick_changed_unlabeled"
        return "unlabeled"
    if c_hit and s_hit:
        return "unchanged_hit"
    if (not c_hit) and (not s_hit):
        return "unchanged_miss"
    if (not c_hit) and s_hit:
        return "improved"
    # control hit, shadow miss
    wr = record.get("winner_rank")
    if wr is not None and int(wr) == 1:
        return "worsened_winner_rank1"
    return "worsened"


def build_race_diff_record(record: dict[str, Any]) -> dict[str, Any]:
    status = classify_diff(record)
    return {
        "race_id": record.get("race_id"),
        "status": status,
        "control_pick": record.get("control_pick"),
        "shadow_pick": record.get("shadow_pick"),
        "pick_changed": bool(record.get("pick_changed")),
        "control_hit": record.get("control_hit"),
        "shadow_hit": record.get("shadow_hit"),
        "winner_id": record.get("winner_id"),
        "winner_rank": record.get("winner_rank"),
        "a05_promote": bool(record.get("a05_promote")),
        "favsafe_blocked": bool(record.get("favsafe_blocked")),
        "favsafe_reason": record.get("favsafe_reason"),
        "shadow_ok": bool(record.get("shadow_ok")),
        "shadow_error": record.get("shadow_error"),
        "worsened_winner_rank1": status == "worsened_winner_rank1",
    }


def build_comparator_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    diffs = [build_race_diff_record(r) for r in records]
    improved = [d for d in diffs if d["status"] == "improved"]
    worsened = [d for d in diffs if d["status"] in {"worsened", "worsened_winner_rank1"}]
    wr1 = [d for d in diffs if d["status"] == "worsened_winner_rank1"]
    return {
        "n": len(diffs),
        "improved_count": len(improved),
        "worsened_count": len(worsened),
        "worsened_winner_rank1_count": len(wr1),
        "unchanged_hit_count": sum(1 for d in diffs if d["status"] == "unchanged_hit"),
        "unchanged_miss_count": sum(1 for d in diffs if d["status"] == "unchanged_miss"),
        "pick_changed_count": sum(1 for d in diffs if d.get("pick_changed")),
        "shadow_error_count": sum(1 for d in diffs if not d.get("shadow_ok")),
        "improved_races": improved,
        "worsened_races": worsened,
        "worsened_winner_rank1_races": wr1,
        "all_diffs": diffs,
    }


__all__ = [
    "classify_diff",
    "build_race_diff_record",
    "build_comparator_report",
]
