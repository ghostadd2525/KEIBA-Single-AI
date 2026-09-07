# Version42 — World Meaning Coverage & Semantic Score

**Date:** 2026-07-28  
**Type:** Research / Audit only

## 採点規則（推測禁止・明示）

各 World の設計概念を列挙し、Trigger との対応を次で採点する。

| 記号 | 点 | 定義 |
|---|---:|---|
| ALIGNED | 1.0 | Trigger が当該概念を表す Signal を **正の条件**として使う（コード根拠あり） |
| PROXY | 0.5 | 関連 Signal はあるが、コード上の意味が設計概念と一致しない／近似のみ |
| ABSENT | 0.0 | Trigger に概念が現れない |
| INVERTED | 0.0 | 現れ方が設計と逆（Wrong Semantic）。点は 0、Wrong フラグ付き |

`Semantic Score = sum(points) / N_concepts`

## ③ World Meaning Coverage

### core_world — Score **0.00** (0/5)

| 設計概念 | 判定 | 点 | 根拠 |
|---|---|---:|---|
| 能力決着の正検出 | ABSENT | 0 | R8 DEFAULT, parts=[] |
| TopGap 大 | ABSENT | 0 | `get_context_top_gap` は Trigger 未使用 |
| 能力差 | ABSENT | 0 | Trigger Signal 集合外 |
| レース格 | ABSENT | 0 | Trigger 未使用 |
| 長距離 | INVERTED/ABSENT | 0 | 距離は sfp の短距離側。core 正条件なし |

Coverage: **0%**

### midupper_world — Score **0.17** (0.5/3)

| 設計概念 | 判定 | 点 | 根拠 |
|---|---|---:|---|
| 上位能力馬中心 | ABSENT | 0 | 能力順位・上位帯 Signal なし。difficulty≠上位能力 |
| 展開の影響 | PROXY | 0.5 | `short_field_pressure` = route/隊列圧（展開の一部近似） |
| 適性の影響 | ABSENT | 0 | Trigger に適性 Signal なし |

Coverage: **17%**

### midhole_world — Score **0.00** (0/2)

| 設計概念 | 判定 | 点 | 根拠 |
|---|---|---:|---|
| 中位評価馬の勝ち筋 | ABSENT | 0 | rank/人気/評価帯なし |
| 「十分存在する」広さ | ABSENT | 0 | late_stop∧sustained はペース生存条件であり中位帯の広さではない |

（PROXY を付けない: コードが中位を指す根拠が無い）

Coverage: **0%**

### rank7_world — Score **0.50** (1.5/3)

| 設計概念 | 判定 | 点 | 根拠 |
|---|---|---:|---|
| Chaos が勝敗に影響 | ALIGNED | 1.0 | R5 `chaos>=0.58` |
| 展開・混戦 | PROXY | 0.5 | `high_pace` は展開の一側面 |
| 能力以上（能力の劣後） | ABSENT | 0 | 低 TopGap 等は Trigger に無し |

Coverage: **50%**

### mixed_world — Score **0.33** (0.5/2)

| 設計概念 | 判定 | 点 | 根拠 |
|---|---|---:|---|
| 複数勝ち筋の共存 | PROXY | 0.5 | R1: 複数 Signal の OR（共存の近似、勝ち筋列挙ではない） |
| 単一説明不能 | ABSENT | 0 | 明示条件なし。高 phase 単体（R3）は説明不能性ではない |

Score = 0.5/2 = **0.33**

### bug_world — Score **0.25** (0.5/2)

| 設計概念 | 判定 | 点 | 根拠 |
|---|---|---:|---|
| 特殊・極端 | PROXY | 0.5 | 高 chaos∧高 difficulty |
| 通常ロジックで説明困難 | ABSENT | 0 | 例外フラグ・説明不能ラベルなし |

Coverage: **25%**

## ⑥ Semantic Score 一覧

| World | Score | Coverage 表現 |
|---|---:|---|
| core_world | **0.00** | 0% |
| midupper_world | **0.17** | 17% |
| midhole_world | **0.00** | 0% |
| rank7_world | **0.50** | 50% |
| mixed_world | **0.33** | 33% |
| bug_world | **0.25** | 25% |
| **平均（等重み）** | **0.21** | **21%** |

## 読み取り

- 最も設計に近いのは `rank7_world`（Chaos が正条件）でも半分。
- `core` / `midhole` は設計概念が Trigger に **ゼロ符号化**。
- 全体 21% は「閾値チューニング不足」ではなく **意味の対応不足**。
