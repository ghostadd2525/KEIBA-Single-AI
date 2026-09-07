# Version10.2 Research — Evidence Analysis

**Date:** 2026-07-27T04:59:19+00:00  
**Type:** Shadow statistical evaluation（Prediction 順位は変更しない）  
**Input:** `research_prediction_snapshots` ∩ `research_snapshot_features` ∩ `race_results`  
**Hard Lock:** PE / CE / AI Score / Prediction Logic **変更なし**

---

## 0. Verdict

| 指標 | 値 |
|------|----|
| 評価レース数 | **51** |
| Baseline Strict Hit | **8/51** (15.7%) |
| Baseline Soft Hit | **13/51** (25.5%) |
| Soft∧¬Strict（回収余地） | **5** |
| Tie レース（|G|≥2） | **9** |
| Rank Degeneracy（|G|≥3） | **7** |
| 平均タイ頭数 | **1.627** |

### Feature 有効性ランキング（要約）

| Rank | Feature | Soft→Strict | StrictΔ | IG(bit) | Coverage | 判定 |
|-----:|---------|------------:|--------:|--------:|---------:|------|
| 1 | `popularity` | 20.0% | 2.0% | 2.0612 | 100.0% | PROMISING |
| 2 | `win_odds` | 20.0% | 2.0% | 2.0612 | 100.0% | PROMISING |
| 3 | `expected_popularity` | 20.0% | 2.0% | 2.0612 | 100.0% | PROMISING |
| 4 | `trainer` | N/A | N/A | N/A | 100.0% | CATEGORICAL |
| 5 | `sire` | N/A | N/A | N/A | 0.0% | NOT_COLLECTED |
| 6 | `damsire` | N/A | N/A | N/A | 0.0% | NOT_COLLECTED |
| 7 | `breeder` | N/A | N/A | N/A | 0.0% | NOT_COLLECTED |
| 8 | `oikiri_time` | 0.0% | 0.0% | N/A | 0.0% | NOT_COLLECTED |
| 9 | `oikiri_rating` | 0.0% | 0.0% | N/A | 0.0% | NOT_COLLECTED |

判定凡例: **PROMISING**=Shadow Resolver で Strict/Soft回収が正、**COLLECTED_NO_LIFT**=取得済みだが改善ゼロ、**CATEGORICAL**=順位付けルール未定義、**NOT_COLLECTED**=Collector 未実装。

### 重要所見（本番 51R）

1. **市場3特徴は同値クラス**: `popularity` / `win_odds` / `expected_popularity` の Shadow 指標が一致（派生関係）。
2. **解消 ≠ 正解**: Tie解消率 **100%**（9/9）だが Tie正解は **1/9**。一意化はできるが、argmin(人気/オッズ) だけでは勝ち馬を高確率では拾えない。
3. **回収**: Soft∧¬Strict 5R のうち **1R 回収**（20%）。Strict は 8→9（+1R / +2.0pt）。
4. **trainer**: Coverage 100%、タイ群内 diversity 100%だが、prior 無しでは Resolver 不可。
5. **血統・調教**: Collector 未実装のため本フェーズでは有効性未評価（V10.1 で取得可能性のみ証明済み）。

---

## 1. 定義

- **coverage**: filled_cells / total_cells over complete snapshots
- **missing_rate**: 1 - coverage
- **tie_races**: races where |tie_group| >= 2 (min model_rank shared)
- **tie_resolution_rate**: among eligible tie races (full feature on G), unique argmin/argmax pick rate
- **strict_hit**: unique top (model_rank, win_prob, horse_number) == winner
- **soft_hit**: winner ∈ tie_group (min model_rank)
- **strict_hit_improve_rate**: (strict_hits_with_shadow_resolver - baseline_strict) / n_races
- **soft_to_strict_improve_rate**: recovered Soft∧¬Strict races / Soft∧¬Strict count
- **information_gain**: mean bits: log2(|G|) - log2(|remaining|) after feature partition on G
- **winner_rank_distribution**: 1-based rank of winner by feature across full field (ordinal only)
- **shadow_only**: resolver applied only in analysis; stored Prediction ranks unchanged

