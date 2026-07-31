# Version10.4 Research — Shadow Resolver Simulation

**Date:** 2026-07-27T06:12:00+00:00  
**重要:** Prediction 順位は変更しない。本番 Resolver は未実装。  
**対象:** Tie races only

---

## 0. Strategy 比較

| Rank | Strategy | Strict | Soft | StrictΔ | Resolved | Fallback | 説明 |
|-----:|----------|-------:|-----:|--------:|---------:|---------:|------|
| 1 | `tier_cascade` | 22.2% | 55.6% | +2 (22.2%) | 9 | 0 | Evidence Priority cascade (Tier S→A→B→C by composite) |
| 2 | `single_trainer` | 22.2% | 55.6% | +2 (22.2%) | 6 | 3 | single feature: trainer |
| 3 | `market_cascade` | 11.1% | 55.6% | +1 (11.1%) | 9 | 0 | popularity → win_odds → expected_popularity |
| 4 | `popularity_then_trainer` | 11.1% | 55.6% | +1 (11.1%) | 9 | 0 | popularity → trainer → sire |
| 5 | `oikiri_then_market` | 11.1% | 55.6% | +1 (11.1%) | 9 | 0 | oikiri_rating → oikiri_time → popularity |
| 6 | `single_owner` | 11.1% | 55.6% | +1 (11.1%) | 8 | 1 | single feature: owner |
| 7 | `single_win_odds` | 11.1% | 55.6% | +1 (11.1%) | 9 | 0 | single feature: win_odds |
| 8 | `single_popularity` | 11.1% | 55.6% | +1 (11.1%) | 9 | 0 | single feature: popularity |
| 9 | `single_expected_popularity` | 11.1% | 55.6% | +1 (11.1%) | 9 | 0 | single feature: expected_popularity |
| 10 | `baseline` | 0.0% | 55.6% | +0 (0.0%) | 0 | 0 | model_rank→win_prob→horse_number (no evidence) |
| 11 | `horse_intel` | 0.0% | 55.6% | +0 (0.0%) | 9 | 0 | sire → damsire → breeder → trainer → owner |
| 12 | `single_damsire` | 0.0% | 55.6% | +0 (0.0%) | 8 | 1 | single feature: damsire |
| 13 | `single_sire` | 0.0% | 55.6% | +0 (0.0%) | 7 | 2 | single feature: sire |
| 14 | `single_breeder` | 0.0% | 55.6% | +0 (0.0%) | 7 | 2 | single feature: breeder |

Soft Hit はタイ群所属で決まるため、Resolver では **SoftΔ = 0**（集合は不変）。
評価の主指標は **Strict 改善**（Soft∧¬Strict の回収）。

---

## 1. Evidence Priority Cascade

```
trainer → owner → win_odds → popularity → expected_popularity → damsire → sire → breeder → sale_price → oikiri_time → oikiri_rating
```

Fail-open: 特徴で解けない場合は既存 baseline（馬番タイブレーク）へフォールバック。

---

## 2. 解釈

1. 最良 Shadow 戦略は **`tier_cascade`** （Strict 2/9, Δ +2）。
2. 本番 Prediction Bundle への書き込みは行っていない。
3. 次フェーズで Resolver を実装する場合、本 Priority / Tier を入力契約とする。

```
Resolver Production: NOT IMPLEMENTED (V10.4)
Prediction Mutation: FORBIDDEN
```
