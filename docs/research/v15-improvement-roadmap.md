# Version15 Research - Improvement Roadmap

**Date:** 2026-07-27T08:44:27+00:00  
**IMPORTANT:** Research roadmap only. No Prediction/Resolver/PE/CE/AI implementation.

| Order | Type | Focus | WI/N | Research Action | Est. Imp ROI (yen) |
|------:|------|-------|-----:|-----------------|-------------------:|
| 1 | `segment_weakness` | `odds_band=odds_mid` | 57.0 | Investigate odds_band=odds_mid losses; collect more Evidence; do NOT change Prediction yet. | 1250.0 |
| 2 | `segment_weakness` | `surface=turf` | 66.3 | Investigate surface=turf losses; collect more Evidence; do NOT change Prediction yet. | 1950.0 |
| 3 | `segment_weakness` | `field_bucket=field_15-16` | 54.4 | Investigate field_bucket=field_15-16 losses; collect more Evidence; do NOT change Prediction yet. | 250.0 |
| 4 | `segment_weakness` | `field_bucket=field_11-14` | 54.0 | Investigate field_bucket=field_11-14 losses; collect more Evidence; do NOT change Prediction yet. | 0.0 |
| 5 | `segment_weakness` | `odds_band=odds_short` | 51.1 | Investigate odds_band=odds_short losses; collect more Evidence; do NOT change Prediction yet. | 0.0 |
| 6 | `segment_weakness` | `race_type=stakes` | 57.7 | Investigate race_type=stakes losses; collect more Evidence; do NOT change Prediction yet. | 250.0 |
| 7 | `segment_weakness` | `class_family=stakes` | 57.7 | Investigate class_family=stakes losses; collect more Evidence; do NOT change Prediction yet. | 250.0 |
| 8 | `segment_weakness` | `venue=京都` | 57.5 | Investigate venue=京都 losses; collect more Evidence; do NOT change Prediction yet. | 450.0 |
| 9 | `data_quality` | `going=unknown` | 340 | Reduce unknown on axis `going` via metadata backfill (Research ingest only). | N/A |
| 10 | `data_quality` | `weather=unknown` | 340 | Reduce unknown on axis `weather` via metadata backfill (Research ingest only). | N/A |
| 11 | `data_quality` | `age_group=unknown` | 295 | Reduce unknown on axis `age_group` via metadata backfill (Research ingest only). | N/A |
| 12 | `data_quality` | `pop_band=unknown` | 246 | Reduce unknown on axis `pop_band` via metadata backfill (Research ingest only). | N/A |
| 13 | `data_quality` | `surface=unknown` | 237 | Reduce unknown on axis `surface` via metadata backfill (Research ingest only). | N/A |
| 14 | `guardrail` | `guardrail` | None | Keep global Strict=20.0% as baseline. No Prediction/Resolver/PE/CE/AI changes in V15. | N/A |

## Guardrails

- Do not change Prediction ranks / PE / CE / AI / Challenge / Resolver / ResultAutomation.
- Improvement ROI estimates are research heuristics (extra hits * illustrative payout).
- Next allowed work: Evidence backfill / metadata enrichment / deeper diagnosis only.
