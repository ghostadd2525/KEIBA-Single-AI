# Version74 — World Strategy Validation

**Generated:** `2026-07-28T08:10:46+00:00`  
**Corpus:** 285R  
**Labels:** V72/V73 CEW（Contract Expected World）  
**Verdict:** **B** — 一部重複する（安定 World は限定的だが、差の証拠あり）  
**Locks:** Trigger / Blueprint / Signal / Threshold / World Meaning / PE / Prediction / Production — 非変更  
**非目的:** Hit 改善 / PE 変更

## CEW 分布

| World | n | stable (≥20) |
|---|---:|:---:|
| `core_world` | 8 | N |
| `midupper_world` | 6 | N |
| `midhole_world` | 24 | Y |
| `rank7_world` | 65 | Y |
| `mixed_world` | 6 | N |
| `bug_world` | 0 | — |
| `unsatisfied` | 176 | Y |

## ① World別勝ち方（勝ち馬・脚質・人気・能力差・展開文脈）

### `core_world`（n=8・不安定）

| 指標 | 値 |
|---|---:|
| winner model_rank mean | 5.3750 |
| winner win_prob mean | 0.0805 |
| winner history mean | 0.7972 |
| winner odds mean | 12.8250 |
| winner popularity mean* | 3.5000 |
| field_size mean | 16.6250 |
| distance mean | 1812.5000 |

能力差・展開文脈（レース平均）:

| Concept | mean |
|---|---:|
| `top_gap` | 0.0496 |
| `ability_separation` | 0.0795 |
| `upper_ability_band` | 0.2776 |
| `mid_eval_band_open` | 0.3849 |
| `top_monopoly` | 0.1325 |
| `ability_subordinate` | 0.7518 |

脚質（勝ち馬カウント）:

| Style | n |
|---|---:|
| 先行 | 5 |
| 逃げ | 2 |
| 差し | 1 |

脚質リフト（winner_share − loser_share）:

| Style | lift |
|---|---:|
| 先行 | 0.3370 |
| 逃げ | 0.0500 |
| 差し | -0.1470 |
| 追込 | -0.2400 |

\*popularity は変動ありレースのみ。

### `midupper_world`（n=6・不安定）

| 指標 | 値 |
|---|---:|
| winner model_rank mean | 3.3333 |
| winner win_prob mean | 0.0824 |
| winner history mean | 0.8322 |
| winner odds mean | 6.0667 |
| winner popularity mean* | — |
| field_size mean | 15.6667 |
| distance mean | 1833.3333 |

能力差・展開文脈（レース平均）:

| Concept | mean |
|---|---:|
| `top_gap` | 0.0202 |
| `ability_separation` | 0.0769 |
| `upper_ability_band` | 0.3271 |
| `mid_eval_band_open` | 0.3860 |
| `top_monopoly` | 0.1292 |
| `ability_subordinate` | 0.8990 |

脚質（勝ち馬カウント）:

| Style | n |
|---|---:|
| 差し | 4 |
| 先行 | 1 |
| 逃げ | 1 |

脚質リフト（winner_share − loser_share）:

| Style | lift |
|---|---:|
| 差し | 0.2008 |
| 逃げ | 0.0076 |
| 先行 | -0.0606 |
| 追込 | -0.1477 |

\*popularity は変動ありレースのみ。

### `midhole_world`（n=24）

| 指標 | 値 |
|---|---:|
| winner model_rank mean | 5.4583 |
| winner win_prob mean | 0.0716 |
| winner history mean | 0.8124 |
| winner odds mean | 20.5333 |
| winner popularity mean* | 5.6667 |
| field_size mean | 14.4583 |
| distance mean | 1754.1667 |

能力差・展開文脈（レース平均）:

| Concept | mean |
|---|---:|
| `top_gap` | 0.0120 |
| `ability_separation` | 0.0276 |
| `upper_ability_band` | 0.2511 |
| `mid_eval_band_open` | 0.4747 |
| `top_monopoly` | 0.0943 |
| `ability_subordinate` | 0.9400 |

脚質（勝ち馬カウント）:

| Style | n |
|---|---:|
| 差し | 10 |
| 先行 | 8 |
| 逃げ | 3 |
| 追込 | 3 |

脚質リフト（winner_share − loser_share）:

