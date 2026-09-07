# -*- coding: utf-8 -*-
"""
Version26 Chaos / World Signal Trace (Task B) — AUDIT ONLY

Traces chaos_score from generation → Research Snapshot.
Does NOT fix instrumentation, Prediction, Trigger, or Worlds.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .config import evidence_root, repo_root

SCHEMA_VERSION = "expect-chaos-signal-trace/1.0"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def static_chaos_trace() -> dict[str, Any]:
    """Code-level audit map (no product mutation)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now(),
        "audit_only": True,
        "product_mutation": False,
        "stages": [
            {
                "stage": 1,
                "name": "generation",
                "location": "demo_probability_adjustment_logic.py :: build_pace_style_features",
                "variable": "chaos_score (per-horse Series)",
                "formula": (
                    "clip(difficulty*0.24 + pace_collapse_risk_v2*0.24 + "
                    "traffic_score*0.22 + outside_run_score*0.16 + high_pace_score*0.14)"
                ),
                "also_written": [
                    "out['chaos_score'] in pace features DataFrame",
                    "diagnostic['chaos_score'] via apply_grade_distance_style_adjustment",
                    "diagnostic['horse_chaos_fit_score'] = diagnostic['chaos_score']",
                    "diagnostic['world_load_score'] uses chaos_score",
                ],
                "value_present": True,
            },
            {
                "stage": 2,
                "name": "scoring_hold",
                "location": "ai_platform.core.scoring.Scorer.score_candidates",
                "variable": "scores['_diagnostic']['chaos_score']",
                "note": (
                    "chaos lives on _diagnostic DataFrame. "
                    "scores['_source_frame'] is context_frame only — "
                    "chaos_score is NOT merged onto _source_frame."
                ),
                "value_present_on_diagnostic": True,
                "value_present_on_source_frame": False,
            },
            {
                "stage": 3,
                "name": "race_meta",
                "location": (
                    "WorldClassifier.build_race_meta → "
                    "demo_ticket_optimizer_core.detect_race_meta"
                ),
                "variable": "meta['chaos_score']",
                "note": (
                    "detect_race_meta copies race_leg_difficulty / pace_collapse_risk "
                    "from frame but does NOT assign meta['chaos_score'] from frame "
                    "or from diagnostic."
                ),
                "value_present": False,
            },
            {
                "stage": 4,
                "name": "world_judgment_input",
                "location": "demo_ticket_optimizer_core.classify_world_line_type",
                "variable": "chaos = nz(meta.get('chaos_score', 0.0), 0.0)",
                "used_in_triggers": True,
                "thresholds": [
                    "mixed: chaos >= 0.42 (with short_field>=0.72 OR branch)",
                    "rank7: chaos >= 0.58 AND high_pace >= 0.48",
                    "bug: chaos >= 0.66 AND difficulty >= 0.62",
                ],
                "note": (
                    "When meta lacks chaos_score, judgment uses 0.0 via nz default. "
                    "Signal is consumed as numeric 0, not as NULL."
                ),
                "effective_value_when_missing": 0.0,
            },
            {
                "stage": 5,
                "name": "prediction_bundle",
                "location": (
                    "app.engine.adapters.single_prediction_mapper "
                    "(map to single-prediction-bundle)"
                ),
                "fields": [
                    "evaluation.world / sub_world (labels only when filled by product path)",
                    "no chaos_score / meta world-line signals in contract mapping",
                ],
                "bundle_contains_chaos_score": False,
                "value_present": False,
            },
            {
                "stage": 6,
                "name": "research_instrumentation",
                "location": "app.research.world_signal_instrumentation",
                "reads": [
                    "bundle walk for keys chaos / chaos_score",
                    "Core meta.get('chaos_score')",
                    "scored_frame column chaos_score if present",
                ],
                "does_not_read": [
                    "scores['_diagnostic']['chaos_score']",
                ],
                "persists_to": "research_prediction_snapshots.payload_json → research_world_signals.signals",
                "v25_result": "chaos / chaos_score NULL rate 100%",
            },
        ],
        "null_drop_point": {
            "first_loss": (
                "Scorer: chaos stays on _diagnostic; not copied to _source_frame"
            ),
            "confirmed_absent_at": [
                "detect_race_meta output meta",
                "Prediction Bundle JSON",
                "V25 research_world_signals.signals.chaos(_score)",
            ],
            "last_present_point": (
                "apply_grade_distance_style_adjustment → diagnostic['chaos_score'] "
                "(and horse_chaos_fit_score alias)"
            ),
        },
        "keys_read_by_v25": ["chaos", "chaos_score"],
        "keys_generated_upstream": [
            "chaos_score",
            "horse_chaos_fit_score",
            "world_load_score (derived)",
        ],
    }


