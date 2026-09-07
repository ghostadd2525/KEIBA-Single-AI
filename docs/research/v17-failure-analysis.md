# Version17 Research - Failure Analysis

**Date:** 2026-07-27T09:50:55+00:00  
Strict misses: `268` (wins complement `67`)
Evidence among misses: `42`
Slice exploratory: `False`

## Condition composition of misses

| Axis | Segment | Count | Share | Gate |
|------|---------|------:|------:|------|
| `category` | `other` | 151 | 56.3% | CONFIDENT |
| `category` | `stakes` | 81 | 30.2% | CONFIDENT |
| `category` | `3yo_maiden` | 15 | 5.6% | CONFIDENT |
| `category` | `class_1win` | 9 | 3.4% | CONFIDENT |
| `category` | `2yo_newcomer` | 7 | 2.6% | CONFIDENT |
| `category` | `2yo_maiden` | 4 | 1.5% | exploratory |
| `category` | `open` | 1 | 0.4% | exploratory |
| `surface` | `turf` | 173 | 64.6% | CONFIDENT |
| `surface` | `dirt` | 87 | 32.5% | CONFIDENT |
| `distance_bucket` | `mile` | 107 | 39.9% | CONFIDENT |
| `distance_bucket` | `sprint` | 92 | 34.3% | CONFIDENT |
| `distance_bucket` | `middle` | 51 | 19.0% | CONFIDENT |
| `distance_bucket` | `long` | 10 | 3.7% | CONFIDENT |
| `going` | `良` | 204 | 76.1% | CONFIDENT |
| `going` | `稍重` | 31 | 11.6% | CONFIDENT |
| `going` | `重` | 18 | 6.7% | CONFIDENT |
| `going` | `稍` | 4 | 1.5% | exploratory |
| `venue` | `中山` | 50 | 18.7% | CONFIDENT |
| `venue` | `京都` | 45 | 16.8% | CONFIDENT |
| `venue` | `阪神` | 35 | 13.1% | CONFIDENT |
| `venue` | `東京` | 34 | 12.7% | CONFIDENT |
| `venue` | `中京` | 30 | 11.2% | CONFIDENT |
| `venue` | `小倉` | 20 | 7.5% | CONFIDENT |
| `venue` | `新潟` | 19 | 7.1% | CONFIDENT |
| `venue` | `札幌` | 14 | 5.2% | CONFIDENT |
| `venue` | `福島` | 13 | 4.9% | CONFIDENT |
| `venue` | `函館` | 8 | 3.0% | CONFIDENT |
| `field_bucket` | `field_15-16` | 121 | 45.1% | CONFIDENT |
| `field_bucket` | `field_11-14` | 78 | 29.1% | CONFIDENT |
| `field_bucket` | `field_17+` | 36 | 13.4% | CONFIDENT |
| `field_bucket` | `field_<=10` | 33 | 12.3% | CONFIDENT |
| `pick_popularity` | `pop_2-3` | 16 | 6.0% | CONFIDENT |
| `pick_popularity` | `pop_4-6` | 11 | 4.1% | CONFIDENT |
| `pick_popularity` | `pop_1` | 8 | 3.0% | CONFIDENT |
| `pick_popularity` | `pop_7+` | 7 | 2.6% | CONFIDENT |
| `pick_odds` | `odds_mid` | 15 | 5.6% | CONFIDENT |
| `pick_odds` | `odds_short` | 13 | 4.9% | CONFIDENT |
| `pick_odds` | `odds_heavy` | 10 | 3.7% | CONFIDENT |
| `pick_odds` | `odds_long` | 4 | 1.5% | exploratory |

## Sample miss race_ids

`2024-01-21-中山-10`, `2024-01-21-中山-11`, `2024-01-21-京都-10`, `2024-01-21-京都-11`, `2024-01-21-小倉-11`, `2024-01-28-京都-10`, `2024-01-28-京都-11`, `2024-01-28-小倉-11`, `2024-02-04-京都-10`, `2024-02-04-京都-11`, `2024-02-04-小倉-11`, `2024-02-04-東京-11`, `2024-02-11-京都-10`, `2024-02-11-京都-11`, `2024-02-11-小倉-11`

## Note

Failure = Prediction Strict miss. No product mutation from this report.
