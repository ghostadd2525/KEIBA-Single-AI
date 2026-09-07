# Version26 — Chaos Signal Trace (Audit)

**Date:** 2026-07-27T12:25:50+00:00  
**Mode:** Audit only — no fix / no Prediction / no Trigger / no World change  

## Verdict

`chaos_score` **is generated** during Core scoring diagnostics, then **dropped before race meta / Bundle / Research Snapshot**. V25 NULL 100% is therefore an instrumentation path gap, not absence of computation.

## Pipeline

```
build_pace_style_features → chaos_score (Series)
        ↓
apply_grade_distance_style_adjustment → diagnostic['chaos_score']  ← LAST PRESENT
        ↓
Scorer._source_frame (context only)  ← DROP (not merged)
        ↓
detect_race_meta(meta)  ← no chaos_score key
        ↓
classify_world_line_type uses nz(meta.chaos_score, 0.0)  ← effective 0.0
        ↓
Prediction Bundle  ← no chaos field
        ↓
V25 research_world_signals  ← chaos NULL
```

## Checklist

| Question | Answer |
|----------|--------|
| Where generated? | `demo_probability_adjustment_logic.build_pace_style_features` → `out['chaos_score']` |
| Hold variable names? | `chaos_score`, alias `horse_chaos_fit_score` on diagnostic |
| Used in World judgment? | **Yes** — `classify_world_line_type` reads `meta['chaos_score']` (defaults to 0.0) |
| Saved on Bundle? | **No** |
| Keys V25 reads? | `chaos`, `chaos_score` (bundle walk + meta + frame col) |
| Keys V25 does **not** read? | `scores['_diagnostic']['chaos_score']` |
| NULL location? | From `_source_frame` onward through Research Snapshot |
| Last present point? | `diagnostic['chaos_score']` inside Scorer |

## Stage detail

### Stage 1: generation

- Location: `demo_probability_adjustment_logic.py :: build_pace_style_features`
- Variable: `chaos_score (per-horse Series)`
- Formula: `clip(difficulty*0.24 + pace_collapse_risk_v2*0.24 + traffic_score*0.22 + outside_run_score*0.16 + high_pace_score*0.14)`

### Stage 2: scoring_hold

- Location: `ai_platform.core.scoring.Scorer.score_candidates`
- Variable: `scores['_diagnostic']['chaos_score']`
- Note: chaos lives on _diagnostic DataFrame. scores['_source_frame'] is context_frame only — chaos_score is NOT merged onto _source_frame.

### Stage 3: race_meta

- Location: `WorldClassifier.build_race_meta → demo_ticket_optimizer_core.detect_race_meta`
- Variable: `meta['chaos_score']`
- Note: detect_race_meta copies race_leg_difficulty / pace_collapse_risk from frame but does NOT assign meta['chaos_score'] from frame or from diagnostic.

### Stage 4: world_judgment_input

- Location: `demo_ticket_optimizer_core.classify_world_line_type`
- Variable: `chaos = nz(meta.get('chaos_score', 0.0), 0.0)`
- Note: When meta lacks chaos_score, judgment uses 0.0 via nz default. Signal is consumed as numeric 0, not as NULL.

### Stage 5: prediction_bundle

- Location: `app.engine.adapters.single_prediction_mapper (map to single-prediction-bundle)`

### Stage 6: research_instrumentation

- Location: `app.research.world_signal_instrumentation`

## Live probe (EC2 read-only)

- ok: `True`
- race_id: `2026-07-26-03-05`
- diagnostic_has_chaos: `True` `{'mean': 0.19802799999999995, 'max': 0.19802799999999998, 'min': 0.19802799999999998}`
- source_frame_has_chaos: `False`
- meta_has_chaos: `False` value=`None`
- bundle contains 'chaos': `False`
- research signals chaos: `None` / `None`
- null_from_here: `['_source_frame', 'meta', 'bundle', 'research_world_signals']`
- last_present_point: `diagnostic['chaos_score']`

## Guardrails

- This document does not recommend or apply a product fix
- AI / Prediction / World / Trigger unchanged