def live_probe(race_id: str | None = None) -> dict[str, Any]:
    """Optional live Core probe (read-only)."""
    migrate()
    try:
        from app.engine.adapters.single_prediction_mapper import resolve_core_race_id
        from app.research.world_signal_instrumentation import _ensure_research_core_path

        _ensure_research_core_path()
        from ai_platform.core.candidate_evaluation import CorePipeline
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"import:{type(exc).__name__}:{exc}"}

    conn = connect()
    try:
        if race_id:
            row = conn.execute(
                "SELECT race_id, payload_json FROM research_prediction_snapshots WHERE race_id=?",
                (race_id,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT race_id, payload_json FROM research_prediction_snapshots "
                "WHERE race_id LIKE '2026-07-%' ORDER BY captured_at DESC LIMIT 1"
            ).fetchone()
        if not row:
            return {"ok": False, "error": "no_snapshot"}
        rid = str(row["race_id"])
        payload = json.loads(row["payload_json"] or "{}")
        sig = ((payload.get("research_world_signals") or {}).get("signals")) or {}
        brow = conn.execute(
            "SELECT bundle_json FROM predictions WHERE race_id=? ORDER BY id DESC LIMIT 1",
            (rid,),
        ).fetchone()
        bundle = json.loads(brow["bundle_json"] or "{}") if brow else {}
    finally:
        conn.close()

    cid = resolve_core_race_id(rid)
    if not cid:
        return {"ok": False, "race_id": rid, "error": "core_race_id_unresolved"}

    pipe = CorePipeline()
    loaded = pipe.load_race_input(cid)
    if loaded is None:
        return {"ok": False, "race_id": rid, "error": "feature_load_none"}
    fm = pipe.features.build_feature_matrix(loaded.frame)
    scores = pipe.scoring.score_candidates(fm)
    sf = scores["_source_frame"]
    diag = scores.get("_diagnostic")
    sf2 = sf.copy()
    sf2["base_model_score"] = scores["base_model_score"]
    sf2["adjusted_model_score"] = scores["adjusted_model_score"]
    sf2["win_prob"] = scores["win_prob"]
    ranking = pipe.ranking.build_ranking(scores)
    rank = {r["horse_name"]: r["rank"] for r in ranking["ranking"]}
    sf2["model_rank"] = sf2["horse_name"].fillna("").astype(str).map(rank)
    meta = pipe.world.build_race_meta(sf2)

    diag_chaos = None
    if diag is not None and hasattr(diag, "columns") and "chaos_score" in diag.columns:
        diag_chaos = {
            "mean": float(diag["chaos_score"].mean()),
            "max": float(diag["chaos_score"].max()),
            "min": float(diag["chaos_score"].min()),
        }

    return {
        "ok": True,
        "race_id": rid,
        "core_race_id": cid,
        "diagnostic_has_chaos_score": diag_chaos is not None,
        "diagnostic_chaos": diag_chaos,
        "source_frame_has_chaos_score": "chaos_score" in sf.columns,
        "meta_has_chaos_score": "chaos_score" in meta,
        "meta_chaos_score": meta.get("chaos_score"),
        "meta_race_leg_difficulty": meta.get("race_leg_difficulty"),
        "bundle_json_contains_chaos_substring": "chaos" in json.dumps(bundle).lower(),
        "bundle_evaluation_world": (bundle.get("evaluation") or {}).get("world"),
        "research_signals_chaos": sig.get("chaos"),
        "research_signals_chaos_score": sig.get("chaos_score"),
        "last_present_point": (
            "diagnostic['chaos_score']" if diag_chaos is not None else "not_observed"
        ),
        "null_from_here": [
            x
            for x, ok in [
                ("_source_frame", "chaos_score" not in sf.columns),
                ("meta", "chaos_score" not in meta),
                ("bundle", "chaos" not in json.dumps(bundle).lower()),
                ("research_world_signals", sig.get("chaos") is None and sig.get("chaos_score") is None),
            ]
            if ok
        ],
    }


def write_chaos_trace_md(static: dict[str, Any], live: dict[str, Any], path: Path) -> None:
    lines = [
        "# Version26 — Chaos Signal Trace (Audit)",
        "",
        f"**Date:** {static.get('generated_at')}  ",
        "**Mode:** Audit only — no fix / no Prediction / no Trigger / no World change  ",
        "",
        "## Verdict",
        "",
        "`chaos_score` **is generated** during Core scoring diagnostics, then "
        "**dropped before race meta / Bundle / Research Snapshot**. "
        "V25 NULL 100% is therefore an instrumentation path gap, not absence of computation.",
        "",
        "## Pipeline",
        "",
        "```",
        "build_pace_style_features → chaos_score (Series)",
        "        ↓",
        "apply_grade_distance_style_adjustment → diagnostic['chaos_score']  ← LAST PRESENT",
        "        ↓",
        "Scorer._source_frame (context only)  ← DROP (not merged)",
        "        ↓",
        "detect_race_meta(meta)  ← no chaos_score key",
        "        ↓",
        "classify_world_line_type uses nz(meta.chaos_score, 0.0)  ← effective 0.0",
        "        ↓",
        "Prediction Bundle  ← no chaos field",
        "        ↓",
        "V25 research_world_signals  ← chaos NULL",
        "```",
        "",
        "## Checklist",
        "",
        "| Question | Answer |",
        "|----------|--------|",
        "| Where generated? | `demo_probability_adjustment_logic.build_pace_style_features` → `out['chaos_score']` |",
        "| Hold variable names? | `chaos_score`, alias `horse_chaos_fit_score` on diagnostic |",
        "| Used in World judgment? | **Yes** — `classify_world_line_type` reads `meta['chaos_score']` (defaults to 0.0) |",
        "| Saved on Bundle? | **No** |",
        "| Keys V25 reads? | `chaos`, `chaos_score` (bundle walk + meta + frame col) |",
        "| Keys V25 does **not** read? | `scores['_diagnostic']['chaos_score']` |",
        "| NULL location? | From `_source_frame` onward through Research Snapshot |",
        "| Last present point? | `diagnostic['chaos_score']` inside Scorer |",
        "",
        "## Stage detail",
        "",
    ]
    for st in static.get("stages") or []:
        lines.append(f"### Stage {st.get('stage')}: {st.get('name')}")
        lines.append("")
        lines.append(f"- Location: `{st.get('location')}`")
        if st.get("variable"):
            lines.append(f"- Variable: `{st.get('variable')}`")
        if st.get("formula"):
            lines.append(f"- Formula: `{st.get('formula')}`")
        if st.get("note"):
            lines.append(f"- Note: {st.get('note')}")
        lines.append("")
    lines += [
        "## Live probe (EC2 read-only)",
        "",
        f"- ok: `{live.get('ok')}`",
        f"- race_id: `{live.get('race_id')}`",
        f"- diagnostic_has_chaos: `{live.get('diagnostic_has_chaos_score')}` "
        f"`{live.get('diagnostic_chaos')}`",
        f"- source_frame_has_chaos: `{live.get('source_frame_has_chaos_score')}`",
        f"- meta_has_chaos: `{live.get('meta_has_chaos_score')}` value=`{live.get('meta_chaos_score')}`",
        f"- bundle contains 'chaos': `{live.get('bundle_json_contains_chaos_substring')}`",
        f"- research signals chaos: `{live.get('research_signals_chaos')}` / "
        f"`{live.get('research_signals_chaos_score')}`",
        f"- null_from_here: `{live.get('null_from_here')}`",
        f"- last_present_point: `{live.get('last_present_point')}`",
        "",
        "## Guardrails",
        "",
        "- This document does not recommend or apply a product fix",
        "- AI / Prediction / World / Trigger unchanged",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_world_signal_trace_md(static: dict[str, Any], live: dict[str, Any], path: Path) -> None:
    """Broader world-signal path audit (chaos + siblings)."""
    lines = [
        "# Version26 — World Signal Trace (Audit)",
        "",
        f"**Date:** {static.get('generated_at')}  ",
        "**Scope:** World-line signals path Prediction → Research (audit)  ",
        "",
        "## Signal families",
        "",
        "| Signal | Generated in | On diagnostic | On meta via detect_race_meta | On Bundle | V25 persisted |",
        "|--------|--------------|:-------------:|:----------------------------:|:---------:|:-------------:|",
        "| chaos_score | pace features | Yes | No | No | No (NULL 100%) |",
        "| race_leg_difficulty | probability/frame | often | Yes (copied) | No | Yes (~87.7%) |",
        "| pace_collapse_risk | frame | — | Yes | No | Yes (via meta / line score) |",
        "| late_stop / high_pace / phase | calc_world_line_score(meta) | derived | derived scores | No | Yes (often 0.0) |",
        "| short_field_pressure | calc_short_field_pressure(meta) | — | computed at V25 copy | No | Yes |",
        "| world / sub_world | classify_world_line_type | — | CE world fields | evaluation.* | Yes (~96.5%) |",
        "| world_reason | (not a stable Core field) | — | No | No | No (NULL 100%) |",
        "",
        "## Drop taxonomy",
        "",
        "1. **Diagnostic-only drop** (chaos): computed in adjustment diagnostic, never joined to meta",
        "2. **Bundle strip**: Prediction Bundle contract does not carry world-line numerics",
        "3. **Instrumentation miss**: V25 reads meta/frame/bundle, not `_diagnostic`",
        "4. **Default-at-judgment**: classify treats missing chaos as 0.0 — product still runs",
        "",
        "## Relation to V25",
        "",
        "- V25 correctly persisted signals that reached meta or were recomputed by "
        "`calc_world_line_score` / `calc_short_field_pressure`",
        "- V25 could not persist chaos because the value never entered those inputs",
        "- Mean persistence 76.6% with chaos/world_reason as structural NULLs",
        "",
        "## Live probe summary",
        "",
        f"- race: `{live.get('race_id')}`",
        f"- diagnostic chaos: `{live.get('diagnostic_chaos')}`",
        f"- null_from_here: `{live.get('null_from_here')}`",
        "",
        "## Forbidden actions (this version)",
        "",
        "- No AI change",
        "- No Prediction change",
        "- No World / Trigger change",
        "- No new Feature",
        "- Audit documentation only",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write(*, race_id: str | None = None) -> dict[str, Any]:
    static = static_chaos_trace()
    live = live_probe(race_id)
    audit = repo_root() / "docs" / "audit"
    audit.mkdir(parents=True, exist_ok=True)
    chaos_path = audit / "v26-chaos-trace.md"
    signal_path = audit / "v26-world-signal-trace.md"
    write_chaos_trace_md(static, live, chaos_path)
    write_world_signal_trace_md(static, live, signal_path)
    json_path = evidence_root() / "reports" / "v26-chaos-trace.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    out = {"static": static, "live": live, "audit_only": True}
    json_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    out["_outputs"] = {
        "chaos_trace": str(chaos_path),
        "world_signal_trace": str(signal_path),
        "json": str(json_path),
    }
    return out
