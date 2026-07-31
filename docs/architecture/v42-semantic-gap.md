# Version42 — Semantic Gap

**Date:** 2026-07-28  
**Type:** Research / Audit only

## ④ Missing Semantic（設計にあるが Trigger に無い）

| 設計概念 | 想定 World | Trigger 出現 | コード上の別所在 |
|---|---|---|---|
| 能力決着（正の検出） | core | **無し**（DEFAULT のみ） | LGBM=能力（docstring） |
| TopGap 大 | core | **無し** | `get_context_top_gap` は存在。World Trigger 未接続 |
| 能力差 | core | **無し** | — |
| レース格（G1等） | core | **無し** | `race_class`/`grade` は metadata・別監査に存在 |
| 長距離 | core | **無し**（正条件として） | distance は sfp の短距離側 |
| 上位能力馬中心 | midupper | **無し** | difficulty は脚難度であり上位能力ではない |
| 適性 | midupper | **無し** | — |
| 中位評価馬の勝ち筋 | midhole | **無し** | late_stop/sustained のみ |
| 中位 rank / 人気帯 | midhole | **無し** | — |
| 「能力より展開」の能力側抑制（低 TopGap） | rank7 | **無し**（Trigger） | large-field top_gap **小** 圧は別関数 |
| 複数勝ち筋の明示的共存 | mixed | **無し**（明示） | 複合圧力の OR 近似のみ |
| 説明不能・例外フラグ | bug | **無し** | 高 chaos∧difficulty 近似のみ |

## ⑤ Wrong Semantic（Trigger にあるが設計と薄い／逆）

| Trigger 条件 | 所属 World | 設計との関係 | 根拠 |
|---|---|---|---|
| `short_field_pressure` 高 | midupper / mixed | **設計の midupper（上位能力+適性）と薄い**。短距離×多頭の route 圧 | `calc_short_field_pressure` docstring: 「能力スコアではなく…文脈圧」 |
| `difficulty` 高 → midupper (R7) | midupper | **脚難度高 = 上位能力中心** とは言えない。難度高はむしろ非・能力単純決着寄り | `race_leg_difficulty` |
| distance via sfp（短距離） | midupper/mixed | core 設計の「長距離」と **逆方向** | sfp は ≤1600/1400 で上昇 |
| core = DEFAULT | core | 設計の独立勝ち筋と **意味が逆**（残余ラベル） | R8 parts=[] |
| soft `core = 1 - max(others)` | core（research fitness） | 同様に残余 | `trigger_proximity_fitness` |
| R3 `phase` 高 → mixed | mixed | phase 単体高が「複数勝ち筋共存」かは薄い | phase_transition は pace 系合成 |

## Gap 構造図

```text
設計: World = 勝ち筋（能力 / 上位+展開 / 中位 / Chaos優位 / 共存 / 例外）
         │
         ▼
実装: World = survival / route 圧力の first-match 分類
         │
         ├── 正の条件: sfp, difficulty, phase, late_stop, sustained, chaos, high_pace
         ├── 能力決着系: TopGap / 格 / 能力差  → Trigger 外（または別圧）
         └── core: 条件なし DEFAULT
```

## V41 との接続（意味論）

V41: core 75% = R1–R7 FAIL → R8。

V42: それは閾値問題以前に、**core に「能力決着」意味が Trigger へ一度も符号化されていない**ため、DEFAULT 以外の帰結になり得ない、という構造ギャップである。
