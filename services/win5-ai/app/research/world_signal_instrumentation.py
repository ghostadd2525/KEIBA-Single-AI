# -*- coding: utf-8 -*-
"""
Version25 World Signal Instrumentation

Persist already-computed World judgment *signals* into Research Snapshots.
Copy only — no World Trigger / Prediction / PE / CE / AI mutation.

FORBIDDEN:
  Changing classify_world_line_type thresholds or outcomes (product)
  Writing back to predictions.bundle_json
  New Worlds
  Re-judging races for product purposes
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .config import evidence_root, repo_root
from .world_boundary_research import extract_world_label
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-world-signal-instrumentation/1.0"

# Inventory of signals to persist (research keys)
SIGNAL_INVENTORY: tuple[str, ...] = (
    "world",
    "sub_world",
    "chaos",
    "chaos_score",
    "difficulty",
    "race_leg_difficulty",
    "phase",
    "phase_transition",
    "late_stop",
    "late_stop_risk_score",
    "sustained",
    "sustained_run_possible_score",
    "high_pace",
    "high_pace_score",
    "pace_collapse_risk",
    "world_line",
    "world_line_score",
    "world_score",
    "world_reason",
    "short_field_pressure",
    "traffic_score",
    "world_load_score",
)

# Map possible nested source keys → inventory keys
SOURCE_ALIASES: dict[str, tuple[str, ...]] = {
    "chaos": ("chaos", "chaos_score"),
    "chaos_score": ("chaos_score", "chaos"),
    "difficulty": ("difficulty", "race_leg_difficulty"),
    "race_leg_difficulty": ("race_leg_difficulty", "difficulty"),
    "phase": ("phase", "phase_transition"),
    "phase_transition": ("phase_transition", "phase"),
    "late_stop": ("late_stop", "late_stop_risk_score"),
    "late_stop_risk_score": ("late_stop_risk_score", "late_stop"),
    "sustained": ("sustained", "sustained_run_possible_score"),
    "sustained_run_possible_score": ("sustained_run_possible_score", "sustained"),
    "high_pace": ("high_pace", "high_pace_score"),
    "high_pace_score": ("high_pace_score", "high_pace"),
    "pace_collapse_risk": ("pace_collapse_risk",),
    "world_line": ("world_line", "world_line_score"),
    "world_line_score": ("world_line_score", "world_line"),
    "world_score": ("world_score", "world_line_score", "world_line"),
    "world_reason": ("world_reason", "world_line_reason", "_world_reason"),
    "short_field_pressure": ("short_field_pressure",),
    "traffic_score": ("traffic_score",),
    "world_load_score": ("world_load_score",),
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _as_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _empty_signals() -> dict[str, Any]:
    return {k: None for k in SIGNAL_INVENTORY}


def _walk_collect(obj: Any, found: dict[str, Any], depth: int = 0) -> None:
    if depth > 5 or not isinstance(obj, dict):
        return
    for k, v in obj.items():
        if k not in found and (
            k in SIGNAL_INVENTORY
            or k
            in {
                "chaos_score",
                "race_leg_difficulty",
                "phase_transition",
                "late_stop_risk_score",
                "sustained_run_possible_score",
                "high_pace_score",
                "pace_collapse_risk",
                "world_line_score",
                "short_field_pressure",
                "traffic_score",
                "world_load_score",
                "world_reason",
            }
        ):
            if isinstance(v, (int, float)) or (
                isinstance(v, str) and k in {"world", "sub_world", "world_reason"}
            ):
                found[k] = v
        if isinstance(v, dict):
            _walk_collect(v, found, depth + 1)


def extract_signals_from_bundle(bundle: dict[str, Any] | None) -> dict[str, Any]:
    """Copy labels/signals already present in Prediction Bundle (no judgment)."""
    out = _empty_signals()
    if not isinstance(bundle, dict):
        return out
    w, s = extract_world_label(bundle)
    if w:
        out["world"] = w
    if s:
        out["sub_world"] = s
    found: dict[str, Any] = {}
    _walk_collect(bundle, found)
    for inv_key, aliases in SOURCE_ALIASES.items():
        if out.get(inv_key) is not None:
            continue
        for a in aliases:
            if a in found and found[a] is not None:
                if inv_key in {"world", "sub_world", "world_reason"}:
                    out[inv_key] = str(found[a])
                else:
                    out[inv_key] = _as_float(found[a])
                break
    # dual-write aliases
    _mirror_aliases(out)
    return out


def _mirror_aliases(signals: dict[str, Any]) -> None:
    pairs = (
        ("chaos", "chaos_score"),
        ("difficulty", "race_leg_difficulty"),
        ("phase", "phase_transition"),
        ("late_stop", "late_stop_risk_score"),
        ("sustained", "sustained_run_possible_score"),
        ("high_pace", "high_pace_score"),
        ("world_line", "world_line_score"),
    )
    for a, b in pairs:
        if signals.get(a) is None and signals.get(b) is not None:
            signals[a] = signals[b]
        if signals.get(b) is None and signals.get(a) is not None:
            signals[b] = signals[a]
    if signals.get("world_score") is None and signals.get("world_line_score") is not None:
        signals["world_score"] = signals["world_line_score"]


def extract_signals_from_core_meta(
    meta: dict[str, Any] | None,
    *,
    line_scores: dict[str, Any] | None = None,
    short_field_pressure: float | None = None,
) -> dict[str, Any]:
    """
    Copy numeric signals from Core race meta / world_line scores.
    Does NOT call classify_world_line_type — no World judgment.
    """
    out = _empty_signals()
    meta = meta or {}
    line_scores = line_scores or {}

    def put(key: str, val: Any) -> None:
        if val is None:
            return
        if key in {"world", "sub_world", "world_reason"}:
            out[key] = str(val)
        else:
            fv = _as_float(val)
            if fv is not None:
                out[key] = fv

    put("chaos_score", meta.get("chaos_score"))
    put("race_leg_difficulty", meta.get("race_leg_difficulty"))
    put("late_stop_risk_score", meta.get("late_stop_risk_score"))
    put("sustained_run_possible_score", meta.get("sustained_run_possible_score"))
    put("high_pace_score", meta.get("high_pace_score"))
    put("pace_collapse_risk", meta.get("pace_collapse_risk"))
    put("traffic_score", meta.get("traffic_score"))
    put("world_load_score", meta.get("world_load_score"))
    put("short_field_pressure", meta.get("short_field_pressure"))
    if short_field_pressure is not None:
        put("short_field_pressure", short_field_pressure)

    put("late_stop", line_scores.get("late_stop"))
    put("sustained", line_scores.get("sustained"))
    put("high_pace", line_scores.get("high_pace"))
    put("phase_transition", line_scores.get("phase_transition"))
    put("world_line_score", line_scores.get("world_line_score"))
    put("world_line", line_scores.get("world_line_score"))
    put("world_score", line_scores.get("world_line_score"))
    # calc_world_line_score also exposes traffic / world_integrated
    put("traffic_score", line_scores.get("traffic"))
    put("world_load_score", line_scores.get("world_integrated"))

    _mirror_aliases(out)
    return out


def merge_signals(*parts: dict[str, Any]) -> dict[str, Any]:
    """First non-null wins per key (prefer earlier parts)."""
    out = _empty_signals()
    for part in parts:
        for k in SIGNAL_INVENTORY:
            if out.get(k) is None and part.get(k) is not None:
                out[k] = part[k]
    _mirror_aliases(out)
    return out


def _ensure_research_core_path() -> str | None:
    """Insert production/research Core roots onto sys.path (research-only)."""
    import os
    import sys

    candidates: list[Path] = []
    for env_key in ("AI_PLATFORM_ROOT",):
        v = (os.environ.get(env_key) or "").strip()
        if v:
            candidates.append(Path(v))
    # Production EC2 layout (expect-ai.service PYTHONPATH)
    candidates.append(Path("/opt/expect-ai/platform"))
    try:
        root = repo_root()
        candidates.append(root / "services" / "win5-ai" / "platform" / "core-overlay")
        candidates.append(root.parent)  # e.g. /home/ubuntu when repo is KEIBA-Single-AI
    except Exception:  # noqa: BLE001
        pass
    cwd = Path.cwd()
    candidates.extend(
        [
            cwd,
            cwd / "platform" / "core-overlay",
            cwd.parent,
            Path("/home/ubuntu"),
        ]
    )
    for root in candidates:
        if (root / "ai_platform").is_dir():
            s = str(root)
            if s not in sys.path:
                sys.path.insert(0, s)
            return s
    return None


def _try_core_meta_copy(race_id: str) -> tuple[dict[str, Any], list[str]]:
    """
    Read-only: rebuild Core race meta + world_line *scores* for research copy.

    Stops before classify_world / classify_world_line_type — no World judgment.
    Does not mutate Prediction / PE / CE product stores or bundle_json.
    """
    notes: list[str] = []
    try:
        from app.engine.adapters.single_prediction_mapper import (
            ensure_ai_platform_path,
            resolve_core_race_id,
        )

        ensure_ai_platform_path()
        core_root = _ensure_research_core_path()
        if core_root:
            notes.append(f"core_path:{core_root}")
        else:
            notes.append("core_path_missing")
        core_id = resolve_core_race_id(race_id)
        if not core_id:
            notes.append("core_race_id_unresolved")
            return _empty_signals(), notes

        import pandas as pd

        from ai_platform.core.candidate_evaluation import CorePipeline
        import demo_ticket_optimizer_core as legacy

        pipe = CorePipeline()
        loaded = pipe.load_race_input(core_id)
        if loaded is None:
            notes.append("feature_load_none")
            return _empty_signals(), notes

        runners = loaded.frame
        feature_matrix = pipe.features.build_feature_matrix(runners)
        scores = pipe.scoring.score_candidates(feature_matrix)
        scored_frame = scores["_source_frame"].copy()
        scored_frame["base_model_score"] = scores["base_model_score"]
        scored_frame["adjusted_model_score"] = scores["adjusted_model_score"]
        scored_frame["win_prob"] = scores["win_prob"]
        ranking = pipe.ranking.build_ranking(scores)
        rank_by_id = {row["horse_name"]: row["rank"] for row in ranking["ranking"]}
        scored_frame["model_rank"] = (
            scored_frame.get("horse_name", pd.Series("", index=scored_frame.index))
            .fillna("")
            .astype(str)
            .map(rank_by_id)
        )

        # Meta + score functions only — never classify_world
        meta = dict(pipe.world.build_race_meta(scored_frame) or {})
        meta["race_id"] = str(core_id)
        # Copy numeric columns already present on the scored frame (no judgment)
        for col in (
            "chaos_score",
            "traffic_score",
            "world_load_score",
            "late_stop_risk_score",
            "high_pace_score",
            "sustained_run_possible_score",
            "pace_collapse_risk",
            "race_leg_difficulty",
        ):
            if meta.get(col) is not None:
                continue
            if col in scored_frame.columns:
                try:
                    val = scored_frame[col].iloc[0]
                    fv = _as_float(val)
                    if fv is not None:
                        meta[col] = fv
                except Exception:  # noqa: BLE001
                    pass
        line_scores = dict(legacy.calc_world_line_score(meta) or {})
        sf = float(legacy.calc_short_field_pressure(meta))
        signals = extract_signals_from_core_meta(
            meta, line_scores=line_scores, short_field_pressure=sf
        )
        notes.append("core_meta_score_copy_no_classify")
        return signals, notes
    except Exception as exc:  # noqa: BLE001
        return _empty_signals(), [f"core_copy_error:{type(exc).__name__}:{exc}"]


def build_research_world_signals(
    *,
    race_id: str,
    prediction_id: int | None = None,
    bundle: dict[str, Any] | None = None,
    try_core: bool = True,
) -> dict[str, Any]:
    """Assemble research_world_signals block for Snapshot payload."""
    sources: list[str] = []
    from_bundle = extract_signals_from_bundle(bundle)
    if any(from_bundle.get(k) is not None for k in ("world", "sub_world")):
        sources.append("prediction_bundle_labels")
    if any(
        from_bundle.get(k) is not None
        for k in SIGNAL_INVENTORY
        if k not in {"world", "sub_world"}
    ):
        sources.append("prediction_bundle_signals")

    from_core = _empty_signals()
    core_notes: list[str] = []
    if try_core:
        from_core, core_notes = _try_core_meta_copy(race_id)
        sources.extend([n for n in core_notes if n.startswith("core_")])

    # Prefer bundle labels; prefer core numerics when bundle lacks them
    merged = merge_signals(from_bundle, from_core)
    # If bundle had world label, keep it over core (product observation first)
    if from_bundle.get("world"):
        merged["world"] = from_bundle["world"]
    if from_bundle.get("sub_world"):
        merged["sub_world"] = from_bundle["sub_world"]

    non_null = sum(1 for k in SIGNAL_INVENTORY if merged.get(k) is not None)
    total = len(SIGNAL_INVENTORY)
    return {
        "schema_version": SCHEMA_VERSION,
        "instrumented_at": _now(),
        "race_id": race_id,
        "prediction_id": prediction_id,
        "signals": merged,
        "inventory": list(SIGNAL_INVENTORY),
        "non_null_n": non_null,
        "null_n": total - non_null,
        "persistence_rate": round(_safe_div(non_null, total) or 0.0, 4),
        "null_rate": round(_safe_div(total - non_null, total) or 0.0, 4),
        "sources": sources,
        "notes": core_notes,
        "score_mutated": False,
        "prediction_mutated": False,
        "world_trigger_changed": False,
        "judgment_changed": False,
        "pe_ce_ai_changed": False,
    }


def load_prediction_bundle(prediction_id: int | None, race_id: str | None = None) -> dict[str, Any]:
    conn = connect()
    try:
        if prediction_id is not None:
            row = conn.execute(
                "SELECT bundle_json FROM predictions WHERE id=?",
                (prediction_id,),
            ).fetchone()
            if row:
                try:
                    return json.loads(row["bundle_json"] or "{}")
                except Exception:
                    return {}
        if race_id:
            row = conn.execute(
                """
                SELECT bundle_json FROM predictions
                WHERE race_id=? ORDER BY id DESC LIMIT 1
                """,
                (race_id,),
            ).fetchone()
            if row:
                try:
                    return json.loads(row["bundle_json"] or "{}")
                except Exception:
                    return {}
        return {}
    finally:
        conn.close()


def attach_world_signals_to_payload(
    payload: dict[str, Any],
    *,
    try_core: bool = True,
) -> dict[str, Any]:
    """Mutate research snapshot payload only (not product prediction)."""
    race_id = str(payload.get("race_id") or "")
    prediction_id = payload.get("prediction_id")
    try:
        pid = int(prediction_id) if prediction_id is not None else None
    except (TypeError, ValueError):
        pid = None
    bundle = load_prediction_bundle(pid, race_id)
    block = build_research_world_signals(
        race_id=race_id,
        prediction_id=pid,
        bundle=bundle,
        try_core=try_core,
    )
    payload["research_world_signals"] = block
    return payload


class WorldSignalInstrumentation:
    def __init__(self) -> None:
        migrate()
        self.root = repo_root()
        self.evidence = evidence_root()
        self.reports = self.evidence / "reports"

    def instrument_all_snapshots(self, *, try_core: bool = True, limit: int | None = None) -> dict[str, Any]:
        """Backfill research_world_signals onto existing snapshot payloads."""
        conn = connect()
        updated = 0
        failed = 0
        rows = []
        try:
            sql = """
                SELECT snapshot_id, prediction_id, race_id, payload_json, json_path
                FROM research_prediction_snapshots
                ORDER BY captured_at ASC
            """
            if limit:
                sql += f" LIMIT {int(limit)}"
            rows = conn.execute(sql).fetchall()
        finally:
            conn.close()

        per_key_non_null = {k: 0 for k in SIGNAL_INVENTORY}
        persistence_rates: list[float] = []

        for row in rows:
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except Exception:
                failed += 1
                continue
            attach_world_signals_to_payload(payload, try_core=try_core)
            block = payload.get("research_world_signals") or {}
            signals = block.get("signals") or {}
            for k in SIGNAL_INVENTORY:
                if signals.get(k) is not None:
                    per_key_non_null[k] += 1
            persistence_rates.append(float(block.get("persistence_rate") or 0.0))

            conn = connect()
            try:
                conn.execute(
                    """
                    UPDATE research_prediction_snapshots
                    SET payload_json=?
                    WHERE snapshot_id=?
                    """,
                    (json.dumps(payload, ensure_ascii=False), row["snapshot_id"]),
                )
                conn.commit()
                updated += 1
            except Exception:
                failed += 1
            finally:
                conn.close()

            # best-effort file rewrite
            jp = row["json_path"]
            if jp:
                try:
                    Path(jp).write_text(
                        json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                except OSError:
                    pass

        n = max(updated, 1)
        coverage = {
            k: {"non_null": per_key_non_null[k], "rate": _safe_div(per_key_non_null[k], updated)}
            for k in SIGNAL_INVENTORY
        }
        mean_persist = _safe_div(sum(persistence_rates), len(persistence_rates))
        mean_null = None if mean_persist is None else 1.0 - mean_persist

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "snapshots_seen": len(rows),
            "snapshots_updated": updated,
            "snapshots_failed": failed,
            "inventory": list(SIGNAL_INVENTORY),
            "coverage": coverage,
            "null_rate_mean": mean_null,
            "persistence_rate_mean": mean_persist,
            "product_mutation": False,
            "world_trigger_changed": False,
            "judgment_changed": False,
        }

    def analyze_coverage(self) -> dict[str, Any]:
        """Read-only coverage from already-instrumented snapshots."""
        conn = connect()
        try:
            rows = conn.execute(
                "SELECT payload_json FROM research_prediction_snapshots"
            ).fetchall()
        finally:
            conn.close()
        n = 0
        with_block = 0
        per_key = {k: 0 for k in SIGNAL_INVENTORY}
        persist_rates: list[float] = []
        for row in rows:
            n += 1
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except Exception:
                continue
            block = payload.get("research_world_signals")
            if not isinstance(block, dict):
                continue
            with_block += 1
            signals = block.get("signals") or {}
            for k in SIGNAL_INVENTORY:
                if signals.get(k) is not None:
                    per_key[k] += 1
            if block.get("persistence_rate") is not None:
                persist_rates.append(float(block["persistence_rate"]))
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now(),
            "snapshots_n": n,
            "instrumented_n": with_block,
            "instrumentation_coverage": _safe_div(with_block, n),
            "inventory": list(SIGNAL_INVENTORY),
            "signal_coverage": {
                k: {"non_null": per_key[k], "rate": _safe_div(per_key[k], with_block or n)}
                for k in SIGNAL_INVENTORY
            },
            "null_rate_by_signal": {
                k: 1.0 - (_safe_div(per_key[k], with_block or n) or 0.0)
                for k in SIGNAL_INVENTORY
            },
            "persistence_rate_mean": _safe_div(sum(persist_rates), len(persist_rates)),
            "null_rate_mean": (
                None
                if not persist_rates
                else 1.0 - (_safe_div(sum(persist_rates), len(persist_rates)) or 0.0)
            ),
        }


def write_inventory_md(report: dict[str, Any], coverage: dict[str, Any], path: Path) -> None:
    lines = [
        "# Version25 — World Signal Inventory",
        "",
        f"**Date:** {report.get('generated_at') or coverage.get('generated_at')}  ",
        "**Scope:** Persist only / No World Trigger change / No Prediction change  ",
        "",
        "## Guardrails",
        "",
        f"- product_mutation: `{report.get('product_mutation', False)}`",
        f"- world_trigger_changed: `{report.get('world_trigger_changed', False)}`",
        f"- judgment_changed: `{report.get('judgment_changed', False)}`",
        "",
        "## Signal Inventory",
        "",
        "| Signal | Non-null | Coverage | NULL rate |",
        "|--------|---------:|---------:|----------:|",
    ]
    cov = coverage.get("signal_coverage") or report.get("coverage") or {}
    nulls = coverage.get("null_rate_by_signal") or {}
    for k in SIGNAL_INVENTORY:
        c = cov.get(k) or {}
        nr = nulls.get(k)
        if nr is None and c.get("rate") is not None:
            nr = 1.0 - float(c["rate"])
        lines.append(
            f"| `{k}` | {c.get('non_null')} | {_pct(c.get('rate'))} | {_pct(nr)} |"
        )
    lines += [
        "",
        "## Run summary",
        "",
        f"- Snapshots seen: `{report.get('snapshots_seen')}`",
        f"- Snapshots updated: `{report.get('snapshots_updated')}`",
        f"- Instrumented (coverage scan): `{coverage.get('instrumented_n')}` / `{coverage.get('snapshots_n')}`",
        f"- Mean persistence rate: `{_pct(coverage.get('persistence_rate_mean') or report.get('persistence_rate_mean'))}`",
        f"- Mean NULL rate: `{_pct(coverage.get('null_rate_mean') or report.get('null_rate_mean'))}`",
        "",
        "## Notes",
        "",
        "- Signals are copied into `payload.research_world_signals` on Research Snapshots",
        "- Prediction Bundle product JSON is not rewritten",
        "- Core meta numerics may be copied read-only at harvest; classify outcome is not used to change product",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_coverage_md(report: dict[str, Any], coverage: dict[str, Any], path: Path) -> None:
    lines = [
        "# Version25 — World Signal Coverage / NULL / Persistence",
        "",
        f"**Date:** {coverage.get('generated_at')}  ",
        "",
        "## Coverage",
        "",
        f"- Instrumentation coverage (snapshots with block): "
        f"`{_pct(coverage.get('instrumentation_coverage'))}` "
        f"({coverage.get('instrumented_n')}/{coverage.get('snapshots_n')})",
        f"- Snapshots updated this run: `{report.get('snapshots_updated')}`",
        "",
        "## Persistence rate",
        "",
        f"- Mean persistence rate (non-null / inventory size): "
        f"`{_pct(coverage.get('persistence_rate_mean') or report.get('persistence_rate_mean'))}`",
        "",
        "## NULL rate",
        "",
        f"- Mean NULL rate: `{_pct(coverage.get('null_rate_mean') or report.get('null_rate_mean'))}`",
        "",
        "| Signal | NULL rate |",
        "|--------|----------:|",
    ]
    for k, v in (coverage.get("null_rate_by_signal") or {}).items():
        lines.append(f"| `{k}` | {_pct(v)} |")
    lines += [
        "",
        "## Interpretation",
        "",
        "- High NULL on chaos/difficulty/phase means Core meta copy was unavailable "
        "or Prediction Bundle never carried those fields",
        "- world/sub_world may persist from Bundle labels even when numerics are NULL",
        "- This run does not change World Trigger or Prediction logic",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write(*, try_core: bool = True, limit: int | None = None) -> dict[str, Any]:
    ops = WorldSignalInstrumentation()
    report = ops.instrument_all_snapshots(try_core=try_core, limit=limit)
    coverage = ops.analyze_coverage()
    docs = repo_root() / "docs" / "research"
    docs.mkdir(parents=True, exist_ok=True)
    inv = docs / "v25-world-signal-inventory.md"
    cov = docs / "v25-world-signal-coverage.md"
    write_inventory_md(report, coverage, inv)
    write_coverage_md(report, coverage, cov)
    json_path = evidence_root() / "reports" / "v25-world-signal-instrumentation.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    out = {
        **report,
        "coverage_scan": coverage,
    }
    json_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    out["_outputs"] = {
        "inventory": str(inv),
        "coverage": str(cov),
        "json": str(json_path),
    }
    return out
