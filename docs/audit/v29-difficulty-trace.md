# Version29 — Difficulty Trace (Audit)

**Date:** 2026-07-27T13:34:28+00:00  

## Checklist

| # | Question | Answer |
|---|----------|--------|
| ① | Production Trigger difficulty value | `0.5` on probe |
| ② | FeatureLoader generation design | Loader does **not** synthesize difficulty; designed synth is `add_win5_leg_difficulty_features` (not called by FG) |
| ③ | DEFAULT=0.5 scope | **Production Core entire CE/Trigger path** (+ Research copy). Not Research-only. |
| ④ | Substitution / rename | Missing col → 0.5 fill; Research aliases `difficulty`↔`race_leg_difficulty`; Trigger uses `nz(...,0.0)` if key absent |

## chaos_score / leg_base_chaos / difficulty relationship

```mermaid
flowchart TD
  WL[win5_leg] --> LBC[leg_base_chaos]
  HC[horse_count / field] --> LFP[leg_field_pressure]
  PCR[pace_collapse_risk] --> LUR[leg_upset_risk designed]
  SE[style_entropy] --> LUR
  US[upset_share] --> LUR
  LBC --> LUR
  LFP --> LUR
  LUR -->|add_win5_leg_difficulty_features| RLD_DES[race_leg_difficulty designed]
  RLD_DES -.->|NOT invoked by FeatureGenerator| X[unused on current Core FG path]
  MISS[column missing] --> DEF[STABLE_FEATURE_DEFAULTS 0.5]
  DEF --> RLD[meta.race_leg_difficulty = 0.5]
  RLD --> TR[classify_world_line_type difficulty]
  PACE[build_pace_style_features] --> CH[chaos_score on diagnostic]
  CH -.->|not copied to meta| CH0[Trigger chaos nz → 0.0]
  RLD --> RS[Research signals.difficulty]
```

## Stage table

| Stage | difficulty | chaos_score | leg_base_chaos |
|-------|------------|-------------|----------------|
| FeatureLoader | absent (`False`) | usually absent | usually absent |
| After FG enrich | `[0.5]` | not from enrich | not from enrich |
| Scorer diagnostic | — | present (V26) | — |
| meta / Trigger | `0.5` | `None` → nz 0.0 | not on meta |
| Prediction Bundle numeric | not stored | not stored | not stored |
| Research Snapshot | `0.5` | NULL (V25) | not persisted |
