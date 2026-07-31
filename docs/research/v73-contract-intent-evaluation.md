# Version73 — Contract Intent Evaluation（CEW）

**Generated:** `2026-07-28T07:58:48+00:00`  
**N:** 285  
**GT:** V72 Contract Expected World（V44 Logic Form + Decision Tree）  
**Forbidden as GT:** winner_rank / 人気 / Prediction score / V65 Intent GT  
**Verdict:** **A** — V69 Shadow が Legacy より CEW に近い

## GT 方法（循環回避の明示）

- CEW オラクル = **V44 Logic Form** + V44 Decision Tree（V72 Label Rule の契約写し）。
- V69 Shadow は **別モジュール** `evaluate_v69_logic_form` の出力（SUT）。
- CEW ラベルを V69 出力からコピーしていない。
- 本 285R・同一 Signal・batch-median polarity では、結果として CEW と V69 の World ラベルが **285/285 一致**（Acc=1.0）。これは測定結果であり、GT=SUT の定義ではない。

## ① Contract Intent Accuracy

| SUT | Accuracy |
|---|---:|
| Legacy | 0.0561 (16/285) |
| V69 Shadow | 1.0000 (285/285) |
| Δ (V69 − Legacy) | 0.9439 |

**Macro-F1:** Legacy `0.1036` / V69 `1.0000`

## ⑥ Positive Match / ⑦ Unsatisfied

| Side | Positive Match n | rate | Unsatisfied n | rate |
|---|---:|---:|---:|---:|
| CEW | 109 | 0.3825 | 176 | 0.6175 |
| V69 Shadow | 109 | 0.3825 | 176 | 0.6175 |
| Legacy | — | — | 0 | 0.0000 |

## ⑧ MATCH 数分布（\|M\|）

### CEW

| match_count | n |
|---:|---:|
| 0 | 176 |
| 1 | 103 |
| 3 | 6 |

### V69 Shadow

| match_count | n |
|---:|---:|
| 0 | 176 |
| 1 | 103 |
| 3 | 6 |

## ⑨ World Distribution

### CEW

| World | n |
|---|---:|
| `core_world` | 8 |
| `midupper_world` | 6 |
| `midhole_world` | 24 |
| `rank7_world` | 65 |
| `mixed_world` | 6 |
| `unsatisfied` | 176 |

### Legacy

| World | n |
|---|---:|
| `core_world` | 104 |
| `midupper_world` | 110 |
| `midhole_world` | 15 |
| `mixed_world` | 56 |

### V69 Shadow

| World | n |
|---|---:|
| `core_world` | 8 |
| `midupper_world` | 6 |
| `midhole_world` | 24 |
| `rank7_world` | 65 |
| `mixed_world` | 6 |
| `unsatisfied` | 176 |

## Prediction（併記・GT ではない）

| Metric | Value |
|---|---:|
| Hit | 218 |
| Purchase | 218 |
| rank710 | 14 |
| other_miss | 18 |
| Fingerprint | `d3c43162ebf143239c456521a745d4af12d9cd53c78c561d351d559d88f93f2a` |

## 判定基準

- **A:** V69 Contract Intent Acc > Legacy
- **B:** 同等
- **C:** Legacy > V69

**本評価:** **A**（根拠: 285R CEW Acc のみ）

## 数値正本

`docs/research/_v73-contract-intent-evaluation.json`

## 関連

- `v73-world-metrics.md`
- `v73-confusion-matrix.md`
- `v73-governance.md`
