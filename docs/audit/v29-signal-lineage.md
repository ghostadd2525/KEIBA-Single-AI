# Version29 — World Signal Lineage (Audit)

**Date:** 2026-07-27T13:34:28+00:00  
**Mode:** Audit only — no Trigger / World / Prediction / AI changes  

## Verdict

**Production World Trigger and Research Snapshot share the same Core meta `race_leg_difficulty` path.** When FeatureLoader omits the column, `enrich_stable_features` fills **0.5** on the Production Core pipeline (not Research-only). V28’s all-0.5 observation is therefore a Production-path default leaking into CE → Trigger → (optional) Research copy.

## End-to-end flow (difficulty)

```
FeatureLoader.load(race_id)
  └─ frame: race_leg_difficulty column usually ABSENT
        ↓
FeatureGenerator.build_feature_matrix
  └─ enrich_stable_features → STABLE_FEATURE_DEFAULTS → 0.5   ← DEFAULT APPLY
        ↓
Scorer / Ranking / Confidence
        ↓
WorldClassifier.build_race_meta → detect_race_meta
  └─ meta['race_leg_difficulty'] = 0.5
        ↓
classify_world_line_type(meta)
  └─ difficulty = nz(meta.race_leg_difficulty, 0.0) = 0.5   ← PRODUCTION TRIGGER
        ↓
CE bundle: world / sub_world (+ meta)
        ↓
Single predict_ranking: DROPS world key
prediction_response_to_bundle: evaluation.world hardcoded None (current mapper)
        ↓
DB predictions.bundle_json may still carry labels from other fill paths
        ↓
V25 research_world_signals.signals.difficulty ← copy of meta (0.5)
```

## Live probe

- ok: `True`
- race / core: `2026-07-26-03-05` / `2026-07-26-03-05`
- loader has race_leg_difficulty: `False`
- after FG unique difficulty: `[0.5]`
- CE meta difficulty: `0.5`
- CE world: `midupper_world` / `midupper_route`
- CE chaos_score: `None`
- predict_ranking has world: `False`
- DB bundle world: `midupper_world` / `midupper_spread`
- research difficulty: `0.5`
- proof: `{'production_trigger_reads_same_meta_difficulty': True, 'difficulty_value_at_trigger': 0.5, 'default_0_5_applies_on_production_core': True, 'research_not_sole_consumer': True}`

## Per-signal lineage summary

### `race_leg_difficulty / difficulty`

```json
{
  "designed_generation": {
    "function": "demo_pace_model_v2.add_win5_leg_difficulty_features",
    "formula": "leg_upset_risk = leg_base_chaos*0.35 + leg_field_pressure*0.20 + pace_collapse_risk*0.20 + style_entropy*0.15 + upset_share*0.10; race_leg_difficulty = mean(leg_upset_risk by race_id)",
    "invoked_by_FeatureGenerator": false
  },
  "production_fill": {
    "function": "demo_probability_feature_utils.enrich_stable_features",
    "called_from": "ai_platform.core.features.FeatureGenerator.build_feature_matrix",
    "default": 0.5,
    "constant": "STABLE_FEATURE_DEFAULTS['race_leg_difficulty']=0.5",
    "scope": "Production Core path (CE / World Trigger) AND any consumer of that meta"
  },
  "meta": {
    "function": "demo_ticket_optimizer_core.detect_race_meta",
    "copy": "meta['race_leg_difficulty'] = frame.race_leg_difficulty.iloc[0]"
  },
  "world_trigger": {
    "function": "demo_ticket_optimizer_core.classify_world_line_type",
    "read": "difficulty = nz(meta.get('race_leg_difficulty', 0.0), 0.0)",
    "used_in_rules": [
      "mixed OR branch (>=0.42)",
      "midupper R2 (>=0.38 with short_field)",
      "bug (>=0.62 with chaos)",
      "midupper R7 (>=0.50 alone)"
    ]
  },
  "prediction_bundle": {
    "numeric_field_persisted": false,
    "label_field": "evaluation.world / sub_world (label only; mapper may set None)"
  },
  "research_snapshot": {
    "key": "research_world_signals.signals.difficulty / race_leg_difficulty",
    "source": "V25 copy from Core meta (same 0.5 when default path)"
  }
}
```

### `leg_base_chaos`

```json
{
  "generation": "demo_pace_model_v2 (win5_leg map; missing→0.50)",
  "on_production_core_frame": "Typically ABSENT unless pace_model_v2 ran",
  "world_trigger_direct_read": false,
  "feeds": "designed leg_upset_risk → race_leg_difficulty (when formula runs)"
}
```

### `leg_field_pressure / field_pressure`

```json
{
  "generation": "demo_pace_model_v2: clip((horse_count-8)/10)",
  "world_trigger_direct_read": false,
  "note": "Not the same as short_field_pressure used by Trigger"
}
```

### `pace_collapse_risk`

```json
{
  "generation": "pace model / frame columns",
  "meta_copy": "detect_race_meta copies pace_collapse_risk",
  "world_trigger": "Indirect via calc_world_line_score → high_pace"
}
```

### `style_entropy`

```json
{
  "generation": "pace/style features",
  "world_trigger_direct_read": false,
  "feeds_designed_difficulty": true
}
```

### `upset_share`

```json
{
  "generation": "pace_model_v2 component of leg_upset_risk",
  "world_trigger_direct_read": false
}
```

### `world_line / world_line_score`

```json
{
  "generation": "calc_world_line_score(meta)",
  "world_trigger": "phase/late_stop/sustained/high_pace derived scores used; type from classify",
  "bundle": "Not persisted as numeric world_line fields"
}
```

### `chaos_score`

```json
{
  "generation": "demo_probability_adjustment_logic.build_pace_style_features → diagnostic",
  "meta": "NOT copied by detect_race_meta",
  "world_trigger": "chaos = nz(meta.get('chaos_score', 0.0), 0.0) → effective 0.0 when missing",
  "research": "NULL in V25 (diagnostic not read)"
}
```

## Guardrails

- product_mutation: `False`
- improvement_forbidden: True
