# Version29 — World Trigger Lineage (Audit)

**Date:** 2026-07-27T13:34:28+00:00  

## Production Trigger entry

1. `CorePipeline.evaluate`
2. `WorldClassifier.build_race_meta(scored_frame)` → `detect_race_meta`
3. `WorldClassifier.classify_world` → `classify_world_line_type(meta)`

## What Trigger reads (live)

- `meta.race_leg_difficulty` = `0.5`
- `meta.chaos_score` = `None` (missing → nz 0.0)
- resulting CE world = `midupper_world`

## Answer to Q1

Production World Trigger’s difficulty value on the probed race is **`0.5`**, sourced from FeatureGenerator `enrich_stable_features` default **0.5**, not from a Research-only computation.

## Designed vs actual generation

| Path | Invoked on Production Core FG? | Result |
|------|:-----------------------------:|--------|
| `add_win5_leg_difficulty_features` (designed) | No | Would vary with win5_leg/field/pace |
| `enrich_stable_features` default 0.5 | Yes | Constant 0.5 when column absent |

- FG calls enrich: `True`
- FG calls add_win5: `False`
