# Version17 Research - Feature Interactions

**Date:** 2026-07-27T09:50:55+00:00  

## Cascade 2-feature (Tie groups)

| Pair | Eligible | Resolved | HitRate | LiftVsSolo | Gate |
|------|---------:|---------:|--------:|-----------:|------|
| `Trainer × Breeder` | 9 | 9 | 22.2% | 0 | exploratory |
| `Popularity × Sire` | 9 | 9 | 11.1% | 0 | exploratory |
| `Popularity × Trainer` | 9 | 9 | 11.1% | -1 | exploratory |
| `Popularity × Win Odds` | 9 | 9 | 11.1% | 0 | exploratory |
| `WorkoutRating × Popularity` | 9 | 9 | 11.1% | 0 | exploratory |
| `Owner × Sire` | 9 | 9 | 11.1% | 0 | exploratory |
| `Sire × Trainer` | 9 | 9 | 0.0% | -2 | exploratory |
| `Damsire × Sire` | 9 | 8 | 0.0% | 0 | exploratory |

## Mined 2-feature patterns (winner bins)

| Pattern | N | Wins | WinRate | Gate |
|---------|--:|-----:|--------:|------|
| `popularity=P1|sire=SIRE_WEAK` | 35 | 14 | 40.0% | CONFIDENT |
| `popularity=P1|trainer=TRAINER_MID` | 20 | 8 | 40.0% | CONFIDENT |
| `popularity=P1|surface=turf` | 23 | 9 | 39.1% | CONFIDENT |
| `popularity=P2-3|surface=dirt` | 30 | 9 | 30.0% | CONFIDENT |
| `popularity=P1|trainer=TRAINER_WEAK` | 21 | 6 | 28.6% | CONFIDENT |
| `popularity=P2-3|distance_bucket=sprint` | 30 | 7 | 23.3% | CONFIDENT |
| `popularity=P2-3|trainer=TRAINER_WEAK` | 46 | 10 | 21.7% | CONFIDENT |
| `popularity=P2-3|sire=SIRE_MID` | 30 | 6 | 20.0% | CONFIDENT |
| `popularity=P2-3|sire=SIRE_WEAK` | 65 | 12 | 18.5% | CONFIDENT |
| `popularity=P2-3|trainer=TRAINER_MID` | 38 | 7 | 18.4% | CONFIDENT |
| `sire=SIRE_MID|trainer=TRAINER_WEAK` | 87 | 13 | 14.9% | CONFIDENT |
| `popularity=P1|distance_bucket=middle` | 3 | 2 | 66.7% | exploratory |
| `oikiri_rating=WK_B|popularity=P2-3` | 8 | 4 | 50.0% | exploratory |
| `oikiri_rating=WK_CDE|popularity=P1` | 5 | 2 | 40.0% | exploratory |
| `popularity=P1|distance_bucket=mile` | 19 | 7 | 36.8% | exploratory |
| `popularity=P4-6|distance_bucket=long` | 3 | 1 | 33.3% | exploratory |
| `oikiri_rating=WK_CDE|popularity=P2-3` | 7 | 2 | 28.6% | exploratory |
| `popularity=P1|distance_bucket=sprint` | 15 | 4 | 26.7% | exploratory |
| `popularity=P1|surface=dirt` | 15 | 4 | 26.7% | exploratory |
| `popularity=P1|distance_bucket=unknown` | 12 | 3 | 25.0% | exploratory |
| `popularity=P1|surface=unknown` | 12 | 3 | 25.0% | exploratory |
| `popularity=P1|trainer=TRAINER_STRONG` | 9 | 2 | 22.2% | exploratory |
| `popularity=P2-3|distance_bucket=unknown` | 24 | 4 | 16.7% | exploratory |
| `popularity=P2-3|surface=unknown` | 24 | 4 | 16.7% | exploratory |
| `popularity=P2-3|distance_bucket=middle` | 6 | 1 | 16.7% | exploratory |

## Mined 3-feature patterns

| Pattern | N | Wins | WinRate | Gate |
|---------|--:|-----:|--------:|------|
| `popularity=P2-3|sire=SIRE_WEAK|trainer=TRAINER_MID` | 25 | 6 | 24.0% | CONFIDENT |
| `popularity=P4-6|sire=SIRE_MID|trainer=TRAINER_WEAK` | 28 | 6 | 21.4% | CONFIDENT |
| `popularity=P2-3|oikiri_rating=WK_B|sire=SIRE_WEAK` | 3 | 2 | 66.7% | exploratory |
| `popularity=P1|surface=turf|distance_bucket=middle` | 3 | 2 | 66.7% | exploratory |
| `popularity=P1|sire=SIRE_WEAK|trainer=TRAINER_MID` | 15 | 7 | 46.7% | exploratory |
| `popularity=P2-3|oikiri_rating=WK_B|sire=SIRE_MID` | 5 | 2 | 40.0% | exploratory |
| `popularity=P1|oikiri_rating=WK_CDE|sire=SIRE_WEAK` | 5 | 2 | 40.0% | exploratory |
| `popularity=P1|sire=SIRE_WEAK|trainer=TRAINER_STRONG` | 5 | 2 | 40.0% | exploratory |
| `popularity=P1|surface=turf|distance_bucket=sprint` | 8 | 3 | 37.5% | exploratory |
| `popularity=P1|surface=dirt|distance_bucket=mile` | 8 | 3 | 37.5% | exploratory |
| `popularity=P1|surface=turf|distance_bucket=mile` | 11 | 4 | 36.4% | exploratory |
| `popularity=P2-3|surface=dirt|distance_bucket=sprint` | 14 | 5 | 35.7% | exploratory |
| `popularity=P1|sire=SIRE_WEAK|trainer=TRAINER_WEAK` | 15 | 5 | 33.3% | exploratory |
| `popularity=P4-6|surface=turf|distance_bucket=long` | 3 | 1 | 33.3% | exploratory |
| `popularity=P2-3|sire=SIRE_MID|trainer=TRAINER_WEAK` | 16 | 5 | 31.2% | exploratory |
| `popularity=P2-3|oikiri_rating=WK_CDE|sire=SIRE_WEAK` | 7 | 2 | 28.6% | exploratory |
| `popularity=P2-3|surface=dirt|distance_bucket=mile` | 16 | 4 | 25.0% | exploratory |
| `popularity=P1|surface=unknown|distance_bucket=unknown` | 12 | 3 | 25.0% | exploratory |
| `popularity=P1|sire=SIRE_MID|trainer=TRAINER_WEAK` | 5 | 1 | 20.0% | exploratory |
| `popularity=P1|sire=SIRE_MID|trainer=TRAINER_MID` | 5 | 1 | 20.0% | exploratory |
| `popularity=P2-3|sire=SIRE_WEAK|trainer=TRAINER_WEAK` | 28 | 5 | 17.9% | exploratory |
| `popularity=P2-3|surface=unknown|distance_bucket=unknown` | 24 | 4 | 16.7% | exploratory |
| `popularity=P4-6|oikiri_rating=WK_B|sire=SIRE_MID` | 6 | 1 | 16.7% | exploratory |
| `popularity=P2-3|surface=turf|distance_bucket=middle` | 6 | 1 | 16.7% | exploratory |
| `popularity=P1|surface=dirt|distance_bucket=sprint` | 7 | 1 | 14.3% | exploratory |
