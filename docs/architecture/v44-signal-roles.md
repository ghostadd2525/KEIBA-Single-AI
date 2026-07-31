# Version44 — Signal Roles（Must / Aux / Forbidden）

**Date:** 2026-07-28  
**Parent:** `v44-world-trigger-specification.md`  
**Source contracts:** V43 Required/Optional/Forbidden; V33 naming where applicable

## Role Definitions

| Role | Trigger 仕様上の扱い |
|---|---|
| **Must** | Logic Form の成立に必須。欠落 ⇒ 当該 World unsatisfied |
| **Aux** | Must 成立後の支持・境界。Must 欠落を埋めない |
| **Forbidden-as-positive** | 当該 World の成立条件に使ってはならない |
| **N/A** | 当該 World 仕様で役割を定めない |

---

## Matrix

| Signal / Concept | core | midupper | midhole | rank7 | mixed | bug |
|---|---|---|---|---|---|---|
| `top_gap`↑ | **Must** | Aux | Forbid+ | Forbid+ | N/A | N/A |
| `top_gap`↓ | Forbid+ | Aux | Aux | **Must** | Aux | N/A |
| ability_separation↑ | **Must** | Aux | Aux | Aux | N/A | N/A |
| upper_ability_band | Forbid+* | **Must** | Forbid+ | Forbid+ | N/A | N/A |
| mid_eval_band_open | Forbid+ | Forbid+ | **Must** | Aux | N/A | N/A |
| top_monopoly↓ | — | — | **Must** | Aux | N/A | N/A |
| aptitude_fit | N/A | **Must** | Aux | N/A | N/A | N/A |
| `chaos`↑ | Forbid+ | Aux | Aux | **Must** | Aux | Aux** |
| `high_pace` / pace_conflict | Forbid+*** | Aux(Dev) | Aux | **Must** | Aux | N/A |
| `short_field_pressure`↑ | Forbid+ | Aux(Dev) | N/A | Aux | Aux | N/A |
| `difficulty` | Forbid+**** | Aux | N/A | Aux | Aux | Aux** |
| `phase` | N/A | Aux(Dev) | N/A | Aux | Aux***** | N/A |
| `late_stop` | Forbid+(∧sust) | N/A | Aux | N/A | N/A | N/A |
| `sustained` | Forbid+(∧late) | N/A | Aux | N/A | N/A | N/A |
| race_grade | Aux | Aux | N/A | N/A | N/A | Aux |
| distance 長 | Aux | N/A | N/A | N/A | N/A | N/A |
| multi_path_active | Forbid+ | Forbid+ | Forbid+ | Forbid+ | **Must** | N/A |
| exception_flag | Forbid+ | N/A | N/A | N/A | N/A | **Must** |
| unlabeled_residual / DEFAULT | **Forbid+** | — | — | — | — | **Forbid+** |

\* core で「上位能力帯」単独を勝ち筋全体の定義にしてはならない（能力決着は gap/separation）。  
\*\* bug では極端値として Aux のみ。Must ではない。  
\*\*\* high_pace 単独を core 正条件にしない。  
\*\*\*\* difficulty 単独で core / midupper を定義しない。  
\*\*\*\*\* phase 単独で mixed を定義しない（Forbid+ as sole definer）。

---

## Must Sets（再掲）

| World | Must set（すべて必要） |
|---|---|
| core | `top_gap`↑, ability_separation↑ |
| midupper | upper_ability_band, development_pressure, aptitude_fit |
| midhole | mid_eval_band_open, top_monopoly↓ |
| rank7 | `chaos`↑, pace_conflict↑, ability_subordinate（`top_gap`↓ 等） |
| mixed | multi_path_active **または** unexplained_single |
| bug | exception_flag（かつ unlabeled_residual ではないこと） |

---

## Aux Sets

| World | Aux（例） |
|---|---|
| core | race_grade, distance 長, sfp↓ |
| midupper | difficulty, sfp 中, top_gap 中 |
| midhole | late_stop, sustained, chaos 中 |
| rank7 | field_size 多頭, distance 短〜中, difficulty |
| mixed | 複合圧力バンドル（sfp/phase/chaos/difficulty 同時） |
| bug | chaos↑↑ ∧ difficulty↑↑ |

---

## Notes on unnamed concepts

`upper_ability_band` / `mid_eval_band_open` / `aptitude_fit` / `multi_path_active` / `exception_flag` は **意味仕様上の Must 概念**である。  
V33 搬送キーへの物理マッピングや新規 Signal 実装は V44 範囲外（Signal 変更禁止）。

## Guardrails

- 役割定義のみ。閾値・実装・Signal 追加手順なし。
