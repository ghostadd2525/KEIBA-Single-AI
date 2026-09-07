# Version10.4 Research — Evidence Ranking Engine

**Date:** 2026-07-27T06:12:00+00:00  
**Type:** Statistical Evidence Priority（Prediction 順位は変更しない）  
**Scope:** Tie races only (`|G| >= 2`)  
**Hard Lock:** PE / CE / AI Score / Prediction Logic / ResultAutomation / Challenge **変更禁止**  
**Resolver:** 本番未実装（Shadow Simulation のみ）

---

## 0. Verdict

| 指標 | 値 |
|------|----|
| 全評価レース | 50 |
| Tie レース（|G|≥2） | **9** |
| Baseline Strict（Tie） | 0/9 |
| Baseline Soft（Tie） | 5/9 |
| Soft∧¬Strict（Tie） | 5 |
| 平均タイ頭数 | 4.556 |

### Evidence Priority（自動生成）

| Priority | Tier | Feature | Score | Soft→Strict | Lift | MI | Perm | Coverage |
|--------:|:----:|---------|------:|------------:|-----:|---:|-----:|---------:|
| 1 | S | `trainer` | 0.478926 | 40.0% | 1.2544 | 0.5349 | 0.1630 | 100.0% |
| 2 | S | `owner` | 0.383592 | 20.0% | 0.4704 | 0.5349 | 0.0444 | 100.0% |
| 3 | S | `win_odds` | 0.315682 | 20.0% | 0.4181 | 0.0912 | -0.0037 | 100.0% |
| 4 | S | `popularity` | 0.315441 | 20.0% | 0.4181 | 0.0860 | 0.0037 | 100.0% |
| 5 | S | `expected_popularity` | 0.314848 | 20.0% | 0.4181 | 0.0860 | -0.0296 | 100.0% |
| 6 | A | `damsire` | 0.273702 | 0.0% | 0.0000 | 0.4190 | -0.0741 | 100.0% |
| 7 | A | `sire` | 0.268174 | 0.0% | 0.0000 | 0.4678 | -0.0815 | 100.0% |
| 8 | A | `breeder` | 0.24126 | 0.0% | 0.0000 | 0.2995 | -0.0926 | 100.0% |
| 9 | B | `sale_price` | 0.21517 | 0.0% | 0.0000 | 0.3949 | N/A | 32.0% |
| 10 | C | `oikiri_time` | 0.017124 | 0.0% | N/A | N/A | N/A | 17.1% |
| 11 | C | `oikiri_rating` | 0.017124 | 0.0% | N/A | N/A | N/A | 17.1% |

- **Tier S:** `trainer`, `owner`, `win_odds`, `popularity`, `expected_popularity`  
- **Tier A:** `damsire`, `sire`, `breeder`  
- **Tier B:** `sale_price`  
- **Tier C:** `oikiri_time`, `oikiri_rating`  

---

## 1. 定義

- **scope**: Tie races only (|G|>=2)
- **coverage**: filled/total cells on complete snapshots
- **tie_resolution_rate**: unique argmax score within G among eligible
- **soft_to_strict_improve_rate**: recovered Soft∧¬Strict / Soft∧¬Strict on tie races
- **information_gain**: mean bits log2(|G|)-log2(remaining) after feature partition
- **mutual_information**: MI(feature_bin_or_category; is_winner) over horses in tie groups
- **permutation_importance**: drop in correct-resolve rate when shuffling feature within G (LOO prior)
- **lift**: P(correct|resolved) / E[1/|G|] on eligible resolved races
- **categorical_ranking**: leave-one-out Laplace win prior P(win|category) excluding eval race
- **tiers**: S/A/B/C from coverage + soft→strict + lift/MI/perm gates
- **shadow_only**: strategies do not write Prediction ranks

### Tier ゲート（統計のみ）

| Tier | 条件 |
|:----:|------|
| S | coverage≥0.9 ∧ Soft→Strict≥0.15 ∧ (lift≥1.2 ∨ MI≥0.02 ∨ perm≥0.05) |
| A | coverage≥0.8 ∧ (Soft→Strict>0 ∨ lift≥1.1 ∨ MI≥0.01 ∨ perm≥0.02) |
| B | coverage≥0.5 ∨ Tie eligible あり |
| C | 上記以外 / 低 Coverage |

