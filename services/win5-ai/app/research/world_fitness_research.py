# -*- coding: utf-8 -*-
"""
Version26 World Fitness Analysis (Task A)

For Predictions assigned to midupper_world, measure soft fitness
to each EXISTING World (core / midupper / midhole / rank7 / bug / mixed).

Uses:
  1) Trigger-proximity fitness from V25 research_world_signals
     (read-only copy of classify_world_line_type thresholds — NOT executed
      to change product assignment)
  2) V22 evidence-likelihood soft fitness (documented; often degenerate
     when only midupper labels exist)

FORBIDDEN:
  New Worlds / Trigger change / Prediction / PE / CE / AI mutation
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .config import evidence_root, repo_root
from .world_activation_research import (
    SHORT_FIELD_PRESSURE_WORLD_THRESHOLD,
    WORLD_TRIGGER_RULES,
)
from .world_boundary_research import (
    AMBIGUITY_MARGIN,
    EXISTING_WORLDS,
    ExistingWorldBoundaryResearch,
    extract_world_label,
)
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-world-fitness/1.0"
NEAR_MISS_MARGIN = AMBIGUITY_MARGIN  # 0.15
TARGET_ASSIGNED = "midupper_world"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _f(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _ratio(val: float | None, thr: float) -> float:
    """Proximity to threshold in [0, 1]. Missing → 0 (and flagged separately)."""
    if val is None or thr <= 0:
        return 0.0
    return float(min(1.0, max(0.0, val / thr)))


def trigger_proximity_fitness(signals: dict[str, Any]) -> dict[str, Any]:
    """
    Soft fitness of a race to each existing World via trigger proximity.
    Does NOT call classify_world_line_type; does not mutate product.
    Missing chaos → treated as 0.0 for numeric proximity (flagged).
    """
    sig = signals or {}
    sf = _f(sig.get("short_field_pressure"))
    phase = _f(sig.get("phase") if sig.get("phase") is not None else sig.get("phase_transition"))
    chaos_raw = sig.get("chaos") if sig.get("chaos") is not None else sig.get("chaos_score")
    chaos = _f(chaos_raw)
    chaos_missing = chaos is None
    chaos_v = 0.0 if chaos is None else chaos
    diff = _f(
        sig.get("difficulty")
        if sig.get("difficulty") is not None
        else sig.get("race_leg_difficulty")
    )
    late = _f(sig.get("late_stop") if sig.get("late_stop") is not None else sig.get("late_stop_risk_score"))
    sust = _f(
        sig.get("sustained")
        if sig.get("sustained") is not None
        else sig.get("sustained_run_possible_score")
    )
    hp = _f(sig.get("high_pace") if sig.get("high_pace") is not None else sig.get("high_pace_score"))

    mixed_a = min(
        _ratio(sf, 0.72),
        max(_ratio(phase, 0.48), _ratio(chaos_v, 0.42), _ratio(diff, 0.42)),
    )
    mixed_b = _ratio(phase, 0.62)
    midupper_a = min(_ratio(sf, SHORT_FIELD_PRESSURE_WORLD_THRESHOLD), _ratio(diff, 0.38))
    midupper_b = _ratio(diff, 0.50)
    midhole = min(_ratio(late, 0.56), _ratio(sust, 0.52))
    rank7 = min(_ratio(chaos_v, 0.58), _ratio(hp, 0.48))
    bug = min(_ratio(chaos_v, 0.66), _ratio(diff, 0.62))

    soft = {
        "mixed_world": round(max(mixed_a, mixed_b), 4),
        "midupper_world": round(max(midupper_a, midupper_b), 4),
        "midhole_world": round(midhole, 4),
        "rank7_world": round(rank7, 4),
        "bug_world": round(bug, 4),
    }
    others_max = max(soft.values()) if soft else 0.0
    soft["core_world"] = round(max(0.0, 1.0 - others_max), 4)

    ranked = sorted(soft.items(), key=lambda x: (-x[1], x[0]))
    best_w, best_s = ranked[0]
    second_w, second_s = ranked[1] if len(ranked) > 1 else (None, 0.0)
    return {
        "soft": soft,
        "best_fit_world": best_w,
        "best_fit": best_s,
        "second_fit_world": second_w,
        "second_fit": second_s,
        "margin": round(best_s - float(second_s or 0.0), 4),
        "chaos_missing": chaos_missing,
        "signal_snapshot": {
            "short_field_pressure": sf,
            "phase": phase,
            "chaos": chaos,
            "difficulty": diff,
            "late_stop": late,
            "sustained": sust,
            "high_pace": hp,
        },
    }


class WorldFitnessResearch:
    def __init__(self) -> None:
        migrate()
        self.root = repo_root()
        self.evidence = evidence_root()
        self.reports = self.evidence / "reports"

    def _load_midupper_labels(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT id, race_id, bundle_json FROM predictions ORDER BY id ASC"
            ).fetchall()
        finally:
            conn.close()
        for row in rows:
            try:
                bundle = json.loads(row["bundle_json"] or "{}")
            except Exception:
                continue
            w, s = extract_world_label(bundle)
            if w != TARGET_ASSIGNED:
                continue
            rid = str(row["race_id"])
            out[rid] = {
                "race_id": rid,
                "prediction_id": int(row["id"]),
                "world": w,
                "sub_world": s,
                "source": "predictions",
            }
        return out

    def _load_snapshot_signals(self) -> dict[str, dict[str, Any]]:
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT race_id, prediction_id, payload_json FROM research_prediction_snapshots"
            ).fetchall()
        finally:
            conn.close()
        by_race: dict[str, dict[str, Any]] = {}
        for row in rows:
            rid = str(row["race_id"])
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except Exception:
                continue
            block = payload.get("research_world_signals")
            signals = (block or {}).get("signals") if isinstance(block, dict) else None
            if not isinstance(signals, dict):
                signals = {}
            by_race[rid] = {
                "prediction_id": row["prediction_id"],
                "signals": signals,
                "instrumented": isinstance(block, dict),
            }
        return by_race

    def analyze(self) -> dict[str, Any]:
        labels = self._load_midupper_labels()
        snaps = self._load_snapshot_signals()

        # V22 likelihood fitness (may be degenerate)
        boundary = ExistingWorldBoundaryResearch()
        all_labels = boundary._load_world_labels()
        rows = boundary._attach_features([], all_labels)
        tables = boundary._build_likelihood_tables(rows)
        world_n = {
            w: int(((tables.get("_world_n") or {}).get(w) or {}).get("n") or 0)
            for w in EXISTING_WORLDS
        }
        total_n = sum(world_n.values())
        bins_by_race = {
            str(r["race_id"]): r.get("bins")
            for r in rows
            if r.get("canonical_world") and r.get("bins")
        }

        per_race: list[dict[str, Any]] = []
        sum_soft: dict[str, float] = {w: 0.0 for w in EXISTING_WORLDS}
        sum_nb: dict[str, float] = {w: 0.0 for w in EXISTING_WORLDS}
        n_proxy = 0
        n_nb = 0
        chaos_missing_n = 0
        near_misses: list[dict[str, Any]] = []
        best_counter: Counter[str] = Counter()

        for rid, lab in sorted(labels.items()):
            snap = snaps.get(rid) or {}
            signals = snap.get("signals") or {}
            prox = trigger_proximity_fitness(signals)
            soft = prox["soft"]
            for w in EXISTING_WORLDS:
                sum_soft[w] += soft.get(w, 0.0)
            n_proxy += 1
            if prox["chaos_missing"]:
                chaos_missing_n += 1
            best_counter[str(prox["best_fit_world"])] += 1

            nb_soft = None
            bins = bins_by_race.get(rid)
            if bins:
                nb_soft = boundary._score_worlds(bins, tables, world_n, total_n)
                for w in EXISTING_WORLDS:
                    sum_nb[w] += nb_soft.get(w, 0.0)
                n_nb += 1

            assigned_fit = soft.get(TARGET_ASSIGNED, 0.0)
            best_other_w = None
            best_other_s = -1.0
            for w, s in soft.items():
                if w == TARGET_ASSIGNED:
                    continue
                if s > best_other_s:
                    best_other_s = s
                    best_other_w = w
            gap_to_other = round(assigned_fit - float(best_other_s), 4)
            is_near = (
                prox["best_fit_world"] != TARGET_ASSIGNED
                or gap_to_other < NEAR_MISS_MARGIN
                or prox["margin"] < NEAR_MISS_MARGIN
            )

            entry = {
                "race_id": rid,
                "prediction_id": lab.get("prediction_id"),
                "assigned_world": TARGET_ASSIGNED,
                "sub_world": lab.get("sub_world"),
                "instrumented": bool(snap.get("instrumented")),
                "trigger_soft": soft,
                "fitness_assigned_trigger": assigned_fit,
                "best_fit_world": prox["best_fit_world"],
                "best_fit": prox["best_fit"],
                "second_fit_world": prox["second_fit_world"],
                "margin": prox["margin"],
                "gap_assigned_vs_best_other": gap_to_other,
                "best_other_world": best_other_w,
                "best_other_fit": best_other_s,
                "near_miss": is_near,
                "chaos_missing": prox["chaos_missing"],
                "signals": prox["signal_snapshot"],
                "nb_soft": nb_soft,
            }
            per_race.append(entry)
            if is_near:
                near_misses.append(entry)

        mean_trigger = {
            w: round(_safe_div(sum_soft[w], n_proxy) or 0.0, 4) for w in EXISTING_WORLDS
        }
        mean_nb = {
            w: round(_safe_div(sum_nb[w], n_nb) or 0.0, 4) for w in EXISTING_WORLDS
        }

        # Rank worlds by mean trigger fitness among midupper-assigned
        ranked_mean = sorted(mean_trigger.items(), key=lambda x: -x[1])

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "product_mutation": False,
            "world_trigger_changed": False,
            "new_worlds_forbidden": True,
            "target_assigned": TARGET_ASSIGNED,
            "sample": {
                "midupper_assigned_n": len(labels),
                "evaluated_with_signals_n": n_proxy,
                "evaluated_with_nb_bins_n": n_nb,
                "near_miss_n": len(near_misses),
                "chaos_missing_n": chaos_missing_n,
                "near_miss_margin": NEAR_MISS_MARGIN,
                "label_world_n": dict(world_n),
                "nb_degenerate": all(
                    (world_n.get(w, 0) == 0) for w in EXISTING_WORLDS if w != TARGET_ASSIGNED
                )
                or (world_n.get(TARGET_ASSIGNED, 0) > 0 and sum(world_n.values()) == world_n.get(TARGET_ASSIGNED, 0)),
            },
            "mean_trigger_fitness": mean_trigger,
            "mean_trigger_rank": [
                {"world": w, "mean_fitness": s} for w, s in ranked_mean
            ],
            "mean_nb_fitness": mean_nb,
            "best_fit_distribution": dict(best_counter),
            "trigger_rules_ref": [
                {"priority": r["priority"], "world": r["world"], "trigger": r["trigger"]}
                for r in WORLD_TRIGGER_RULES
            ],
            "races": per_race,
            "near_misses": near_misses,
            "notes": [
                "Primary metric: trigger-proximity soft fitness from V25 research_world_signals",
                "NB likelihood fitness reused from V22; collapses when only midupper labels exist",
                "chaos missing → proximity uses 0.0 (understates rank7/bug/mixed chaos routes)",
                "Does not change World Trigger or Prediction assignment",
            ],
        }


def write_fitness_md(report: dict[str, Any], path: Path) -> None:
    s = report.get("sample") or {}
    lines = [
        "# Version26 — World Fitness Analysis",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"**Scope:** Predictions assigned to `{report.get('target_assigned')}` → fitness vs all EXISTING Worlds  ",
        "**Metric:** Trigger-proximity soft fitness (NOT hit rate)  ",
        "",
        "## Guardrails",
        "",
        f"- product_mutation: `{report.get('product_mutation')}`",
        f"- world_trigger_changed: `{report.get('world_trigger_changed')}`",
        f"- new_worlds_forbidden: `{report.get('new_worlds_forbidden')}`",
        "",
        "## Sample",
        "",
        f"- midupper_assigned: `{s.get('midupper_assigned_n')}`",
        f"- evaluated (with snapshot signals block): `{s.get('evaluated_with_signals_n')}`",
        f"- NB bins available: `{s.get('evaluated_with_nb_bins_n')}`",
        f"- near-miss: `{s.get('near_miss_n')}` (margin < `{s.get('near_miss_margin')}`)",
        f"- chaos_missing among evaluated: `{s.get('chaos_missing_n')}`",
        f"- NB tables degenerate (midupper-only labels): `{s.get('nb_degenerate')}`",
        "",
        "## Mean fitness to each World (midupper-assigned set)",
        "",
        "| World | Mean trigger fitness | Mean NB fitness |",
        "|-------|---------------------:|----------------:|",
    ]
    mt = report.get("mean_trigger_fitness") or {}
    mn = report.get("mean_nb_fitness") or {}
    for w in EXISTING_WORLDS:
        lines.append(f"| `{w}` | {mt.get(w)} | {mn.get(w)} |")
    lines += [
        "",
        "### Rank by mean trigger fitness",
        "",
    ]
    for i, row in enumerate(report.get("mean_trigger_rank") or [], 1):
        lines.append(f"{i}. `{row.get('world')}` — {row.get('mean_fitness')}")
    lines += [
        "",
        "## Best-fit distribution (trigger proximity argmax)",
        "",
        "| Best-fit World | N |",
        "|----------------|--:|",
    ]
    for w, n in sorted((report.get("best_fit_distribution") or {}).items(), key=lambda x: -x[1]):
        lines.append(f"| `{w}` | {n} |")
    lines += [
        "",
        "## Method",
        "",
        "1. Restrict to Prediction Bundle `evaluation.world == midupper_world`",
        "2. Load V25 `payload.research_world_signals.signals`",
        "3. Score proximity to each EXISTING World trigger (V24 matrix / `classify_world_line_type` thresholds)",
        "4. Secondary: V22 evidence-bin NB soft membership (often 1.0 on midupper only)",
        "",
        "## Notes",
        "",
    ]
    for n in report.get("notes") or []:
        lines.append(f"- {n}")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_near_miss_md(report: dict[str, Any], path: Path) -> None:
    misses = report.get("near_misses") or []
    s = report.get("sample") or {}
    lines = [
        "# Version26 — World Near-Miss",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"**Definition:** assigned=`midupper_world` but best_fit≠midupper OR "
        f"gap vs best other < `{s.get('near_miss_margin')}` OR overall margin < threshold  ",
        "",
        "## Summary",
        "",
        f"- Near-miss N: `{len(misses)}` / midupper `{s.get('midupper_assigned_n')}` "
        f"(`{_pct(_safe_div(len(misses), int(s.get('midupper_assigned_n') or 0)))}`)",
        "",
        "## Near-miss table",
        "",
        "| Race | Assigned fit | Best fit | Best other | Gap | Chaos missing |",
        "|------|-------------:|----------|------------|----:|:-------------:|",
    ]
    for r in misses[:80]:
        lines.append(
            f"| `{r.get('race_id')}` | {r.get('fitness_assigned_trigger')} | "
            f"`{r.get('best_fit_world')}` ({r.get('best_fit')}) | "
            f"`{r.get('best_other_world')}` ({r.get('best_other_fit')}) | "
            f"{r.get('gap_assigned_vs_best_other')} | "
            f"{'Y' if r.get('chaos_missing') else 'N'} |"
        )
    if not misses:
        lines.append("| _(none)_ | | | | | |")
    lines += [
        "",
        "## Soft vector examples (first 15)",
        "",
    ]
    for r in misses[:15]:
        soft = r.get("trigger_soft") or {}
        vec = ", ".join(f"{w}={soft.get(w)}" for w in EXISTING_WORLDS)
        lines.append(f"- `{r.get('race_id')}`: {vec}")
    lines += [
        "",
        "## Interpretation",
        "",
        "- Near-miss ≠ product mis-assignment; research proximity only",
        "- With chaos=NULL, rank7/bug proximity is suppressed (chaos treated as 0)",
        "- See `docs/audit/v26-chaos-trace.md` for chaos NULL root cause",
        "- No Trigger / World / Prediction changes in this run",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write() -> dict[str, Any]:
    ops = WorldFitnessResearch()
    report = ops.analyze()
    docs = repo_root() / "docs" / "research"
    docs.mkdir(parents=True, exist_ok=True)
    fit_path = docs / "v26-world-fitness.md"
    miss_path = docs / "v26-world-near-miss.md"
    write_fitness_md(report, fit_path)
    write_near_miss_md(report, miss_path)
    json_path = evidence_root() / "reports" / "v26-world-fitness.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    # slim JSON for races
    slim = {k: v for k, v in report.items() if k != "races"}
    slim["races_n"] = len(report.get("races") or [])
    slim["races_sample"] = (report.get("races") or [])[:30]
    slim["near_misses"] = report.get("near_misses") or []
    json_path.write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {
        "fitness": str(fit_path),
        "near_miss": str(miss_path),
        "json": str(json_path),
    }
    return report
