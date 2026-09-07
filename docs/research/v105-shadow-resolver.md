# Version10.5 Research — Shadow Tie Resolver

**Date:** 2026-07-27T06:41:11+00:00  
**Input:** Version10.4 Tier Ranking / Evidence Priority  
**重要:** Prediction順位変更禁止 / Production未反映 / Shadow only  

---

## 0. Verdict

| 指標 | 値 |
|------|----|
| Tie races | 9 |
| Baseline Strict | 0 (0.0%) |
| Shadow Strict | 2 (22.2%) |
| Strict Δ | +2 |
| Resolver Win | 2 |
| Resolver Lose | 0 |
| Resolver Draw | 7 |

## 1. Evidence Priority Input

| Priority | Tier | Feature |
|---------:|:----:|---------|
| 1 | S | `trainer` |
| 2 | S | `owner` |
| 3 | S | `win_odds` |
| 4 | S | `popularity` |
| 5 | S | `expected_popularity` |
| 6 | A | `damsire` |
| 7 | A | `sire` |
| 8 | A | `breeder` |
| 9 | B | `sale_price` |
| 10 | C | `oikiri_time` |
| 11 | C | `oikiri_rating` |

## 2. Race Comparison

| Race | Winner | Prediction Pick | Shadow Pick | Outcome | Used Feature | Tier | Shadow Winner Rank |
|------|-------:|----------------:|------------:|---------|--------------|------|-------------------:|
| `2026-07-26-01-02` | 6 | 5 | 6 | win | trainer | S | 1 |
| `2026-07-26-02-01` | 8 | 5 | 5 | draw | trainer | S | 4 |
| `2026-07-26-02-02` | 3 | 5 | 6 | draw | trainer | S | N/A |
| `2026-07-25-01-02` | 12 | 11 | 14 | draw | owner | S | 3 |
| `2026-07-25-01-03` | 4 | 5 | 5 | draw | trainer | S | N/A |
| `2026-07-25-02-01` | 1 | 5 | 7 | draw | owner | S | N/A |
| `2026-07-25-02-02` | 11 | 6 | 7 | draw | owner | S | 6 |
| `2026-07-25-03-05` | 1 | 5 | 6 | draw | trainer | S | N/A |
| `2026-07-26-03-05` | 9 | 5 | 9 | win | trainer | S | 1 |

## 3. Usage

### Feature使用回数

| Feature | Tier | Used |
|---------|:----:|-----:|
| `trainer` | S | 6 |
| `owner` | S | 3 |

### Tier使用回数

| Tier | Used |
|:----:|-----:|
| S | 9 |

### Cascade停止位置

| Stop | Count |
|------|------:|
| `owner` | 3 |
| `trainer` | 6 |

## 4. Decision

```
Action Type: Shadow Tie Resolver
Implementation Required: Shadow only
Deployment Required: Optional research CLI / dashboard
Production Required: No
Prediction Mutation: FORBIDDEN
Adoption Gate: Review ~6 months ROI in Version11
```
