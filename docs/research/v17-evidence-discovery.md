# Version17 Research - Evidence Discovery

**Date:** 2026-07-27T09:50:55+00:00  
Gate: N>=`20` and Wilson 95% CI lower > baseline

Counts: confident=`15` / exploratory=`161`

## Confident hypotheses

- **[feature_importance]** Popularity field-hit=32.0% on n=50 (evidence races)
- **[feature_importance]** Win Odds field-hit=32.0% on n=50 (evidence races)
- **[interaction_2way]** Pattern popularity=P1|sire=SIRE_WEAK win_rate=40.0% n=35
- **[interaction_2way]** Pattern popularity=P1|trainer=TRAINER_MID win_rate=40.0% n=20
- **[interaction_2way]** Pattern popularity=P1|surface=turf win_rate=39.1% n=23
- **[interaction_2way]** Pattern popularity=P2-3|surface=dirt win_rate=30.0% n=30
- **[interaction_2way]** Pattern popularity=P1|trainer=TRAINER_WEAK win_rate=28.6% n=21
- **[interaction_2way]** Pattern popularity=P2-3|distance_bucket=sprint win_rate=23.3% n=30
- **[interaction_2way]** Pattern popularity=P2-3|trainer=TRAINER_WEAK win_rate=21.7% n=46
- **[interaction_2way]** Pattern popularity=P2-3|sire=SIRE_MID win_rate=20.0% n=30
- **[interaction_2way]** Pattern popularity=P2-3|sire=SIRE_WEAK win_rate=18.5% n=65
- **[interaction_2way]** Pattern popularity=P2-3|trainer=TRAINER_MID win_rate=18.4% n=38
- **[interaction_2way]** Pattern sire=SIRE_MID|trainer=TRAINER_WEAK win_rate=14.9% n=87
- **[interaction_3way]** Pattern popularity=P2-3|sire=SIRE_WEAK|trainer=TRAINER_MID win_rate=24.0% n=25
- **[interaction_3way]** Pattern popularity=P4-6|sire=SIRE_MID|trainer=TRAINER_WEAK win_rate=21.4% n=28

## Exploratory hypotheses (separated)