---

## 2. Feature Importance 詳細

### `trainer` — Tier S

| 指標 | 値 |
|------|----|
| rank | 1 |
| composite_score | 0.478926 |
| coverage | 100.0% |
| missing_rate | 0.0% |
| tie_eligible | 9 |
| tie_resolution_rate | 66.7% |
| tie_correct | 2 |
| strict_hit | 2 |
| soft_hit | 5 |
| soft_to_strict_improve_rate | 40.0% |
| information_gain_mean | 1.551754 |
| mutual_information | 0.534944 |
| permutation_importance | 0.162963 |
| lift | 1.254355 |
| winner_rank_mean | 4.4444 |
| within_tie_diversity_rate | 1.0 |
| notes | ranked_by_loo_empirical_win_prior |

### `owner` — Tier S

| 指標 | 値 |
|------|----|
| rank | 2 |
| composite_score | 0.383592 |
| coverage | 100.0% |
| missing_rate | 0.0% |
| tie_eligible | 9 |
| tie_resolution_rate | 88.9% |
| tie_correct | 1 |
| strict_hit | 1 |
| soft_hit | 5 |
| soft_to_strict_improve_rate | 20.0% |
| information_gain_mean | 1.950083 |
| mutual_information | 0.534944 |
| permutation_importance | 0.044444 |
| lift | 0.470383 |
| winner_rank_mean | 6.2222 |
| within_tie_diversity_rate | 1.0 |
| notes | ranked_by_loo_empirical_win_prior |

### `win_odds` — Tier S

| 指標 | 値 |
|------|----|
| rank | 3 |
| composite_score | 0.315682 |
| coverage | 100.0% |
| missing_rate | 0.0% |
| tie_eligible | 9 |
| tie_resolution_rate | 100.0% |
| tie_correct | 1 |
| strict_hit | 1 |
| soft_hit | 5 |
| soft_to_strict_improve_rate | 20.0% |
| information_gain_mean | 2.061194 |
| mutual_information | 0.091216 |
| permutation_importance | -0.003704 |
| lift | 0.418118 |
| winner_rank_mean | 3.4444 |
| within_tie_diversity_rate | 1.0 |
| notes |  |

### `popularity` — Tier S

| 指標 | 値 |
|------|----|
| rank | 4 |
| composite_score | 0.315441 |
| coverage | 100.0% |
| missing_rate | 0.0% |
| tie_eligible | 9 |
| tie_resolution_rate | 100.0% |
| tie_correct | 1 |
| strict_hit | 1 |
| soft_hit | 5 |
| soft_to_strict_improve_rate | 20.0% |
| information_gain_mean | 2.061194 |
| mutual_information | 0.086008 |
| permutation_importance | 0.003704 |
| lift | 0.418118 |
| winner_rank_mean | 3.4444 |
| within_tie_diversity_rate | 1.0 |
| notes |  |

### `expected_popularity` — Tier S

| 指標 | 値 |
|------|----|
| rank | 5 |
| composite_score | 0.314848 |
| coverage | 100.0% |
| missing_rate | 0.0% |
| tie_eligible | 9 |
| tie_resolution_rate | 100.0% |
| tie_correct | 1 |
| strict_hit | 1 |
| soft_hit | 5 |
| soft_to_strict_improve_rate | 20.0% |
| information_gain_mean | 2.061194 |
| mutual_information | 0.086008 |
| permutation_importance | -0.02963 |
| lift | 0.418118 |
| winner_rank_mean | 3.4444 |
| within_tie_diversity_rate | 1.0 |
| notes |  |

### `damsire` — Tier A

| 指標 | 値 |
|------|----|
| rank | 6 |
| composite_score | 0.273702 |
| coverage | 100.0% |
| missing_rate | 0.0% |
| tie_eligible | 9 |
| tie_resolution_rate | 88.9% |
| tie_correct | 0 |
| strict_hit | 0 |
| soft_hit | 5 |
| soft_to_strict_improve_rate | 0.0% |
| information_gain_mean | 1.950083 |
| mutual_information | 0.418971 |
| permutation_importance | -0.074074 |
| lift | 0.0 |
| winner_rank_mean | 5.4444 |
| within_tie_diversity_rate | 1.0 |
| notes | ranked_by_loo_empirical_win_prior |

