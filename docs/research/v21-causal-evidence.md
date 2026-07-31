# Version21 Research - Causal Evidence

**Date:** 2026-07-27T10:35:22+00:00  
**Scope:** Feature → Condition → Outcome (associational) / Prediction FORBIDDEN  

## Sample

- Unique races: `335` / Evidence: `50`
- Global Prediction Strict: `16.0%`
- Exploratory: `True`

## Unconditional feature effects (field-best)

| Feature | N | Hit | Soft | ROI | Effect vs Pred | Reliability | Confidence |
|---------|--:|----:|-----:|----:|---------------:|------------:|------------|
| `Popularity` | 50 | 32.0% | 32.0% | -20.0% | 0.16 | 75.4 | High |
| `Win Odds` | 50 | 32.0% | 32.0% | -20.0% | 0.16 | 65.8 | High |
| `Trainer` | 35 | 8.6% | 8.6% | -78.6% | -0.0743 | 73.9 | Medium |
| `Sire` | 36 | 2.8% | 2.8% | -93.1% | -0.1322 | 74.5 | Medium |
| `Damsire` | 36 | 8.3% | 16.7% | -79.2% | -0.0767 | 74.9 | Medium |
| `Breeder` | 35 | 2.9% | 8.6% | -92.9% | -0.1314 | 75.3 | Medium |
| `Owner` | 32 | 9.4% | 15.6% | -76.6% | -0.0663 | 74.2 | Medium |
| `WorkoutRating` | 0 | N/A | N/A | N/A | None | 51.9 | Exploratory |

## Preset causal chains

### Popularity → surface → HIT

- Condition bins: `2`
- Best: `turf` hit=39.1% effect=0.0713 n=23 (Medium)
- Worst: `dirt` hit=26.7% effect=-0.0533 n=15 (Medium)

### Popularity → distance_bucket → HIT

- Condition bins: `4`
- Best: `middle` hit=66.7% effect=0.3467 n=3 (Exploratory)
- Worst: `long` hit=0.0% effect=-0.32 n=1 (Exploratory)

### Popularity → going → ROI

- Condition bins: `3`
- Best: `良` hit=39.4% effect=0.0739 n=33 (Medium)
- Worst: `重` hit=0.0% effect=-0.32 n=1 (Exploratory)

### Trainer → category → HIT

- Condition bins: `6`
- Best: `open` hit=100.0% effect=0.9143 n=1 (Exploratory)
- Worst: `other` hit=0.0% effect=-0.0857 n=4 (Exploratory)

### Sire → debut → HIT

- Condition bins: `2`
- Best: `debut` hit=25.0% effect=0.2222 n=4 (Exploratory)
- Worst: `non_debut` hit=0.0% effect=-0.0278 n=32 (Medium)

### Win Odds → surface → HIT

- Condition bins: `2`
- Best: `turf` hit=39.1% effect=0.0713 n=23 (Medium)
- Worst: `dirt` hit=26.7% effect=-0.0533 n=15 (Medium)

### Sire → surface → HIT

- Condition bins: `2`
- Best: `dirt` hit=9.1% effect=0.0631 n=11 (Medium)
- Worst: `turf` hit=0.0% effect=-0.0278 n=15 (Medium)

### Trainer → going → HIT

- Condition bins: `3`
- Best: `良` hit=13.6% effect=0.0506 n=22 (Medium)
- Worst: `重` hit=0.0% effect=-0.0857 n=1 (Exploratory)

### WorkoutRating → debut → HIT

- Condition bins: `0`
- Best: `None` hit=N/A effect=None n=None (None)
- Worst: `None` hit=N/A effect=None n=None (None)

### Popularity → field_bucket → SOFT

- Condition bins: `4`
- Best: `field_11-14` hit=46.7% effect=0.1467 n=15 (Medium)
- Worst: `field_17+` hit=0.0% effect=-0.32 n=4 (Exploratory)

## Guardrails

- Associational only — not causal proof
- No Prediction / PE / CE / AI / Resolver / Production changes
