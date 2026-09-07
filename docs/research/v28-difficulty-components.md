# Version28 — Difficulty Components

**Date:** 2026-07-27T13:20:11+00:00  

## Designed formula (read-only)

- Source: `demo_pace_model_v2.add_win5_leg_difficulty_features`
- Aggregation: `race_leg_difficulty = mean(leg_upset_risk) by race_id`

```
leg_upset_risk =
    leg_base_chaos      * 0.35
  + leg_field_pressure  * 0.20
  + pace_collapse_risk  * 0.20
  + style_entropy       * 0.15
  + upset_share         * 0.10
race_leg_difficulty = mean(leg_upset_risk) by race_id
```

- Stable default when column missing: `0.5`
- Default source: `demo_probability_feature_utils.STABLE_FEATURE_DEFAULTS`

## Designed weight / contribution share

| Component | Weight | Share | Inputs |
|-----------|-------:|------:|--------|
| `leg_base_chaos` | 0.35 | 35.0% | win5_leg |
| `leg_field_pressure` | 0.2 | 20.0% | horse_count, field_size, race_id count |
| `pace_collapse_risk` | 0.2 | 20.0% | nige_count, front_count, horse_count |
| `style_entropy` | 0.15 | 15.0% | running_style counts |
| `upset_share` | 0.1 | 10.0% | sashi_count, oikomi_count, unknown_count, horse_count |

## Empirical contribution share (live reconstruction mean)

| Component | Mean share of reconstructed total |
|-----------|----------------------------------:|
| `leg_base_chaos` | 0.593253 |
| `leg_field_pressure` | 0.236004 |
| `pace_collapse_risk` | 0.0 |
| `style_entropy` | 0.0 |
| `upset_share` | 0.170744 |

## Live frame probe

- ok: `True`
- probed_n: `15`
- frame has race_leg_difficulty: `0`
- frame missing col: `15`
- flags: `{}`
- note: Core FeatureLoader path does not call add_win5_leg_difficulty_features; STABLE_FEATURE_DEFAULTS.race_leg_difficulty=0.5 fills missing columns.

### Samples

- `2026-07-26-03-05` frame_diff=`None` default0.5=`False` recon=`0.315` gap=`None`
  - component cols present: ['win5_leg', 'field_size', 'sashi_count', 'oikomi_count']
- `2026-07-26-03-04` frame_diff=`None` default0.5=`False` recon=`0.298636` gap=`None`
  - component cols present: ['win5_leg', 'field_size', 'sashi_count', 'oikomi_count']
- `2026-07-26-02-05` frame_diff=`None` default0.5=`False` recon=`0.37875` gap=`None`
  - component cols present: ['win5_leg', 'field_size', 'sashi_count', 'oikomi_count']
- `2026-07-26-01-05` frame_diff=`None` default0.5=`False` recon=`0.375` gap=`None`
  - component cols present: ['win5_leg', 'field_size', 'sashi_count', 'oikomi_count']
- `2026-07-25-03-12` frame_diff=`None` default0.5=`False` recon=`0.289545` gap=`None`
  - component cols present: ['win5_leg', 'field_size', 'sashi_count', 'oikomi_count']
- `2026-07-25-03-11` frame_diff=`None` default0.5=`False` recon=`0.288333` gap=`None`
  - component cols present: ['win5_leg', 'field_size', 'sashi_count', 'oikomi_count']
- `2026-07-25-03-10` frame_diff=`None` default0.5=`False` recon=`0.271364` gap=`None`
  - component cols present: ['win5_leg', 'field_size', 'sashi_count', 'oikomi_count']
- `2026-07-25-03-09` frame_diff=`None` default0.5=`False` recon=`0.235` gap=`None`
  - component cols present: ['win5_leg', 'field_size', 'sashi_count', 'oikomi_count']
- `2026-07-25-03-08` frame_diff=`None` default0.5=`False` recon=`0.296667` gap=`None`
  - component cols present: ['win5_leg', 'field_size', 'sashi_count', 'oikomi_count']
- `2026-07-25-03-07` frame_diff=`None` default0.5=`False` recon=`0.335` gap=`None`
  - component cols present: ['win5_leg', 'field_size', 'sashi_count', 'oikomi_count']

## Guardrails

- Reconstruction is observational; product formula/path unchanged