### `sire` — Tier A

| 指標 | 値 |
|------|----|
| rank | 7 |
| composite_score | 0.268174 |
| coverage | 100.0% |
| missing_rate | 0.0% |
| tie_eligible | 9 |
| tie_resolution_rate | 77.8% |
| tie_correct | 0 |
| strict_hit | 0 |
| soft_hit | 5 |
| soft_to_strict_improve_rate | 0.0% |
| information_gain_mean | 1.838972 |
| mutual_information | 0.467751 |
| permutation_importance | -0.081481 |
| lift | 0.0 |
| winner_rank_mean | 5.7778 |
| within_tie_diversity_rate | 0.888889 |
| notes | ranked_by_loo_empirical_win_prior |

### `breeder` — Tier A

| 指標 | 値 |
|------|----|
| rank | 8 |
| composite_score | 0.24126 |
| coverage | 100.0% |
| missing_rate | 0.0% |
| tie_eligible | 9 |
| tie_resolution_rate | 77.8% |
| tie_correct | 0 |
| strict_hit | 0 |
| soft_hit | 5 |
| soft_to_strict_improve_rate | 0.0% |
| information_gain_mean | 1.838972 |
| mutual_information | 0.299542 |
| permutation_importance | -0.092593 |
| lift | 0.0 |
| winner_rank_mean | 4.8889 |
| within_tie_diversity_rate | 0.888889 |
| notes | ranked_by_loo_empirical_win_prior |

### `sale_price` — Tier B

| 指標 | 値 |
|------|----|
| rank | 9 |
| composite_score | 0.21517 |
| coverage | 32.0% |
| missing_rate | 68.0% |
| tie_eligible | 1 |
| tie_resolution_rate | 100.0% |
| tie_correct | 0 |
| strict_hit | 0 |
| soft_hit | 5 |
| soft_to_strict_improve_rate | 0.0% |
| information_gain_mean | 1.0 |
| mutual_information | 0.394895 |
| permutation_importance | None |
| lift | 0.0 |
| winner_rank_mean | None |
| within_tie_diversity_rate | 0.111111 |
| notes |  |

### `oikiri_time` — Tier C

| 指標 | 値 |
|------|----|
| rank | 10 |
| composite_score | 0.017124 |
| coverage | 17.1% |
| missing_rate | 82.9% |
| tie_eligible | 0 |
| tie_resolution_rate | N/A |
| tie_correct | 0 |
| strict_hit | 0 |
| soft_hit | 5 |
| soft_to_strict_improve_rate | 0.0% |
| information_gain_mean | None |
| mutual_information | None |
| permutation_importance | None |
| lift | None |
| winner_rank_mean | None |
| within_tie_diversity_rate | 0.0 |
| notes | no_tie_eligible |

### `oikiri_rating` — Tier C

| 指標 | 値 |
|------|----|
| rank | 11 |
| composite_score | 0.017124 |
| coverage | 17.1% |
| missing_rate | 82.9% |
| tie_eligible | 0 |
| tie_resolution_rate | N/A |
| tie_correct | 0 |
| strict_hit | 0 |
| soft_hit | 5 |
| soft_to_strict_improve_rate | 0.0% |
| information_gain_mean | None |
| mutual_information | None |
| permutation_importance | None |
| lift | None |
| winner_rank_mean | None |
| within_tie_diversity_rate | 0.0 |
| notes | no_tie_eligible |

---

## 3. 【Decision】

```
Action Type: Evidence Ranking (shadow statistics)
Implementation Required: Ranking Engine only
Deployment Required: Optional CLI
Production Required: No (Prediction unchanged)
Resolver Required: No (V10.4 does not ship Resolver)
Risk: Low
Expected Next Action: Use Evidence Priority in future Tie Resolver design
```

Related: `v104-feature-importance.csv` · `v104-tier-ranking.csv` · `v104-shadow-resolver.md`