| Style | lift |
|---|---:|
| 先行 | 0.0949 |
| 差し | 0.0080 |
| 逃げ | -0.0174 |
| 追込 | -0.0855 |

\*popularity は変動ありレースのみ。

### `rank7_world`（n=65）

| 指標 | 値 |
|---|---:|
| winner model_rank mean | 4.7077 |
| winner win_prob mean | 0.0743 |
| winner history mean | 0.8340 |
| winner odds mean | 10.8815 |
| winner popularity mean* | — |
| field_size mean | 16.1077 |
| distance mean | 1623.8462 |

能力差・展開文脈（レース平均）:

| Concept | mean |
|---|---:|
| `top_gap` | 0.0125 |
| `ability_separation` | 0.0498 |
| `upper_ability_band` | 0.2712 |
| `mid_eval_band_open` | 0.4058 |
| `top_monopoly` | 0.1042 |
| `ability_subordinate` | 0.9377 |

脚質（勝ち馬カウント）:

| Style | n |
|---|---:|
| 先行 | 26 |
| 逃げ | 21 |
| 差し | 13 |
| 追込 | 5 |

脚質リフト（winner_share − loser_share）:

| Style | lift |
|---|---:|
| 逃げ | 0.0970 |
| 先行 | 0.0772 |
| 差し | -0.0831 |
| 追込 | -0.0911 |

\*popularity は変動ありレースのみ。

### `mixed_world`（n=6・不安定）

| 指標 | 値 |
|---|---:|
| winner model_rank mean | 4.8333 |
| winner win_prob mean | 0.0896 |
| winner history mean | 0.7449 |
| winner odds mean | 9.4333 |
| winner popularity mean* | — |
| field_size mean | 14.6667 |
| distance mean | 1750.0000 |

能力差・展開文脈（レース平均）:

| Concept | mean |
|---|---:|
| `top_gap` | 0.0131 |
| `ability_separation` | 0.0451 |
| `upper_ability_band` | 0.2800 |
| `mid_eval_band_open` | 0.4497 |
| `top_monopoly` | 0.1045 |
| `ability_subordinate` | 0.9343 |

脚質（勝ち馬カウント）:

| Style | n |
|---|---:|
| 追込 | 2 |
| 逃げ | 2 |
| 差し | 1 |
| 先行 | 1 |

脚質リフト（winner_share − loser_share）:

| Style | lift |
|---|---:|
| 追込 | 0.1748 |
| 逃げ | 0.0894 |
| 差し | 0.0081 |
| 先行 | -0.2724 |

\*popularity は変動ありレースのみ。

### `bug_world`

サンプル 0 — 抽出不可。

### `unsatisfied`（n=176）

| 指標 | 値 |
|---|---:|
| winner model_rank mean | 4.3977 |
| winner win_prob mean | 0.0935 |
| winner history mean | 0.8150 |
| winner odds mean | 9.1625 |
| winner popularity mean* | 3.7000 |
| field_size mean | 13.9261 |
| distance mean | 1708.8068 |

能力差・展開文脈（レース平均）:

| Concept | mean |
|---|---:|
| `top_gap` | 0.0398 |
| `ability_separation` | 0.0780 |
| `upper_ability_band` | 0.3281 |
| `mid_eval_band_open` | 0.4518 |
| `top_monopoly` | 0.1419 |
| `ability_subordinate` | 0.8011 |

脚質（勝ち馬カウント）:

| Style | n |
|---|---:|
| 先行 | 61 |
| 逃げ | 56 |
| 差し | 41 |
| 追込 | 18 |

脚質リフト（winner_share − loser_share）:

| Style | lift |
|---|---:|
| 逃げ | 0.1191 |
| 先行 | 0.0451 |
| 追込 | -0.0714 |
| 差し | -0.0928 |

\*popularity は変動ありレースのみ。

## ④ Strategy Separation（要約）

- 安定 World（n≥20）: `midhole_world`, `rank7_world`
- 不安定（0<n<20）: `core_world`, `midupper_world`, `mixed_world`
- ゼロ: `bug_world`
- 相互作用符号逆転ペア数: **2**
- 安定 Strategy ペア mean Top5 Jaccard: 0.6667
- 安定 Strategy ペア mean context profile corr: 0.9959
- unsatisfied n: 176

## 数値正本

`docs/research/_v74-world-strategy-validation.json`
