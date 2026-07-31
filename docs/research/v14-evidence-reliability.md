# Version14 Research - Evidence Reliability

**Date:** 2026-07-27T08:36:40+00:00  
**Scope:** Research only / Reliability not Effect / Prediction+Resolver FORBIDDEN  

## Sample

- Feature rows: `6190`
- Snapshots: `50` / Races: `50`
- Exploratory: `True`

## Reliability Score (0-100)

| Rank | Feature | Score | Coverage | Availability | Missing | SelBias | TempBias | LeakRisk | Stability | Drift |
|-----:|---------|------:|---------:|-------------:|--------:|--------:|---------:|---------:|----------:|------:|
| 1 | `Popularity` | 75.4 | 100.0% | 100.0% | 0.0% | 0.0 | 0.9 | 0.7 | 0.9998 | 0.0 |
| 2 | `Breeder` | 75.3 | 100.0% | 100.0% | 0.0% | 0.0 | 0.9 | 0.7 | 1.0 | 0.0 |
| 3 | `Damsire` | 74.9 | 100.0% | 100.0% | 0.0% | 0.0 | 0.9 | 0.7 | 1.0 | 0.0 |
| 4 | `Sire` | 74.5 | 100.0% | 100.0% | 0.0% | 0.0 | 0.9 | 0.7 | 1.0 | 0.0 |
| 5 | `Owner` | 74.2 | 100.0% | 100.0% | 0.0% | 0.0 | 0.9 | 0.7 | 1.0 | 0.0 |
| 6 | `Trainer` | 73.9 | 100.0% | 100.0% | 0.0% | 0.0 | 0.9 | 0.7 | 1.0 | 0.0 |
| 7 | `Odds` | 65.8 | 100.0% | 100.0% | 0.0% | 0.4639 | 0.9 | 0.7 | 0.9505 | 0.0 |
| 8 | `SalePrice` | 56.9 | 32.0% | 100.0% | 68.0% | 0.1345 | 0.9217 | 0.7 | 0.9885 | 0.0723 |
| 9 | `WorkoutTime` | 52.7 | 17.1% | 72.0% | 82.9% | 0.11 | 0.9013 | 0.7 | 0.9789 | 0.0044 |
| 10 | `WorkoutRating` | 51.9 | 17.1% | 72.0% | 82.9% | 0.11 | 0.9013 | 0.7 | 0.9956 | 0.0044 |

## Score formula (research)

```
100 * (
  0.22*Coverage + 0.13*Availability
  + 0.15*(1-SelectionBias) + 0.10*(1-TemporalBias)
  + 0.20*(1-LeakRisk) + 0.08*(1-VariancePenalty)
  + 0.07*Stability + 0.05*(1-WeeklyDrift)
)
```

## Archetype reweight (top)

| Rank | Archetype | N | MeanFeatRel | Weight | WeightedScore | Win | ROI |
|-----:|-----------|--:|------------:|-------:|--------------:|----:|----:|
| 1 | `oikiri_rating=WK_B + sire=SIRE_MID` | 6 | 63.2 | 0.632 | 0.324638 | 50.0% | 216.0% |
| 2 | `oikiri_rating=WK_B + owner=OWNER_WEAK` | 8 | 63.0 | 0.6305 | 0.312413 | 50.0% | 205.0% |
| 3 | `popularity=P1 + sire=SIRE_WEAK` | 16 | 75.0 | 0.7495 | 0.266635 | 43.8% | 7.5% |
| 4 | `Market Favorite (P1)` | 31 | 75.4 | 0.754 | 0.236558 | 32.3% | -21.9% |
| 5 | `owner=OWNER_STRONG + popularity=P1` | 6 | 74.8 | 0.748 | 0.234623 | 50.0% | 0.0% |
| 6 | `Strong Trainer + Market Top3` | 19 | 74.7 | 0.7465 | 0.229465 | 26.3% | 13.1% |
| 7 | `trainer=TRAINER_STRONG + win_odds=O_SHORT` | 9 | 69.8 | 0.6985 | 0.227432 | 44.4% | 18.9% |
| 8 | `popularity=P1 + trainer=TRAINER_STRONG` | 7 | 74.7 | 0.7465 | 0.227085 | 42.9% | 17.1% |
| 9 | `Favorite + Short Odds` | 31 | 70.6 | 0.706 | 0.221498 | 32.3% | -21.9% |
| 10 | `Short Odds` | 52 | 65.8 | 0.658 | 0.22067 | 32.7% | -21.9% |
| 11 | `breeder=BREEDER_MID + popularity=P1` | 6 | 75.3 | 0.7535 | 0.209976 | 50.0% | 6.7% |
| 12 | `oikiri_rating=WK_B + win_odds=O_SHORT` | 6 | 58.8 | 0.5885 | 0.198815 | 50.0% | -17.5% |
| 13 | `Market Contender (P2-3)` | 62 | 75.4 | 0.754 | 0.198569 | 19.4% | -26.8% |
| 14 | `owner=OWNER_STRONG + win_odds=O_SHORT` | 7 | 70.0 | 0.7 | 0.19094 | 42.9% | -14.3% |
| 15 | `Favorite/Contender + Workout A/B` | 9 | 63.7 | 0.6365 | 0.180091 | 33.3% | -52.9% |

## Decision

```
Action Type: Evidence Reliability Research
Prediction Mutation: FORBIDDEN
Resolver Mutation: FORBIDDEN
Young Horse Score: NOT CREATED
```
