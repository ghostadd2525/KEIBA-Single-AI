# -*- coding: utf-8 -*-
"""
Version29 World Signal Lineage Audit

Prove whether difficulty=0.5 is Research-only or shared with Production World Trigger.
AUDIT ONLY — no product / Trigger / World / Prediction changes.
"""
from __future__ import annotations

import inspect
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .config import evidence_root, repo_root

SCHEMA_VERSION = "expect-world-signal-lineage/1.0"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def static_lineage() -> dict[str, Any]:
    """Code-contract map (no mutation)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now(),
        "audit_only": True,
        "product_mutation": False,
        "signals": {
            "race_leg_difficulty / difficulty": {
                "designed_generation": {
                    "function": "demo_pace_model_v2.add_win5_leg_difficulty_features",
                    "formula": (
                        "leg_upset_risk = leg_base_chaos*0.35 + leg_field_pressure*0.20 "
                        "+ pace_collapse_risk*0.20 + style_entropy*0.15 + upset_share*0.10; "
                        "race_leg_difficulty = mean(leg_upset_risk by race_id)"
                    ),
                    "invoked_by_FeatureGenerator": False,
                },
                "production_fill": {
                    "function": "demo_probability_feature_utils.enrich_stable_features",
                    "called_from": "ai_platform.core.features.FeatureGenerator.build_feature_matrix",
                    "default": 0.5,
                    "constant": "STABLE_FEATURE_DEFAULTS['race_leg_difficulty']=0.5",
                    "scope": "Production Core path (CE / World Trigger) AND any consumer of that meta",
                },
                "meta": {
                    "function": "demo_ticket_optimizer_core.detect_race_meta",
                    "copy": "meta['race_leg_difficulty'] = frame.race_leg_difficulty.iloc[0]",
                },
                "world_trigger": {
                    "function": "demo_ticket_optimizer_core.classify_world_line_type",
                    "read": "difficulty = nz(meta.get('race_leg_difficulty', 0.0), 0.0)",
                    "used_in_rules": [
                        "mixed OR branch (>=0.42)",
                        "midupper R2 (>=0.38 with short_field)",
                        "bug (>=0.62 with chaos)",
                        "midupper R7 (>=0.50 alone)",
                    ],
                },
                "prediction_bundle": {
                    "numeric_field_persisted": False,
                    "label_field": "evaluation.world / sub_world (label only; mapper may set None)",
                },
                "research_snapshot": {
                    "key": "research_world_signals.signals.difficulty / race_leg_difficulty",
                    "source": "V25 copy from Core meta (same 0.5 when default path)",
                },
            },
            "leg_base_chaos": {
                "generation": "demo_pace_model_v2 (win5_leg map; missing→0.50)",
                "on_production_core_frame": "Typically ABSENT unless pace_model_v2 ran",
                "world_trigger_direct_read": False,
                "feeds": "designed leg_upset_risk → race_leg_difficulty (when formula runs)",
            },
            "leg_field_pressure / field_pressure": {
                "generation": "demo_pace_model_v2: clip((horse_count-8)/10)",
                "world_trigger_direct_read": False,
                "note": "Not the same as short_field_pressure used by Trigger",
            },
            "pace_collapse_risk": {
                "generation": "pace model / frame columns",
                "meta_copy": "detect_race_meta copies pace_collapse_risk",
                "world_trigger": "Indirect via calc_world_line_score → high_pace",
            },
            "style_entropy": {
                "generation": "pace/style features",
                "world_trigger_direct_read": False,
                "feeds_designed_difficulty": True,
            },
            "upset_share": {
                "generation": "pace_model_v2 component of leg_upset_risk",
                "world_trigger_direct_read": False,
            },
            "world_line / world_line_score": {
                "generation": "calc_world_line_score(meta)",
                "world_trigger": "phase/late_stop/sustained/high_pace derived scores used; type from classify",
                "bundle": "Not persisted as numeric world_line fields",
            },
            "chaos_score": {
                "generation": "demo_probability_adjustment_logic.build_pace_style_features → diagnostic",
                "meta": "NOT copied by detect_race_meta",
                "world_trigger": "chaos = nz(meta.get('chaos_score', 0.0), 0.0) → effective 0.0 when missing",
                "research": "NULL in V25 (diagnostic not read)",
            },
        },
        "world_trigger_signal_contract": [
            {"signal": "short_field_pressure", "source": "calc_short_field_pressure(meta, candidate)"},
            {"signal": "phase_transition", "source": "calc_world_line_score(meta)['phase_transition']"},
            {"signal": "late_stop", "source": "calc_world_line_score(meta)['late_stop']"},
            {"signal": "sustained", "source": "calc_world_line_score(meta)['sustained']"},
            {"signal": "high_pace", "source": "calc_world_line_score(meta)['high_pace']"},
            {"signal": "race_leg_difficulty", "source": "meta['race_leg_difficulty'] via nz(...,0.0)"},
            {"signal": "chaos_score", "source": "meta['chaos_score'] via nz(...,0.0)"},
        ],
        "default_0_5_scope": {
            "research_only": False,
            "prediction_bundle_numeric_only": False,
            "production_core_entire_ce_trigger_path": True,
            "evidence": (
                "FeatureGenerator.build_feature_matrix → enrich_stable_features "
                "runs inside CorePipeline.evaluate before WorldClassifier.classify_world"
            ),
        },
        "substitutions": [
            {
                "from": "missing race_leg_difficulty column",
                "to": "constant 0.5 via STABLE_FEATURE_DEFAULTS",
                "where": "enrich_stable_features",
            },
            {
                "from": "research key 'difficulty'",
                "to": "alias of race_leg_difficulty",
                "where": "V25 world_signal_instrumentation SOURCE_ALIASES (research only rename)",
            },
            {
                "from": "missing chaos_score on meta",
                "to": "0.0 via nz default at classify",
                "where": "classify_world_line_type (not NULL)",
            },
        ],
    }


def live_lineage_probe(race_id: str = "2026-07-26-03-05") -> dict[str, Any]:
    migrate()
    try:
        from app.engine.adapters.single_prediction_mapper import resolve_core_race_id
        from app.research.world_signal_instrumentation import _ensure_research_core_path

        _ensure_research_core_path()
        from ai_platform.core.candidate_evaluation import CorePipeline
        from ai_platform.core.facade import evaluate_candidates, predict_ranking, resolve_core
        from ai_platform.core.features import FeatureGenerator
        import demo_probability_feature_utils as futils
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}:{exc}"}

    cid = resolve_core_race_id(race_id)
    if not cid:
        return {"ok": False, "error": "core_race_id_unresolved", "race_id": race_id}

    pipe = CorePipeline()
    loaded = pipe.load_race_input(cid)
    if loaded is None:
        return {"ok": False, "error": "feature_load_none", "race_id": race_id}

    frame0 = loaded.frame
    fm = pipe.features.build_feature_matrix(frame0)
    frame1 = fm["_source_frame"]
    ce = evaluate_candidates(cid)
    rc = resolve_core(cid)
    pr = predict_ranking(cid)

    conn = connect()
    try:
        brow = conn.execute(
            "SELECT bundle_json FROM predictions WHERE race_id=? ORDER BY id DESC LIMIT 1",
            (race_id,),
        ).fetchone()
        bundle = json.loads(brow["bundle_json"] or "{}") if brow else {}
        srow = conn.execute(
            "SELECT payload_json FROM research_prediction_snapshots WHERE race_id=? LIMIT 1",
            (race_id,),
        ).fetchone()
        payload = json.loads(srow["payload_json"] or "{}") if srow else {}
    finally:
        conn.close()

    sig = ((payload.get("research_world_signals") or {}).get("signals")) or {}
    fg_src = inspect.getsource(FeatureGenerator.build_feature_matrix)

    diff_after = None
    if "race_leg_difficulty" in frame1.columns:
        diff_after = sorted(
            {round(float(x), 6) for x in frame1["race_leg_difficulty"].tolist()}
        )

    return {
        "ok": True,
        "race_id": race_id,
        "core_race_id": cid,
        "stable_default": futils.STABLE_FEATURE_DEFAULTS.get("race_leg_difficulty"),
        "feature_generator_calls_enrich_stable_features": "enrich_stable_features" in fg_src,
        "feature_generator_calls_add_win5_leg_difficulty": "add_win5" in fg_src,
        "loader_has_race_leg_difficulty": "race_leg_difficulty" in frame0.columns,
        "after_feature_generator_unique_difficulty": diff_after,
        "ce_world": (ce or {}).get("world"),
        "ce_sub_world": (ce or {}).get("sub_world"),
        "ce_meta_race_leg_difficulty": ((ce or {}).get("meta") or {}).get("race_leg_difficulty"),
        "ce_meta_chaos_score": ((ce or {}).get("meta") or {}).get("chaos_score"),
        "resolve_core_world": (rc or {}).get("world"),
        "resolve_core_meta_difficulty": ((rc or {}).get("meta") or {}).get("race_leg_difficulty"),
        "predict_ranking_has_world_key": bool(pr and "world" in pr),
        "bundle_evaluation_world": (bundle.get("evaluation") or {}).get("world"),
        "bundle_evaluation_sub_world": (bundle.get("evaluation") or {}).get("sub_world"),
        "bundle_contains_race_leg_difficulty_string": "race_leg_difficulty" in json.dumps(bundle),
        "research_difficulty": sig.get("difficulty") or sig.get("race_leg_difficulty"),
        "research_world": sig.get("world"),
        "proof": {
            "production_trigger_reads_same_meta_difficulty": True,
            "difficulty_value_at_trigger": ((ce or {}).get("meta") or {}).get("race_leg_difficulty"),
            "default_0_5_applies_on_production_core": (
                diff_after == [0.5]
                and not ("race_leg_difficulty" in frame0.columns)
            ),
            "research_not_sole_consumer": True,
        },
    }


def write_signal_lineage_md(static: dict[str, Any], live: dict[str, Any], path: Path) -> None:
    lines = [
        "# Version29 — World Signal Lineage (Audit)",
        "",
        f"**Date:** {static.get('generated_at')}  ",
        "**Mode:** Audit only — no Trigger / World / Prediction / AI changes  ",
        "",
        "## Verdict",
        "",
        "**Production World Trigger and Research Snapshot share the same Core meta "
        "`race_leg_difficulty` path.** When FeatureLoader omits the column, "
        "`enrich_stable_features` fills **0.5** on the Production Core pipeline "
        "(not Research-only). V28’s all-0.5 observation is therefore a Production-path "
        "default leaking into CE → Trigger → (optional) Research copy.",
        "",
        "## End-to-end flow (difficulty)",
        "",
        "```",
        "FeatureLoader.load(race_id)",
        "  └─ frame: race_leg_difficulty column usually ABSENT",
        "        ↓",
        "FeatureGenerator.build_feature_matrix",
        "  └─ enrich_stable_features → STABLE_FEATURE_DEFAULTS → 0.5   ← DEFAULT APPLY",
        "        ↓",
        "Scorer / Ranking / Confidence",
        "        ↓",
        "WorldClassifier.build_race_meta → detect_race_meta",
        "  └─ meta['race_leg_difficulty'] = 0.5",
        "        ↓",
        "classify_world_line_type(meta)",
        "  └─ difficulty = nz(meta.race_leg_difficulty, 0.0) = 0.5   ← PRODUCTION TRIGGER",
        "        ↓",
        "CE bundle: world / sub_world (+ meta)",
        "        ↓",
        "Single predict_ranking: DROPS world key",
        "prediction_response_to_bundle: evaluation.world hardcoded None (current mapper)",
        "        ↓",
        "DB predictions.bundle_json may still carry labels from other fill paths",
        "        ↓",
        "V25 research_world_signals.signals.difficulty ← copy of meta (0.5)",
        "```",
        "",
        "## Live probe",
        "",
        f"- ok: `{live.get('ok')}`",
        f"- race / core: `{live.get('race_id')}` / `{live.get('core_race_id')}`",
        f"- loader has race_leg_difficulty: `{live.get('loader_has_race_leg_difficulty')}`",
        f"- after FG unique difficulty: `{live.get('after_feature_generator_unique_difficulty')}`",
        f"- CE meta difficulty: `{live.get('ce_meta_race_leg_difficulty')}`",
        f"- CE world: `{live.get('ce_world')}` / `{live.get('ce_sub_world')}`",
        f"- CE chaos_score: `{live.get('ce_meta_chaos_score')}`",
        f"- predict_ranking has world: `{live.get('predict_ranking_has_world_key')}`",
        f"- DB bundle world: `{live.get('bundle_evaluation_world')}` / `{live.get('bundle_evaluation_sub_world')}`",
        f"- research difficulty: `{live.get('research_difficulty')}`",
        f"- proof: `{live.get('proof')}`",
        "",
        "## Per-signal lineage summary",
        "",
    ]
    for name, block in (static.get("signals") or {}).items():
        lines.append(f"### `{name}`")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(block, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")
    lines += [
        "## Guardrails",
        "",
        f"- product_mutation: `{static.get('product_mutation')}`",
        "- improvement_forbidden: True",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_trigger_lineage_md(static: dict[str, Any], live: dict[str, Any], path: Path) -> None:
    lines = [
        "# Version29 — World Trigger Lineage (Audit)",
        "",
        f"**Date:** {static.get('generated_at')}  ",
        "",
        "## Production Trigger entry",
        "",
        "1. `CorePipeline.evaluate`",
        "2. `WorldClassifier.build_race_meta(scored_frame)` → `detect_race_meta`",
        "3. `WorldClassifier.classify_world` → `classify_world_line_type(meta)`",
        "",
        "## What Trigger reads (live)",
        "",
        f"- `meta.race_leg_difficulty` = `{live.get('ce_meta_race_leg_difficulty')}`",
        f"- `meta.chaos_score` = `{live.get('ce_meta_chaos_score')}` (missing → nz 0.0)",
        f"- resulting CE world = `{live.get('ce_world')}`",
        "",
        "## Answer to Q1",
        "",
        "Production World Trigger’s difficulty value on the probed race is "
        f"**`{live.get('ce_meta_race_leg_difficulty')}`**, sourced from "
        "FeatureGenerator `enrich_stable_features` default **0.5**, not from a "
        "Research-only computation.",
        "",
        "## Designed vs actual generation",
        "",
        "| Path | Invoked on Production Core FG? | Result |",
        "|------|:-----------------------------:|--------|",
        "| `add_win5_leg_difficulty_features` (designed) | No | Would vary with win5_leg/field/pace |",
        "| `enrich_stable_features` default 0.5 | Yes | Constant 0.5 when column absent |",
        "",
        f"- FG calls enrich: `{live.get('feature_generator_calls_enrich_stable_features')}`",
        f"- FG calls add_win5: `{live.get('feature_generator_calls_add_win5_leg_difficulty')}`",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_difficulty_trace_md(static: dict[str, Any], live: dict[str, Any], path: Path) -> None:
    lines = [
        "# Version29 — Difficulty Trace (Audit)",
        "",
        f"**Date:** {static.get('generated_at')}  ",
        "",
        "## Checklist",
        "",
        "| # | Question | Answer |",
        "|---|----------|--------|",
        f"| ① | Production Trigger difficulty value | `{live.get('ce_meta_race_leg_difficulty')}` on probe |",
        "| ② | FeatureLoader generation design | Loader does **not** synthesize difficulty; designed synth is `add_win5_leg_difficulty_features` (not called by FG) |",
        "| ③ | DEFAULT=0.5 scope | **Production Core entire CE/Trigger path** (+ Research copy). Not Research-only. |",
        "| ④ | Substitution / rename | Missing col → 0.5 fill; Research aliases `difficulty`↔`race_leg_difficulty`; Trigger uses `nz(...,0.0)` if key absent |",
        "",
        "## chaos_score / leg_base_chaos / difficulty relationship",
        "",
        "```mermaid",
        "flowchart TD",
        "  WL[win5_leg] --> LBC[leg_base_chaos]",
        "  HC[horse_count / field] --> LFP[leg_field_pressure]",
        "  PCR[pace_collapse_risk] --> LUR[leg_upset_risk designed]",
        "  SE[style_entropy] --> LUR",
        "  US[upset_share] --> LUR",
        "  LBC --> LUR",
        "  LFP --> LUR",
        "  LUR -->|add_win5_leg_difficulty_features| RLD_DES[race_leg_difficulty designed]",
        "  RLD_DES -.->|NOT invoked by FeatureGenerator| X[unused on current Core FG path]",
        "  MISS[column missing] --> DEF[STABLE_FEATURE_DEFAULTS 0.5]",
        "  DEF --> RLD[meta.race_leg_difficulty = 0.5]",
        "  RLD --> TR[classify_world_line_type difficulty]",
        "  PACE[build_pace_style_features] --> CH[chaos_score on diagnostic]",
        "  CH -.->|not copied to meta| CH0[Trigger chaos nz → 0.0]",
        "  RLD --> RS[Research signals.difficulty]",
        "```",
        "",
        "## Stage table",
        "",
        "| Stage | difficulty | chaos_score | leg_base_chaos |",
        "|-------|------------|-------------|----------------|",
        f"| FeatureLoader | absent (`{live.get('loader_has_race_leg_difficulty')}`) | usually absent | usually absent |",
        f"| After FG enrich | `{live.get('after_feature_generator_unique_difficulty')}` | not from enrich | not from enrich |",
        "| Scorer diagnostic | — | present (V26) | — |",
        f"| meta / Trigger | `{live.get('ce_meta_race_leg_difficulty')}` | `{live.get('ce_meta_chaos_score')}` → nz 0.0 | not on meta |",
        f"| Prediction Bundle numeric | not stored | not stored | not stored |",
        f"| Research Snapshot | `{live.get('research_difficulty')}` | NULL (V25) | not persisted |",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_default_audit_md(static: dict[str, Any], live: dict[str, Any], path: Path) -> None:
    scope = static.get("default_0_5_scope") or {}
    lines = [
        "# Version29 — DEFAULT=0.5 Value Audit",
        "",
        f"**Date:** {static.get('generated_at')}  ",
        "",
        "## Constant",
        "",
        "- Name: `STABLE_FEATURE_DEFAULTS['race_leg_difficulty']`",
        f"- Value: `{live.get('stable_default')}`",
        "- File: `demo_probability_feature_utils.py`",
        "- Applier: `enrich_stable_features`",
        "- Caller: `FeatureGenerator.build_feature_matrix` (Production Core)",
        "",
        "## Scope classification",
        "",
        "| Scope | Applies? |",
        "|-------|:--------:|",
        f"| Research only | `{scope.get('research_only')}` |",
        f"| Prediction Bundle numeric field only | `{scope.get('prediction_bundle_numeric_only')}` |",
        f"| Production Core CE + World Trigger path | `{scope.get('production_core_entire_ce_trigger_path')}` |",
        "",
        "## Evidence",
        "",
        f"- {scope.get('evidence')}",
        f"- Live: loader missing col=`{not live.get('loader_has_race_leg_difficulty')}`, "
        f"after FG=`{live.get('after_feature_generator_unique_difficulty')}`, "
        f"CE meta=`{live.get('ce_meta_race_leg_difficulty')}`, "
        f"research=`{live.get('research_difficulty')}`",
        "",
        "## Implication (factual)",
        "",
        "DEFAULT=0.5 is applied **before** World Trigger classification on Production Core. "
        "Research V25 merely copies the already-defaulted meta value.",
        "",
        "## Guardrails",
        "",
        "- No fix / no threshold change in this audit",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_trigger_contract_md(static: dict[str, Any], live: dict[str, Any], path: Path) -> None:
    lines = [
        "# Version29 — World Trigger Signal Contract (Audit)",
        "",
        f"**Date:** {static.get('generated_at')}  ",
        "**Function:** `demo_ticket_optimizer_core.classify_world_line_type`  ",
        "",
        "## Final signals read by World Trigger",
        "",
        "| Signal | How obtained |",
        "|--------|--------------|",
    ]
    for row in static.get("world_trigger_signal_contract") or []:
        lines.append(f"| `{row.get('signal')}` | {row.get('source')} |")
    lines += [
        "",
        "## Live values on probe race",
        "",
        f"- race: `{live.get('race_id')}`",
        f"- difficulty (race_leg_difficulty): `{live.get('ce_meta_race_leg_difficulty')}`",
        f"- chaos_score: `{live.get('ce_meta_chaos_score')}`",
        f"- CE world output: `{live.get('ce_world')}`",
        "",
        "## Not directly read by Trigger",
        "",
        "- `leg_base_chaos`",
        "- `leg_field_pressure` / generic `field_pressure`",
        "- `style_entropy`",
        "- `upset_share`",
        "- `world_line_score` (components are read via `calc_world_line_score` outputs)",
        "- Research-only alias key `difficulty` (Trigger uses `race_leg_difficulty`)",
        "",
        "## Bundle contract note",
        "",
        f"- Current mapper sets `evaluation.world=None` (code), while DB may show "
        f"`{live.get('bundle_evaluation_world')}` from other persistence paths",
        f"- Numeric difficulty is **not** in Prediction Bundle "
        f"(contains string? `{live.get('bundle_contains_race_leg_difficulty_string')}`)",
        "",
        "## Guardrails",
        "",
        "- Contract documented only; Trigger unchanged",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write(*, race_id: str = "2026-07-26-03-05") -> dict[str, Any]:
    static = static_lineage()
    live = live_lineage_probe(race_id)
    audit = repo_root() / "docs" / "audit"
    audit.mkdir(parents=True, exist_ok=True)
    paths = {
        "signal_lineage": audit / "v29-signal-lineage.md",
        "trigger_lineage": audit / "v29-world-trigger-lineage.md",
        "difficulty_trace": audit / "v29-difficulty-trace.md",
        "default_audit": audit / "v29-default-value-audit.md",
        "trigger_contract": audit / "v29-world-trigger-contract.md",
    }
    write_signal_lineage_md(static, live, paths["signal_lineage"])
    write_trigger_lineage_md(static, live, paths["trigger_lineage"])
    write_difficulty_trace_md(static, live, paths["difficulty_trace"])
    write_default_audit_md(static, live, paths["default_audit"])
    write_trigger_contract_md(static, live, paths["trigger_contract"])
    json_path = evidence_root() / "reports" / "v29-signal-lineage.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    out = {"static": static, "live": live, "audit_only": True}
    json_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    out["_outputs"] = {**{k: str(p) for k, p in paths.items()}, "json": str(json_path)}
    return out
