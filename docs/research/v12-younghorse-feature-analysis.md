# Version12 Research - Young Horse Feature Analysis

**Date:** 2026-07-27T08:18:26+00:00  
**Scope:** Research only / Prediction mutation FORBIDDEN / No Young Horse Score  

## Sample

- Young races with Evidence: `31`
- 2歳新馬 (debut): `7`
- Baseline Strict: `6` (19.4%)
- Baseline Soft: `11` (35.5%)
- Tie races (|G|>=2): `9`
- Exploratory: `True`

### Age breakdown

| Age | Count |
|-----|------:|
| `2yo_maiden` | 5 |
| `2yo_newcomer` | 7 |
| `3yo_maiden` | 19 |

## Solo Feature Effects

| Feature | Coverage | Field WinRate | Tie Resolve | Tie StrictWR | Avg IG |
|---------|---------:|--------------:|------------:|-------------:|-------:|
| `popularity` | 100.0% | 32.3% | 100.0% | 11.1% | 2.0611940872648042 |
| `win_odds` | 100.0% | 32.3% | 100.0% | 11.1% | 2.0611940872648042 |
| `damsire` | 100.0% | 18.2% | 88.9% | 0.0% | 1.9500829761536933 |
| `breeder` | 100.0% | 0.0% | 88.9% | 0.0% | 1.9500829761536933 |
| `sire` | 100.0% | 6.7% | 55.6% | 20.0% | 1.146880899431929 |
| `trainer` | 100.0% | 4.5% | 55.6% | 20.0% | 0.9896545106231687 |
| `oikiri_time` | 17.2% | N/A | 0.0% | N/A | N/A |
| `oikiri_rating` | 17.2% | N/A | 0.0% | N/A | N/A |

## Definitions

- **Field WinRate**: feature-best horse among full field equals Winner
- **Tie Resolve**: unique pick inside model_rank tie group G
- **Tie StrictWR**: resolved pick equals Winner
- **IG**: information gain vs uniform pick in G (bits)
- Categoricals use leave-one-out Laplace prior (research shadow only)

## Decision

```
Action Type: Young Horse Intelligence Research
Young Horse Score: NOT CREATED
Prediction Mutation: FORBIDDEN
Resolver Mutation: FORBIDDEN
```