- [feature_importance] Trainer field-hit=8.6% on n=35 (evidence races) (reason=`ci95_low_not_above_baseline`)
- [feature_importance] Owner field-hit=9.4% on n=32 (evidence races) (reason=`ci95_low_not_above_baseline`)
- [feature_importance] Damsire field-hit=8.3% on n=36 (evidence races) (reason=`ci95_low_not_above_baseline`)
- [feature_importance] Breeder field-hit=2.9% on n=35 (evidence races) (reason=`ci95_low_not_above_baseline`)
- [feature_importance] Sire field-hit=2.8% on n=36 (evidence races) (reason=`ci95_low_not_above_baseline`)
- [feature_importance] WorkoutRating field-hit=N/A on n=0 (evidence races) (reason=`n<20`)
- [feature_importance] WorkoutTime field-hit=N/A on n=0 (evidence races) (reason=`n<20`)
- [interaction_2way] Pattern popularity=P1|distance_bucket=middle win_rate=66.7% n=3 (reason=`n<20`)
- [interaction_2way] Pattern oikiri_rating=WK_B|popularity=P2-3 win_rate=50.0% n=8 (reason=`n<20`)
- [interaction_2way] Pattern oikiri_rating=WK_CDE|popularity=P1 win_rate=40.0% n=5 (reason=`n<20`)
- [interaction_2way] Pattern popularity=P1|distance_bucket=mile win_rate=36.8% n=19 (reason=`n<20`)
- [interaction_2way] Pattern popularity=P4-6|distance_bucket=long win_rate=33.3% n=3 (reason=`n<20`)
- [interaction_2way] Pattern oikiri_rating=WK_CDE|popularity=P2-3 win_rate=28.6% n=7 (reason=`n<20`)
- [interaction_2way] Pattern popularity=P1|distance_bucket=sprint win_rate=26.7% n=15 (reason=`n<20`)
- [interaction_2way] Pattern popularity=P1|surface=dirt win_rate=26.7% n=15 (reason=`n<20`)
- [interaction_2way] Pattern popularity=P1|distance_bucket=unknown win_rate=25.0% n=12 (reason=`n<20`)
- [interaction_2way] Pattern popularity=P1|surface=unknown win_rate=25.0% n=12 (reason=`n<20`)
- [interaction_2way] Pattern popularity=P1|trainer=TRAINER_STRONG win_rate=22.2% n=9 (reason=`n<20`)
- [interaction_2way] Pattern popularity=P2-3|distance_bucket=unknown win_rate=16.7% n=24 (reason=`ci95_low_not_above_baseline`)
- [interaction_2way] Pattern popularity=P2-3|surface=unknown win_rate=16.7% n=24 (reason=`ci95_low_not_above_baseline`)
- [interaction_2way] Pattern popularity=P2-3|distance_bucket=middle win_rate=16.7% n=6 (reason=`n<20`)
- [interaction_2way] Pattern popularity=P2-3|distance_bucket=mile win_rate=15.8% n=38 (reason=`ci95_low_not_above_baseline`)
- [interaction_2way] Pattern popularity=P1|sire=SIRE_MID win_rate=14.3% n=14 (reason=`n<20`)
- [interaction_2way] Pattern popularity=P4-6|sire=SIRE_MID win_rate=14.0% n=43 (reason=`ci95_low_not_above_baseline`)
- [interaction_2way] Pattern popularity=P4-6|distance_bucket=unknown win_rate=13.9% n=36 (reason=`ci95_low_not_above_baseline`)
- [interaction_2way] Pattern popularity=P4-6|surface=unknown win_rate=13.9% n=36 (reason=`ci95_low_not_above_baseline`)
- [interaction_2way] Pattern sire=SIRE_WEAK|trainer=TRAINER_MID win_rate=11.6% n=155 (reason=`ci95_low_not_above_baseline`)
- [interaction_2way] Pattern popularity=P2-3|surface=turf win_rate=10.9% n=46 (reason=`ci95_low_not_above_baseline`)
- [interaction_2way] Pattern sire=SIRE_WEAK|trainer=TRAINER_STRONG win_rate=10.6% n=47 (reason=`ci95_low_not_above_baseline`)
- [interaction_2way] Pattern sire=SIRE_MID|going=unknown win_rate=10.5% n=38 (reason=`ci95_low_not_above_baseline`)
- [interaction_2way] Pattern popularity=P4-6|trainer=TRAINER_WEAK win_rate=9.1% n=77 (reason=`ci95_low_not_above_baseline`)
- [interaction_2way] Pattern sire=SIRE_WEAK|going=良 win_rate=9.0% n=256 (reason=`ci95_low_not_above_baseline`)
- [interaction_2way] Pattern popularity=P4-6|distance_bucket=mile win_rate=8.8% n=57 (reason=`ci95_low_not_above_baseline`)
- [interaction_2way] Pattern popularity=P4-6|surface=turf win_rate=8.7% n=69 (reason=`ci95_low_not_above_baseline`)
- [interaction_2way] Pattern sire=SIRE_WEAK|going=稍 win_rate=8.5% n=47 (reason=`ci95_low_not_above_baseline`)
- [interaction_2way] Pattern oikiri_rating=WK_B|popularity=P4-6 win_rate=8.3% n=12 (reason=`n<20`)
- [interaction_2way] Pattern sire=SIRE_WEAK|going=重 win_rate=8.3% n=12 (reason=`n<20`)
- [interaction_2way] Pattern sire=SIRE_WEAK|going=unknown win_rate=8.2% n=85 (reason=`ci95_low_not_above_baseline`)
- [interaction_2way] Pattern sire=SIRE_MID|going=良 win_rate=7.8% n=129 (reason=`ci95_low_not_above_baseline`)
- [interaction_2way] Pattern popularity=P4-6|trainer=TRAINER_MID win_rate=6.9% n=58 (reason=`ci95_low_not_above_baseline`)

## Improvement candidates (NOT implemented)

These are ticket suggestions only. Do not change Prediction/PE/CE/Resolver.

- Investigate as Research follow-up only; do NOT change Prediction yet. — ref: `Popularity field-hit=32.0% on n=50 (evidence races)`
- Investigate as Research follow-up only; do NOT change Prediction yet. — ref: `Win Odds field-hit=32.0% on n=50 (evidence races)`
- Investigate as Research follow-up only; do NOT change Prediction yet. — ref: `Pattern popularity=P1|sire=SIRE_WEAK win_rate=40.0% n=35`
- Investigate as Research follow-up only; do NOT change Prediction yet. — ref: `Pattern popularity=P1|trainer=TRAINER_MID win_rate=40.0% n=20`
- Investigate as Research follow-up only; do NOT change Prediction yet. — ref: `Pattern popularity=P1|surface=turf win_rate=39.1% n=23`
- Investigate as Research follow-up only; do NOT change Prediction yet. — ref: `Pattern popularity=P2-3|surface=dirt win_rate=30.0% n=30`
- Investigate as Research follow-up only; do NOT change Prediction yet. — ref: `Pattern popularity=P1|trainer=TRAINER_WEAK win_rate=28.6% n=21`
- Investigate as Research follow-up only; do NOT change Prediction yet. — ref: `Pattern popularity=P2-3|distance_bucket=sprint win_rate=23.3% n=30`
- Investigate as Research follow-up only; do NOT change Prediction yet. — ref: `Pattern popularity=P2-3|trainer=TRAINER_WEAK win_rate=21.7% n=46`
- Investigate as Research follow-up only; do NOT change Prediction yet. — ref: `Pattern popularity=P2-3|sire=SIRE_MID win_rate=20.0% n=30`

## Decision

```
Action Type: Evidence Discovery (Research)
Prediction Mutation: FORBIDDEN
PE/CE/AI/Resolver/Shadow Mutation: FORBIDDEN
Implementation of fixes: SEPARATE TICKET
```
