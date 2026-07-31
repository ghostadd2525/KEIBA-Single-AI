# Version16 Research - Weakness Atlas Delta (vs V15)

**Scope:** Re-generated Weakness Atlas after metadata completion.  

## Sample

- Before (V15): `{"prediction_corpus": 340, "evaluable": 335, "young_horse": 33, "tie": 15, "with_evidence": 55, "with_shadow": 9, "global_strict_rate": 0.2, "global_soft_rate": 0.21791044776119403, "global_roi": -0.05253731343283582, "exploratory": true}`
- After (V16): `{"prediction_corpus": 340, "evaluable": 335, "young_horse": 33, "tie": 15, "with_evidence": 55, "with_shadow": 9, "global_strict_rate": 0.2, "global_soft_rate": 0.21791044776119403, "global_roi": -0.05253731343283582, "exploratory": true}`

## Unknown mass by axis

| Axis | Unknown Before | Unknown After | Δ | Share Before | Share After | Δpp |
|------|---------------:|--------------:|--:|-------------:|------------:|----:|
| `age_group` | 295 | 295 | 0 | 86.8% | 86.8% | 0.0 |
| `class_family` | 230 | 230 | 0 | 67.7% | 67.7% | 0.0 |
| `course_type` | 0 | 12 | 12 | 0.0% | 3.5% | 3.53 |
| `distance_bucket` | 237 | 12 | -225 | 69.7% | 3.5% | -66.18 |
| `field_bucket` | 0 | 0 | 0 | 0.0% | 0.0% | 0.0 |
| `going` | 340 | 17 | -323 | 100.0% | 5.0% | -95.0 |
| `odds_band` | 10 | 10 | 0 | 2.9% | 2.9% | 0.0 |
| `pop_band` | 246 | 246 | 0 | 72.4% | 72.4% | 0.0 |
| `race_class` | 0 | 190 | 190 | 0.0% | 55.9% | 55.88 |
| `race_type` | 230 | 230 | 0 | 67.7% | 67.7% | 0.0 |
| `surface` | 237 | 12 | -225 | 69.7% | 3.5% | -66.18 |
| `venue` | 0 | 0 | 0 | 0.0% | 0.0% | 0.0 |
| `weather` | 340 | 203 | -137 | 100.0% | 59.7% | -40.29 |

## Priority Map Top5 Before

- `odds_band=odds_mid` WI=57.0 P=277.89 Strict=16.2%
- `surface=turf` WI=66.3 P=276.76 Strict=7.8%
- `field_bucket=field_15-16` WI=54.4 P=272.94 Strict=19.3%
- `field_bucket=field_11-14` WI=54.0 P=248.68 Strict=21.2%
- `odds_band=odds_short` WI=51.1 P=244.21 Strict=31.4%

## Priority Map Top5 After

- `course_type=turf` WI=57.9 P=308.2 Strict=15.2%
- `surface=turf` WI=57.9 P=308.2 Strict=15.2%
- `going=良` WI=54.3 P=301.1 Strict=20.0%
- `distance_bucket=sprint` WI=60.1 P=280.84 Strict=13.2%
- `odds_band=odds_mid` WI=57.0 P=277.89 Strict=16.2%

## Decision

```
Action Type: Metadata Completion (Research)
Prediction Mutation: FORBIDDEN
Implementation of product fixes: FORBIDDEN
```
