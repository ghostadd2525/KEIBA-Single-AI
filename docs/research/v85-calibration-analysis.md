# Version85 — Calibration Analysis（World別 / C0）

**Generated:** `2026-07-28T10:06:08+00:00`  
候補比較の test 指標も末尾に記載。Interaction 非使用。

## ③ World別 Calibration（C0 win_prob mass）

### `rank7_world`

| Metric | Value |
|---|---:|
| n | 65 |
| hit_rate | 0.8000 |
| p_mean | 0.1042 |
| bias (p−hit) | -0.6958 |
| ECE | 0.6958 |
| Brier | 0.6408 |
| LogLoss | 1.8295 |
| Reliability mean|gap| | 0.6953 |

### `midhole_world`

| Metric | Value |
|---|---:|
| n | 24 |
| hit_rate | 0.9167 |
| p_mean | 0.0943 |
| bias (p−hit) | -0.8224 |
| ECE | 0.8224 |
| Brier | 0.7551 |
| LogLoss | 2.1948 |
| Reliability mean|gap| | 0.7998 |

### `unsatisfied`

| Metric | Value |
|---|---:|
| n | 176 |
| hit_rate | 0.7273 |
| p_mean | 0.1419 |
| bias (p−hit) | -0.5854 |
| ECE | 0.5854 |
| Brier | 0.5414 |
| LogLoss | 1.4778 |
| Reliability mean|gap| | 0.6071 |

### `core_world`

| Metric | Value |
|---|---:|
| n | 8 |
| hit_rate | 0.7500 |
| p_mean | 0.1325 |
| bias (p−hit) | -0.6175 |
| ECE | 0.6175 |
| Brier | 0.5698 |
| LogLoss | 1.5565 |
| Reliability mean|gap| | 0.6175 |

### `midupper_world`

| Metric | Value |
|---|---:|
| n | 6 |
| hit_rate | 0.8333 |
| p_mean | 0.1292 |
| bias (p−hit) | -0.7042 |
| ECE | 0.7042 |
| Brier | 0.6336 |
| LogLoss | 1.7288 |
| Reliability mean|gap| | 0.7042 |

### `mixed_world`

| Metric | Value |
|---|---:|
| n | 6 |
| hit_rate | 0.8333 |
| p_mean | 0.1045 |
| bias (p−hit) | -0.7289 |
| ECE | 0.7289 |
| Brier | 0.6720 |
| LogLoss | 1.9200 |
| Reliability mean|gap| | 0.7289 |

### `_all`

| Metric | Value |
|---|---:|
| n | 285 |
| hit_rate | 0.7649 |
| p_mean | 0.1280 |
| bias (p−hit) | -0.6370 |
| ECE | 0.6370 |
| Brier | 0.5875 |
| LogLoss | 1.6352 |
| Reliability mean|gap| | 0.6265 |

## Candidate test-split（参考・実装なし）

train=142 / test=143（時系列半分割。World prior は train のみ）

| Rank | Candidate | ECE | Brier | LogLoss | bias | p_mean | hit |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | `C3_world_empirical_prior_train` | 0.0319 | 0.1836 | 0.5523 | 0.0151 | 0.7703 | 0.7552 |
| 2 | `C7c_blend_mass_0_9_prior` | 0.0491 | 0.1857 | 0.5576 | -0.0491 | 0.7061 | 0.7552 |
| 3 | `C7b_blend_mass_0_7_prior` | 0.1776 | 0.2150 | 0.6222 | -0.1776 | 0.5776 | 0.7552 |
| 4 | `C5_top1_over_top1_plus_top2` | 0.1902 | 0.2284 | 0.6497 | -0.1902 | 0.5650 | 0.7552 |
| 5 | `C7_blend_mass_0_3_prior` | 0.4402 | 0.3736 | 0.9542 | -0.4346 | 0.3207 | 0.7552 |
| 6 | `C6_softmax_T0_5` | 0.5423 | 0.4870 | 1.2847 | -0.5423 | 0.2129 | 0.7552 |
| 7 | `C4_market_inv_odds_mass` | 0.5651 | 0.5139 | 1.4511 | -0.5651 | 0.1902 | 0.7552 |
| 8 | `C0_win_prob_mass_V84` | 0.6273 | 0.5802 | 1.6162 | -0.6273 | 0.1280 | 0.7552 |
| 9 | `C1_raw_win_prob` | 0.6273 | 0.5802 | 1.6162 | -0.6273 | 0.1280 | 0.7552 |
| 10 | `C6b_softmax_T2_0` | 0.6588 | 0.6194 | 1.8100 | -0.6588 | 0.0965 | 0.7552 |
| 11 | `C2_uniform_1_over_field` | 0.6834 | 0.6517 | 2.0189 | -0.6834 | 0.0719 | 0.7552 |

### 読み方

- bias < 0 → underconfident（平均）。
- C3/C7* は prior を含むため「定義候補」であり、Production 採用ではない。
- 本表は調査用。PE 組み込み禁止。
