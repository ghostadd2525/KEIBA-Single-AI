# Version16 Research - Metadata Completion

**Date:** 2026-07-27T08:57:11+00:00  
**Run:** `meta-da4ab1e7ca33`  
**Scope:** Research only / Unknown reduction only / Prediction FORBIDDEN  

## Priority Chain

1. Existing DB (`races`, `race_results`, `race_evaluations`, corpus, historical, snapshots)
2. Existing PI (`*.pi.json`)
3. Baseline fixture (`baseline-285r-evaluations.json` — treated as DB-adjacent offline)
4. Netkeiba result HTML (research client; only when `numeric_race_id` present)
5. JRA — unavailable (no local research provider)

## Coverage Before → After

| Feature | Known Before | Known After | Coverage Before | Coverage After | Δpp |
|---------|-------------:|------------:|----------------:|---------------:|----:|
| `surface` | 100 | 325 | 29.7% | 96.4% | 66.77 |
| `distance` | 100 | 325 | 29.7% | 96.4% | 66.77 |
| `field_size` | 51 | 337 | 15.1% | 100.0% | 84.87 |
| `age_group` | 44 | 44 | 13.1% | 13.1% | 0.0 |
| `weather` | 0 | 135 | 0.0% | 40.1% | 40.06 |
| `going` | 0 | 321 | 0.0% | 95.2% | 95.25 |
| `race_class` | 147 | 147 | 43.6% | 43.6% | 0.0 |
| `course_type` | 100 | 325 | 29.7% | 96.4% | 66.77 |

## Summary

- Races: `337`
- Mean coverage: `20.1%` → `72.7%`
- Baseline fixture rows: `285`
- PI files: `9`
- Netkeiba: `{"enabled": true, "attempted": 40, "filled": 40, "errors": 0, "skipped": 0, "jra_status": "unavailable_no_local_provider"}`
- JRA: `unavailable_no_local_provider`

## Guardrails

- Did not mutate Prediction / PE / CE / AI / Challenge / Resolver / ResultAutomation
- Wrote `research_race_meta` + patched `research_prediction_corpus` columns only