Ordinal の Tie 解決方向:

| Feature | 規則 |
|---------|------|
| popularity / expected_popularity | 小さいほど良い（argmin） |
| win_odds | 小さいほど良い（argmin） |
| oikiri_time | 小さいほど良い（argmin） |
| oikiri_rating | A>B>C>D>E（argmax letter） |
| trainer / sire / damsire / breeder | カテゴリカル — prior 無しでは未解決 |

---

## 2. Feature 別詳細

### `popularity`

| 指標 | 値 |
|------|----|
| Coverage | 100.0% (630/630) |
| Missing率 | 0.0% |
| Tieレース数（全体） | 9 |
| Tie eligible（G上フル） | 9 |
| Tie解消数 / 率 | 9 / 100.0% |
| Tie正解数 | 1 |
| Strict Hit改善率 | 2.0% |
| Soft→Strict改善率 | 20.0% (1/5) |
| Information Gain (mean bit) | 2.0612 |
| Winner順位平均 | 3.0784 |
| Winner順位分布 | `{"1": 17, "2": 11, "3": 7, "4": 5, "5": 5, "6": 2, "9": 1, "10": 2, "11": 1}` |
| Within-tie diversity | 100.0% |
| Rankable | True |

### `win_odds`

| 指標 | 値 |
|------|----|
| Coverage | 100.0% (630/630) |
| Missing率 | 0.0% |
| Tieレース数（全体） | 9 |
| Tie eligible（G上フル） | 9 |
| Tie解消数 / 率 | 9 / 100.0% |
| Tie正解数 | 1 |
| Strict Hit改善率 | 2.0% |
| Soft→Strict改善率 | 20.0% (1/5) |
| Information Gain (mean bit) | 2.0612 |
| Winner順位平均 | 3.1176 |
| Winner順位分布 | `{"1": 17, "2": 10, "3": 8, "4": 4, "5": 6, "6": 2, "9": 1, "10": 2, "11": 1}` |
| Within-tie diversity | 100.0% |
| Rankable | True |

### `expected_popularity`

| 指標 | 値 |
|------|----|
| Coverage | 100.0% (630/630) |
| Missing率 | 0.0% |
| Tieレース数（全体） | 9 |
| Tie eligible（G上フル） | 9 |
| Tie解消数 / 率 | 9 / 100.0% |
| Tie正解数 | 1 |
| Strict Hit改善率 | 2.0% |
| Soft→Strict改善率 | 20.0% (1/5) |
| Information Gain (mean bit) | 2.0612 |
| Winner順位平均 | 3.1176 |
| Winner順位分布 | `{"1": 17, "2": 10, "3": 8, "4": 4, "5": 6, "6": 2, "9": 1, "10": 2, "11": 1}` |
| Within-tie diversity | 100.0% |
| Rankable | True |

### `trainer`

| 指標 | 値 |
|------|----|
| Coverage | 100.0% (630/630) |
| Missing率 | 0.0% |
| Tieレース数（全体） | 9 |
| Tie eligible（G上フル） | 0 |
| Tie解消数 / 率 | 0 / N/A |
| Tie正解数 | 0 |
| Strict Hit改善率 | N/A |
| Soft→Strict改善率 | N/A (0/5) |
| Information Gain (mean bit) | N/A |
| Winner順位平均 | N/A |
| Winner順位分布 | `{}` |
| Within-tie diversity | 100.0% |
| Rankable | False |
| Notes | CATEGORICAL_NO_PRIOR — resolver metrics N/A without win-rate prior |

### `sire`

| 指標 | 値 |
|------|----|
| Coverage | 0.0% (0/630) |
| Missing率 | 100.0% |
| Tieレース数（全体） | 9 |
| Tie eligible（G上フル） | 0 |
| Tie解消数 / 率 | 0 / N/A |
| Tie正解数 | 0 |
| Strict Hit改善率 | N/A |
| Soft→Strict改善率 | N/A (0/5) |
| Information Gain (mean bit) | N/A |
| Winner順位平均 | N/A |
| Winner順位分布 | `{}` |
| Within-tie diversity | 0.0% |
| Rankable | False |
| Notes | NOT_COLLECTED; CATEGORICAL_NO_PRIOR — resolver metrics N/A without win-rate prior |

