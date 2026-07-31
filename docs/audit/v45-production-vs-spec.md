# Version45 — Production vs V44 Spec（対応表）

**Date:** 2026-07-28  
**Type:** Audit mapping only

## Side-by-side

| World | V44 Logic Form（要約） | Production Form | Must 差分 | Forbidden 抵触 |
|---|---|---|---|---|
| core | top_gap↑ ∧ separation↑ ∧ ¬Exclude | `else → core_world` | Must 全滅 | DEFAULT 本体 |
| midupper | UPPER ∧ DEV ∧ APT | `(sfp∧diff)` OR `diff` | UPPER/APT 欠。DEV は sfp 近似のみ | R7 difficulty のみ |
| midhole | mid_band∧¬top_monopoly | `late_stop∧sustained` | Must 全滅。pace が本体 | Aux の Must 昇格 |
| rank7 | chaos∧pace∧ability↓ | `chaos∧high_pace` | ability↓（top_gap）欠 | なし（当該範囲） |
| mixed | multi_path≥2 OR unexplained | `(sfp∧OR)` OR `phase` | multi_path 欠 | phase 単独 |
| bug | exception_flag | `chaos∧difficulty` | exception 欠 | 定義が Aux 昇格 |

## Signal Usage Matrix（Production classify）

| Signal | 使用 World（Prod） | V44 での正規役割（主） | Gap |
|---|---|---|---|
| short_field_pressure | mixed, midupper | Aux（Dev）/ core では Forbid+ | midupper Must 代用 |
| phase | mixed | Aux / mixed 単独 Forbid | R3 抵触 |
| chaos | mixed, rank7, bug | rank7 Must / 他は Aux・Forbid | bug Must 代用 |
| difficulty | mixed, midupper, bug | Aux（単独 midupper Forbid） | R7 抵触 |
| late_stop | midhole | midhole Aux | Must 昇格 |
| sustained | midhole | midhole Aux | Must 昇格 |
| high_pace | rank7 | rank7 Must | 部分一致 |
| top_gap | **未使用** | core Must↑ / rank7 Must↓ | 最大欠落 |
| ability_separation | **未使用** | core Must | 欠落 |
| upper_ability_band | **未使用** | midupper Must | 欠落 |
| aptitude_fit | **未使用** | midupper Must | 欠落 |
| mid_eval_band | **未使用** | midhole Must | 欠落 |
| multi_path_active | **未使用** | mixed Must | 欠落 |
| exception_flag | **未使用** | bug Must | 欠落 |

## Evaluation Order

| 段 | V44 | Production |
|---|---|---|
| 1 | Exclusion | なし（優先度 first-match のみ） |
| 2 | Must 充足（並列評価可） | 逐次 if で最初の PASS |
| 3 | 複数充足 ⇒ mixed | 単一 World を即 return |
| 4 | Aux は support のみ | 実質 Must 条件に混在 |
| 5 | 未充足 ⇒ unsatisfied | **core_world** |

## Agreement vs Gap（一文）

- **最も近い:** `rank7_world`（chaos∧pace の正検出が仕様の一部と一致）
- **最も遠い:** `core_world`（仕様の正検出に対し Production は DEFAULT のみ）
- **共通構造ギャップ:** Must 概念の多数が classify に存在せず、未充足が常に core へ吸収される

## Note

本表は適合監査である。Threshold の是非・修正方針は範囲外。
