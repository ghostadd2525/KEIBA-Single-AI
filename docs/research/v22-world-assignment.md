# Version22 — Existing World Assignment (Fitness)

**Date:** 2026-07-27T11:30:59+00:00  
**Metric:** World membership fitness (NOT Hit rate)  

## Summary

- Labeled evaluated: `51`
- Natural membership rate: `100.0%`
- Ambiguous rate: `0.0%`
- Mean assigned fitness: `1.0`

_Fitness = soft membership from feature likelihood tables; NOT hit rate. natural_membership = argmax soft == assigned world._

## Assignment Confidence by Feature

| Feature | Mean Δ fitness if dropped | N | Conf |
|---------|--------------------------:|--:|------|
| Popularity | 0.0 | 51 | High |
| Win Odds | 0.0 | 51 | High |
| Trainer | 0.0 | 51 | High |
| Sire | 0.0 | 51 | High |
| Damsire | 0.0 | 51 | High |
| Breeder | 0.0 | 51 | High |
| Owner | 0.0 | 51 | High |
| WorkoutRating | 0.0 | 51 | High |
| Surface | 0.0 | 51 | High |
| Distance | 0.0 | 51 | High |
| Going | 0.0 | 51 | High |
| Weather | 0.0 | 51 | High |
| Field Size | 0.0 | 51 | High |

## Examples

- `2026-07-25-01-01` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-01-02` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-01-03` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-01-04` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-01-05` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-01-06` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-01-07` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-01-08` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-01-09` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-01-10` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-01-11` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-01-12` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-02-01` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-02-02` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-02-03` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-02-04` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-02-05` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-02-06` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-02-07` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-02-08` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-02-09` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-02-10` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-02-11` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-02-12` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False
- `2026-07-25-03-01` assigned=`midupper_world` best_fit=`midupper_world` fit=1.0 margin=1.0 natural=True amb=False

## Guardrails

- Soft membership uses EXISTING world likelihood tables only
- Does not change Prediction / PE / CE / AI assignment in product
