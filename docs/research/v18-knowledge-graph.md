# Version18 Research - Knowledge Graph

**Date:** 2026-07-27T09:59:03+00:00  
**Week:** `2026-W31`  

## Graph summary

- Nodes: `572`
- Edges: `1391`
- Features: `15`
- Segments: `43`
- Interactions: `168`
- Evidence nodes: `346`

## Structure

```
Feature → Segment → Interaction → Evidence
```

## Feature nodes

- `feature:breeder` — Breeder
- `feature:damsire` — Damsire
- `feature:distance_bucket` — Distance
- `feature:field_bucket` — Field Size
- `feature:going` — Going
- `feature:owner` — Owner
- `feature:popularity` — Popularity
- `feature:sire` — Sire
- `feature:surface` — Surface
- `feature:trainer` — Trainer
- `feature:venue` — Venue
- `feature:weather` — Weather
- `feature:win_odds` — Win Odds
- `feature:oikiri_rating` — WorkoutRating
- `feature:oikiri_time` — WorkoutTime

## Segment nodes

- `segment:2yo_maiden` — 2yo_maiden
- `segment:2yo_newcomer` — 2yo_newcomer
- `segment:3yo_maiden` — 3yo_maiden
- `segment:class_1win` — class_1win
- `segment:dirt` — dirt
- `segment:field_11-14` — field_11-14
- `segment:field_15-16` — field_15-16
- `segment:field_17+` — field_17+
- `segment:field_<=10` — field_<=10
- `segment:long` — long
- `segment:middle` — middle
- `segment:mile` — mile
- `segment:odds_heavy` — odds_heavy
- `segment:odds_long` — odds_long
- `segment:odds_mid` — odds_mid
- `segment:odds_short` — odds_short
- `segment:open` — open
- `segment:other` — other
- `segment:pop_1` — pop_1
- `segment:pop_2-3` — pop_2-3
- `segment:pop_4-6` — pop_4-6
- `segment:pop_7+` — pop_7+
- `segment:sprint` — sprint
- `segment:stakes` — stakes
- `segment:turf` — turf

## Interaction nodes (top)

- `interaction:trainer×breeder`
- `interaction:popularity×sire`
- `interaction:popularity×trainer`
- `interaction:popularity×win_odds`
- `interaction:oikiri_rating×popularity`
- `interaction:owner×sire`
- `interaction:sire×trainer`
- `interaction:damsire×sire`
- `interaction:popularity=P1|sire=SIRE_WEAK`
- `interaction:popularity=P1|trainer=TRAINER_MID`
- `interaction:popularity=P1|surface=turf`
- `interaction:popularity=P2-3|surface=dirt`
- `interaction:popularity=P1|trainer=TRAINER_WEAK`
- `interaction:popularity=P2-3|distance_bucket=sprint`
- `interaction:popularity=P2-3|trainer=TRAINER_WEAK`
- `interaction:popularity=P2-3|sire=SIRE_MID`
- `interaction:popularity=P2-3|sire=SIRE_WEAK`
- `interaction:popularity=P2-3|trainer=TRAINER_MID`
- `interaction:sire=SIRE_MID|trainer=TRAINER_WEAK`
- `interaction:popularity=P1|distance_bucket=middle`

## Edge relations

| From | To | Relation |
|------|----|----------|
| `feature:breeder` | `segment:2yo_maiden` | conditions |
| `feature:breeder` | `segment:2yo_newcomer` | conditions |
| `feature:breeder` | `segment:3yo_maiden` | conditions |
| `feature:breeder` | `segment:class_1win` | conditions |
| `feature:breeder` | `segment:open` | conditions |
| `feature:breeder` | `segment:other` | conditions |
| `feature:breeder` | `segment:stakes` | conditions |
| `feature:breeder` | `kb-06f91dbe4836` | supports |
| `feature:breeder` | `kb-203acbda8a2a` | supports |
| `feature:breeder` | `kb-24d3f963f095` | supports |
| `feature:breeder` | `kb-3dc125582cbb` | supports |
| `feature:breeder` | `kb-64fc7eef066a` | supports |
| `feature:breeder` | `kb-9409c90a4403` | supports |
| `feature:breeder` | `kb-9cea4010f710` | supports |
| `feature:breeder` | `kb-acf5546b525c` | supports |
| `feature:breeder` | `kb-eef265a0ca33` | supports |
| `feature:damsire` | `segment:2yo_maiden` | conditions |
| `feature:damsire` | `segment:2yo_newcomer` | conditions |
| `feature:damsire` | `segment:3yo_maiden` | conditions |
| `feature:damsire` | `segment:class_1win` | conditions |
| `feature:damsire` | `segment:open` | conditions |
| `feature:damsire` | `segment:other` | conditions |
| `feature:damsire` | `segment:stakes` | conditions |
| `feature:damsire` | `kb-2d495b9d17c7` | supports |
| `feature:damsire` | `kb-4e8627cb6d3d` | supports |
| `feature:damsire` | `kb-5e8c2b751c21` | supports |
| `feature:damsire` | `kb-635280739ed9` | supports |
| `feature:damsire` | `kb-8f0c5a623d44` | supports |
| `feature:damsire` | `kb-a381d3360c71` | supports |
| `feature:damsire` | `kb-c255c107286d` | supports |
| `feature:damsire` | `kb-cd1770f1d2b9` | supports |
| `feature:damsire` | `kb-ea2de533d8f4` | supports |
| `feature:distance_bucket` | `interaction:popularity=P1|distance_bucket=middle` | combines |
| `feature:distance_bucket` | `interaction:popularity=P1|distance_bucket=mile` | combines |
| `feature:distance_bucket` | `interaction:popularity=P1|distance_bucket=sprint` | combines |
| `feature:distance_bucket` | `interaction:popularity=P1|distance_bucket=unknown` | combines |
| `feature:distance_bucket` | `interaction:popularity=P1|surface=dirt|distance_bucket=mile` | combines |
| `feature:distance_bucket` | `interaction:popularity=P1|surface=dirt|distance_bucket=sprint` | combines |
| `feature:distance_bucket` | `interaction:popularity=P1|surface=turf|distance_bucket=long` | combines |
| `feature:distance_bucket` | `interaction:popularity=P1|surface=turf|distance_bucket=middle` | combines |
