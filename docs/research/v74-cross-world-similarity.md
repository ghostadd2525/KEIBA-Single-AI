# Version74 — Cross World Similarity

**Generated:** `2026-07-28T08:10:46+00:00`  
ラベル = CEW。類似度は 285R 実測のみ。

## ③ Pairwise

| A | B | n_a | n_b | stable | strat | ctx ρ | importance ρ | Top5 Jaccard | style Δmax |
|---|---|---:|---:|:---:|:---:|---:|---:|---:|---:|
| `core_world` | `midupper_world` | 8 | 6 | N | N | 0.9967 | 1.0000 | 1.0000 | 0.3976 |
| `core_world` | `midhole_world` | 8 | 24 | N | N | 0.9971 | 0.6000 | 0.6667 | 0.2421 |
| `core_world` | `rank7_world` | 8 | 65 | N | N | 0.9980 | 0.8286 | 1.0000 | 0.2598 |
| `core_world` | `mixed_world` | 8 | 6 | N | N | 0.9994 | 0.6571 | 0.6667 | 0.6094 |
| `core_world` | `unsatisfied` | 8 | 176 | N | N | 0.9973 | 1.0000 | 0.6000 | 0.2919 |
| `midupper_world` | `midhole_world` | 6 | 24 | N | N | 0.9890 | 0.6000 | 0.6667 | 0.1928 |
| `midupper_world` | `rank7_world` | 6 | 65 | N | N | 0.9972 | 0.8286 | 1.0000 | 0.2839 |
| `midupper_world` | `mixed_world` | 6 | 6 | N | N | 0.9948 | 0.6571 | 0.6667 | 0.3225 |
| `midupper_world` | `unsatisfied` | 6 | 176 | N | N | 0.9911 | 1.0000 | 0.6000 | 0.2935 |
| `midhole_world` | `rank7_world` | 24 | 65 | Y | Y | 0.9959 | 0.7714 | 0.6667 | 0.1144 |
| `midhole_world` | `mixed_world` | 24 | 6 | N | N | 0.9989 | -0.0857 | 0.6667 | 0.3673 |
| `midhole_world` | `unsatisfied` | 24 | 176 | Y | N | 0.9934 | 0.6000 | 0.6000 | 0.1365 |
| `rank7_world` | `mixed_world` | 65 | 6 | N | N | 0.9986 | 0.1429 | 0.6667 | 0.3495 |
| `rank7_world` | `unsatisfied` | 65 | 176 | Y | N | 0.9907 | 0.8286 | 0.6000 | 0.0321 |
| `mixed_world` | `unsatisfied` | 6 | 176 | N | N | 0.9953 | 0.6571 | 0.3333 | 0.3174 |

## 分ける価値の評価（測定）

- Strategy 安定ペア mean Top5 Jaccard = 0.6667
- Strategy 安定ペア mean context profile corr = 0.9959
- 相互作用符号逆転 = 2 件

高 Jaccard（馬特徴セット重複）でも、文脈プロファイル相関・相互作用符号・脚質リフトが異なれば Selector としての分離理由になる。

**Verdict 連動:** **B** — 一部重複する（安定 World は限定的だが、差の証拠あり）
