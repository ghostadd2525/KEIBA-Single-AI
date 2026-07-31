# Version12 Research - Young Horse Feature Interactions

**Date:** 2026-07-27T08:18:26+00:00  
**Scope:** Research only / cascade pairs on Tie groups  

## Pairwise Cascade (top)

| A | B | Tie N | ResolveRate | CascadeWR | Lift vs best solo | Avg IG |
|---|---|------:|------------:|----------:|------------------:|-------:|
| `trainer` | `sire` | 9 | 100.0% | 22.2% | 1 | 2.0611940872648042 |
| `trainer` | `oikiri_time` | 9 | 55.6% | 20.0% | 0 | 1.7813781191217035 |
| `trainer` | `oikiri_rating` | 9 | 55.6% | 20.0% | 0 | 1.7813781191217035 |
| `sire` | `oikiri_time` | 9 | 55.6% | 20.0% | 0 | 2.0643856189774725 |
| `sire` | `oikiri_rating` | 9 | 55.6% | 20.0% | 0 | 2.0643856189774725 |
| `sire` | `breeder` | 9 | 77.8% | 14.3% | 0 | 2.137969183523155 |
| `sire` | `damsire` | 9 | 88.9% | 12.5% | 0 | 2.193843348172905 |
| `popularity` | `win_odds` | 9 | 100.0% | 11.1% | 0 | 2.0611940872648042 |
| `popularity` | `trainer` | 9 | 100.0% | 11.1% | 0 | 2.0611940872648042 |
| `popularity` | `sire` | 9 | 100.0% | 11.1% | 0 | 2.0611940872648042 |
| `popularity` | `damsire` | 9 | 100.0% | 11.1% | 0 | 2.0611940872648042 |
| `popularity` | `breeder` | 9 | 100.0% | 11.1% | 0 | 2.0611940872648042 |
| `popularity` | `oikiri_time` | 9 | 100.0% | 11.1% | 0 | 2.0611940872648042 |
| `popularity` | `oikiri_rating` | 9 | 100.0% | 11.1% | 0 | 2.0611940872648042 |
| `win_odds` | `trainer` | 9 | 100.0% | 11.1% | 0 | 2.0611940872648042 |
| `win_odds` | `sire` | 9 | 100.0% | 11.1% | 0 | 2.0611940872648042 |
| `win_odds` | `damsire` | 9 | 100.0% | 11.1% | 0 | 2.0611940872648042 |
| `win_odds` | `breeder` | 9 | 100.0% | 11.1% | 0 | 2.0611940872648042 |
| `win_odds` | `oikiri_time` | 9 | 100.0% | 11.1% | 0 | 2.0611940872648042 |
| `win_odds` | `oikiri_rating` | 9 | 100.0% | 11.1% | 0 | 2.0611940872648042 |
| `trainer` | `damsire` | 9 | 100.0% | 11.1% | 0 | 2.0611940872648042 |
| `trainer` | `breeder` | 9 | 100.0% | 11.1% | 0 | 2.0611940872648042 |
| `damsire` | `breeder` | 9 | 88.9% | 0.0% | 0 | 2.193843348172905 |
| `damsire` | `oikiri_time` | 9 | 88.9% | 0.0% | 0 | 2.193843348172905 |
| `damsire` | `oikiri_rating` | 9 | 88.9% | 0.0% | 0 | 2.193843348172905 |

## Reading

- Cascade applies A then B inside Tie group G.
- Lift = cascade_correct - max(solo_A_correct, solo_B_correct).
- Positive lift suggests complementary interaction (exploratory at low N).
