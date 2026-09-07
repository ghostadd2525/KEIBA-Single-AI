# Version42 — World Semantics Audit

**Date:** 2026-07-28  
**Type:** Research / Architecture Audit only（改善・実装禁止）  
**Question:** Trigger は各 World の設計思想（勝ち筋）を表現しているか？  
**Not questioned:** Trigger が発火するか / 閾値が適切か（V40/V41）

## 正本（設計思想）

World = 分類ラベルではなく **勝ち筋**。

| World | 設計思想（勝ち筋） |
|---|---|
| `core_world` | 能力順に決着しやすい世界（G1長距離・TopGap大など能力差が結果へ反映） |
| `midupper_world` | 上位能力馬中心だが、展開・適性も勝敗へ影響 |
| `midhole_world` | 中位評価馬まで十分勝ち筋が存在する |
| `rank7_world` | 展開・混戦・Chaos が能力以上に勝敗へ影響 |
| `mixed_world` | 複数の勝ち筋が共存し、一つの World では説明できない |
| `bug_world` | 通常ロジックでは説明困難な特殊ケース |

## 実コード正本（Trigger）

出典:

- Product: `demo_ticket_optimizer_core.classify_world_line_type`
- Research mirror: `TRIGGER_RULES` in `world_trigger_saturation.py`（R1–R8、product と同型）

| Rule | World | 条件（実コード） |
|---|---|---|
| R1 | mixed | `short_field_pressure>=0.72` AND (`phase>=0.48` OR `chaos>=0.42` OR `difficulty>=0.42`) |
| R2 | midupper | `short_field_pressure>=0.58` AND `difficulty>=0.38` |
| R3 | mixed | `phase>=0.62` |
| R4 | midhole | `late_stop>=0.56` AND `sustained>=0.52` |
| R5 | rank7 | `chaos>=0.58` AND `high_pace>=0.48` |
| R6 | bug | `chaos>=0.66` AND `difficulty>=0.62` |
| R7 | midupper | `difficulty>=0.50` |
| R8 | **core** | **`DEFAULT`（parts=[]）** |

使用 Signal 集合（Trigger 入力）:

`short_field_pressure`, `difficulty`/`race_leg_difficulty`, `phase`/`phase_transition`, `late_stop`, `sustained`, `chaos`, `high_pace`

**含まれない:** `top_gap`, 能力差, レース格/`race_class`/`grade`, 「長距離」条件, 中位 rank 帯

## Semantic Mapping（①）

### core_world

| 項目 | 内容 |
|---|---|
| 設計思想 | 能力決着の勝ち筋（独立） |
| 現在 Trigger | R8 `DEFAULT` — 他ルール全 FAIL 時の残余 |
| 使用 Signal | **なし**（正の条件ゼロ） |
| 一致評価 | **不一致** — 設計は正の勝ち筋、実装は負の残余ラベル |

`classify_world_line_type` docstring（実コード）:

> LGBMは能力評価専用。world_line側で survival world を判定する。

→ Product 自身が world_line を **survival world** として定義しており、設計正本の「能力決着勝ち筋」と役割が逆転している。

### midupper_world

| 項目 | 内容 |
|---|---|
| 設計思想 | 上位能力 + 展開・適性 |
| 現在 Trigger | R2: sfp∧difficulty / R7: difficulty 単体 |
| 使用 Signal | `short_field_pressure`, `difficulty` |
| 一致評価 | **部分〜乖離** — 「上位能力」「適性」を表す Signal が Trigger に無い。`difficulty` は脚難度、`sfp` は短距離×多頭の route 圧（docstring: 能力スコアではない） |

### midhole_world

| 項目 | 内容 |
|---|---|
| 設計思想 | 中位評価馬の勝ち筋が十分存在する |
| 現在 Trigger | R4: late_stop ∧ sustained |
| 使用 Signal | `late_stop`, `sustained` |
| 一致評価 | **乖離** — 中位評価・中位 rank・人気帯を検出する条件が無い。ペース持続系 Signal のみ |

### rank7_world

| 項目 | 内容 |
|---|---|
| 設計思想 | 展開・混戦・Chaos > 能力 |
| 現在 Trigger | R5: chaos ∧ high_pace |
| 使用 Signal | `chaos`, `high_pace` |
| 一致評価 | **部分一致** — Chaos / ペース展開は表現。ただし「能力以上」を示す低 TopGap・能力差圧縮は Trigger 未使用（`get_context_top_gap` は別圧関数に存在） |

### mixed_world

| 項目 | 内容 |
|---|---|
| 設計思想 | 複数勝ち筋の共存 |
| 現在 Trigger | R1: 高 sfp + (phase\|chaos\|difficulty) / R3: 高 phase |
| 使用 Signal | sfp, phase, chaos, difficulty |
| 一致評価 | **部分一致** — 複数圧力の OR は「複合」の近似。ただし「複数勝ち筋の共存」そのものの検出ではなく、短距離多頭圧 or phase 高値 |

### bug_world

| 項目 | 内容 |
|---|---|
| 設計思想 | 通常ロジックで説明困難な特殊ケース |
| 現在 Trigger | R6: 高 chaos ∧ 高 difficulty |
| 使用 Signal | chaos, difficulty |
| 一致評価 | **弱い近似** — 極端な混線・難度。説明不能性・例外フラグの明示なし |

## Score 早見（⑥の要約）

| World | Semantic Score | 判定 |
|---|---:|---|
| core | **0.00** | 構造的不一致 |
| midupper | **0.17** | 乖離 |
| midhole | **0.00** | 乖離 |
| rank7 | **0.50** | 部分 |
| mixed | **0.33** | 部分 |
| bug | **0.25** | 弱い近似 |
| **平均** | **0.21** | — |

詳細は `v42-world-meaning.md` / `v42-semantic-gap.md`。

## 制約遵守

Prediction / PE / CE / AI / World / Trigger / Signal / SubWorld / Role / Required / Candidate Pool / Production: **未変更**