### `damsire`

| 指標 | 値 |
|------|----|
| Coverage | 0.0% (0/630) |
| Missing率 | 100.0% |
| Tieレース数（全体） | 9 |
| Tie eligible（G上フル） | 0 |
| Tie解消数 / 率 | 0 / N/A |
| Tie正解数 | 0 |
| Strict Hit改善率 | N/A |
| Soft→Strict改善率 | N/A (0/5) |
| Information Gain (mean bit) | N/A |
| Winner順位平均 | N/A |
| Winner順位分布 | `{}` |
| Within-tie diversity | 0.0% |
| Rankable | False |
| Notes | NOT_COLLECTED; CATEGORICAL_NO_PRIOR — resolver metrics N/A without win-rate prior |

### `breeder`

| 指標 | 値 |
|------|----|
| Coverage | 0.0% (0/630) |
| Missing率 | 100.0% |
| Tieレース数（全体） | 9 |
| Tie eligible（G上フル） | 0 |
| Tie解消数 / 率 | 0 / N/A |
| Tie正解数 | 0 |
| Strict Hit改善率 | N/A |
| Soft→Strict改善率 | N/A (0/5) |
| Information Gain (mean bit) | N/A |
| Winner順位平均 | N/A |
| Winner順位分布 | `{}` |
| Within-tie diversity | 0.0% |
| Rankable | False |
| Notes | NOT_COLLECTED; CATEGORICAL_NO_PRIOR — resolver metrics N/A without win-rate prior |

### `oikiri_time`

| 指標 | 値 |
|------|----|
| Coverage | 0.0% (0/630) |
| Missing率 | 100.0% |
| Tieレース数（全体） | 9 |
| Tie eligible（G上フル） | 0 |
| Tie解消数 / 率 | 0 / N/A |
| Tie正解数 | 0 |
| Strict Hit改善率 | 0.0% |
| Soft→Strict改善率 | 0.0% (0/5) |
| Information Gain (mean bit) | N/A |
| Winner順位平均 | N/A |
| Winner順位分布 | `{}` |
| Within-tie diversity | 0.0% |
| Rankable | True |
| Notes | NOT_COLLECTED |

### `oikiri_rating`

| 指標 | 値 |
|------|----|
| Coverage | 0.0% (0/630) |
| Missing率 | 100.0% |
| Tieレース数（全体） | 9 |
| Tie eligible（G上フル） | 0 |
| Tie解消数 / 率 | 0 / N/A |
| Tie正解数 | 0 |
| Strict Hit改善率 | 0.0% |
| Soft→Strict改善率 | 0.0% (0/5) |
| Information Gain (mean bit) | N/A |
| Winner順位平均 | N/A |
| Winner順位分布 | `{}` |
| Within-tie diversity | 0.0% |
| Rankable | True |
| Notes | NOT_COLLECTED |

---

## 3. 解釈（Prediction 非改変）

1. 本レポートは **Shadow Resolver** 評価のみ。保存済み `model_rank` / `win_prob` は未変更。
2. Soft∧¬Strict が Resolver の理論回収上限（Oracle = Soft Hit）。
3. NOT_COLLECTED Feature（sire / damsire / breeder / oikiri_*）は V10.1 で取得可能性のみ確認済み。Collector 実装後に再計測。
4. カテゴリカル Feature は勝率 prior を持たない限り Tie Resolver に直接使えない。
5. 次フェーズ Version10.3 Tie Resolver は、本ランキングで PROMISING / 高 Coverage の Feature から採用する。

---

## 4. 【Decision】

```
Action Type: Evidence Analysis (read-only + analyzer code)
Implementation Required: Analyzer only (no Prediction change)
Deployment Required: Optional (CLI on EC2)
Configuration Required: No
Production Required: No (Prediction 非改変)
Rollback Required: No
Risk: Low
Expected Next Action: Version10.3 Tie Resolver design/impl using PROMISING features
```

CSV: `docs/research/v102-feature-ranking.csv`  
Generated: `2026-07-27T04:59:19+00:00`
