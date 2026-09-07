# -*- coding: utf-8 -*-
"""W5 Phase2 gate monitor — internal state only (no Feature / no Prediction).

Updates after each scheduled acquire. Does not run full Phase2 analysis.
Owner-facing alerts only for exception / gate / cohort-completion triggers.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import W5Config
from .queue import load_queue, queue_stats
from .store import load_by_horse

WINNER_RESOLVABILITY_GATE = 0.40
BASELINE_SUMMARY_NAME = "phase2_summary.json"
JOIN_TABLE_NAME = "phase2_join_table.jsonl"
TERMINAL_STATUSES = frozenset(
    {"complete", "cache_hit", "blocked", "source_missing", "parse_failed"}
)
# fetch_failed can retry — not terminal for cohort completion


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ymd(s: Any):
    if not s:
        return None
    s = str(s).strip().replace("/", "-")
    for fmt, n in (("%Y-%m-%d", 10), ("%Y%m%d", 8)):
        try:
            return datetime.strptime(s[:n], fmt).date()
        except ValueError:
            continue
    return None


def _default_paths(cfg: W5Config) -> dict[str, Path]:
    research = cfg.data_root / "research" / "maiden_phase2"
    # Prefer repo checkout copies when present on EC2
    repo = Path("/home/ubuntu/KEIBA-Single-AI/research/maiden_phase2")
    return {
        "state": cfg.w5_root / "gate_monitor_state.json",
        "alerts": cfg.w5_root / "owner_alerts.jsonl",
        "summary": repo / BASELINE_SUMMARY_NAME
        if (repo / BASELINE_SUMMARY_NAME).is_file()
        else research / BASELINE_SUMMARY_NAME,
        "join": repo / JOIN_TABLE_NAME
        if (repo / JOIN_TABLE_NAME).is_file()
        else research / JOIN_TABLE_NAME,
    }


@dataclass
class GateMonitorState:
    updated_at: str = ""
    acquire_run_path: str | None = None
    w5_complete: int = 0
    w5_pending: int = 0
    w5_queue_stats: dict[str, int] = field(default_factory=dict)
    w5_queue_total: int = 0
    history_class_counts: dict[str, int] = field(default_factory=dict)
    winner_class: dict[str, int] = field(default_factory=dict)
    winner_resolved: int = 0
    winner_unresolved: int = 0
    n_winners: int = 0
    winner_resolvability: float | None = None
    reevaluation_gate: float = WINNER_RESOLVABILITY_GATE
    reevaluation_ready: bool = False
    cohort_acquisition_complete: bool = False
    w3_sync: dict[str, Any] = field(default_factory=dict)
    alerts_emitted: list[str] = field(default_factory=list)
    source_health_state: str | None = None
    note: str = (
        "Lightweight join+W5 overlay; not a full Phase2 re-evaluation. "
        "Gate >=0.40 means Phase2 full re-evaluation ready — not Feature Phase."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _load_join(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict):
            out.append(o)
    return out


def _append_alert(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _w3_sync_status(cfg: W5Config, queue: dict[str, dict[str, Any]]) -> dict[str, Any]:
    runners_path = cfg.w3_runner_raw_path
    w3_horses: set[str] = set()
    if runners_path.is_file():
        for line in runners_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            hid = str(o.get("horse_id") or "").strip()
            if hid:
                w3_horses.add(hid)
    q_horses = set(queue.keys())
    missing = sorted(w3_horses - q_horses)
    return {
        "w3_unique_horses": len(w3_horses),
        "queue_horses": len(q_horses),
        "w3_not_in_queue": len(missing),
        "w3_not_in_queue_sample": missing[:20],
        "synced": len(missing) == 0,
    }


def _prior_count_under_cutoff(
    history_rows: list[dict[str, Any]], target_date
) -> tuple[int, bool]:
    """Return (prior_count, cutoff_ok). cutoff_ok False if target missing."""
    if target_date is None:
        return 0, False
    prior = 0
    for h in history_rows:
        hrid = str(h.get("history_race_id") or "").strip()
        if not (hrid.isdigit() and len(hrid) == 12):
            continue
        hd = _parse_ymd(h.get("history_date") or h.get("race_date"))
        if hd is None:
            continue
        if hd < target_date:
            prior += 1
    return prior, True


def update_gate_monitor(
    cfg: W5Config,
    *,
    acquire_report: dict[str, Any] | None = None,
) -> GateMonitorState:
    paths = _default_paths(cfg)
    cfg.w5_root.mkdir(parents=True, exist_ok=True)

    baseline = _load_json(paths["summary"])
    join = _load_join(paths["join"])
    queue = load_queue(cfg.queue_path)
    raw = load_by_horse(cfg.raw_path)
    qstats = queue_stats(queue)

    state = GateMonitorState(
        updated_at=_utc_iso(),
        acquire_run_path=(acquire_report or {}).get("run_report_path"),
        w5_complete=int(qstats.get("complete", 0)) + int(qstats.get("cache_hit", 0)),
        w5_pending=int(qstats.get("pending", 0)),
        w5_queue_stats=qstats,
        w5_queue_total=len(queue),
        source_health_state=(acquire_report or {}).get("source_health_state"),
    )

    # Baseline class counts (Phase2 snapshot)
    base_classes = dict(baseline.get("class_counts") or {"H-A": 56, "H-D": 349})
    base_winner = dict(baseline.get("winner_class") or {"H-A": 9, "H-D": 16})
    n_winners = int(
        baseline.get("flat_3yo_races")
        and sum(base_winner.values())
        or sum(base_winner.values())
        or 25
    )
    if not base_winner:
        n_winners = 25
        base_winner = {"H-A": 9, "H-D": 16}
    if sum(base_winner.values()) > 0:
        n_winners = sum(base_winner.values())

    class_counts = Counter(base_classes)
    winner_class = Counter(base_winner)

    # Overlay: promote H-D join rows when W5 research history yields cutoff priors
    for row in join:
        if str(row.get("history_class") or "") != "H-D":
            continue
        hid = str(row.get("horse_id") or "")
        w5 = raw.get(hid)
        if not w5:
            continue
        # Only trust successful research persistence
        src = str(w5.get("source") or "")
        if not (src.startswith("w5_") or src.startswith("hd5")):
            continue
        target = _parse_ymd(row.get("target_race_date") or row.get("race_date"))
        prior, cutoff_ok = _prior_count_under_cutoff(
            list(w5.get("history_rows") or []), target
        )
        if not cutoff_ok:
            continue
        new_cls = "H-A" if prior > 0 else "H-C"
        old = "H-D"
        if class_counts[old] > 0:
            class_counts[old] -= 1
            class_counts[new_cls] += 1
        is_winner = str(row.get("outcome_bucket") or "") == "winner" or int(
            row.get("finish_position") or 0
        ) == 1
        if is_winner and winner_class[old] > 0:
            winner_class[old] -= 1
            winner_class[new_cls] += 1

    state.history_class_counts = dict(class_counts)
    state.winner_class = dict(winner_class)
    state.n_winners = n_winners
    state.winner_resolved = int(winner_class.get("H-A", 0)) + int(
        winner_class.get("H-C", 0)
    )
    state.winner_unresolved = max(0, n_winners - state.winner_resolved)
    state.winner_resolvability = (
        round(state.winner_resolved / n_winners, 4) if n_winners else None
    )
    state.reevaluation_ready = bool(
        state.winner_resolvability is not None
        and state.winner_resolvability >= WINNER_RESOLVABILITY_GATE
    )

    sync = _w3_sync_status(cfg, queue)
    state.w3_sync = sync

    pending = int(qstats.get("pending", 0))
    fetch_failed = int(qstats.get("fetch_failed", 0))
    # Cohort complete = no pending/retryable left for current queue, and W3 synced
    state.cohort_acquisition_complete = (
        pending == 0
        and fetch_failed == 0
        and state.w5_queue_total > 0
        and bool(sync.get("synced"))
    )

    alerts: list[str] = []
    ar = acquire_report or {}
    if ar.get("stopped_block") or str(ar.get("source_health_state") or "").upper() in {
        "BLOCKED",
        "COOLDOWN",
    }:
        alerts.append("SOURCE_HEALTH_BLOCKED")
    if ar.get("parse_failed", 0) and int(ar.get("parse_failed") or 0) >= int(
        ar.get("horses_processed") or 0
    ) > 0 and int(ar.get("complete") or 0) == 0:
        alerts.append("ABNORMAL_PARSER_FAILURE")
    if state.reevaluation_ready:
        alerts.append("PHASE2_REEVALUATION_GATE")
    if state.cohort_acquisition_complete:
        alerts.append("W5_COHORT_ACQUISITION_COMPLETE")

    # Dedup gate/complete alerts against previous state
    prev = _load_json(paths["state"])
    prev_alerts = set(prev.get("alerts_emitted") or [])
    for code in alerts:
        sticky = code in {
            "PHASE2_REEVALUATION_GATE",
            "W5_COHORT_ACQUISITION_COMPLETE",
        }
        if sticky and code in prev_alerts and prev.get("reevaluation_ready") and code == "PHASE2_REEVALUATION_GATE":
            continue
        if sticky and code in prev_alerts and prev.get("cohort_acquisition_complete") and code == "W5_COHORT_ACQUISITION_COMPLETE":
            continue
        _append_alert(
            paths["alerts"],
            {
                "at": _utc_iso(),
                "code": code,
                "winner_resolvability": state.winner_resolvability,
                "winner_resolved": state.winner_resolved,
                "winner_unresolved": state.winner_unresolved,
                "history_class_counts": state.history_class_counts,
                "w5_complete": state.w5_complete,
                "w5_pending": state.w5_pending,
                "w3_sync": state.w3_sync,
                "source_health_state": state.source_health_state,
                "message": {
                    "PHASE2_REEVALUATION_GATE": "winner resolvability >= 0.40 — Phase2 full re-evaluation ready (Feature PROHIBITED)",
                    "W5_COHORT_ACQUISITION_COMPLETE": "current W5 queue terminal and W3 synced",
                    "SOURCE_HEALTH_BLOCKED": "W5 SourceHealth blocked / hard stop",
                    "ABNORMAL_PARSER_FAILURE": "acquire run parse_failed without completes",
                }.get(code, code),
            },
        )
        state.alerts_emitted.append(code)

    # Keep sticky alerts visible on state even if not re-appended
    for code in ("PHASE2_REEVALUATION_GATE", "W5_COHORT_ACQUISITION_COMPLETE"):
        if code in prev_alerts and code not in state.alerts_emitted:
            if (code == "PHASE2_REEVALUATION_GATE" and state.reevaluation_ready) or (
                code == "W5_COHORT_ACQUISITION_COMPLETE" and state.cohort_acquisition_complete
            ):
                state.alerts_emitted.append(code)

    paths["state"].write_text(
        json.dumps(state.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return state
