# Version71 — Intent Mapping（4 者対応表）

**Date:** 2026-07-28  
**Parent:** `v71-intent-gt-audit.md`  
**Scope:** 定義マッピングのみ。実装変更なし。

凡例: **一致** / **部分** / **不一致** / **非対象**

---

## `core_world`

| 軸 | V43 | V44 | V69 | Intent GT | 判定 |
|---|---|---|---|---|---|
| Purpose | 能力決着の独立勝ち筋 | Positive AbilityResolution | 同左 | 「上位が勝ち切る」 | **部分**（結果条件が付加） |
| Must | top_gap 大 + 能力差 | Gap↑ ∧ Sep↑ | 同左 | Gap↑ ∧ Sep↑ ∧ **wr≤3** | **不一致**（outcome Must 化） |
| Forbidden | DEFAULT 残余 | DEFAULT 禁止 | DEFAULT 廃止 | DEFAULT 非評価 | **非対象** |
| Exclude | 高 chaos / sfp 等 | chaos∨sfp∨… | 同左 | なし | **不一致** |
| Aux | grade / 距離 / 低 sfp | 同左 | 同左 | なし | **不一致** |

---

## `midupper_world`

| 軸 | V43 | V44 | V69 | Intent GT | 判定 |
|---|---|---|---|---|---|
| Purpose | 上位能力 + 展開 + 適性 | UPPER∧DEV∧APT | 同左 | core/rank7 中間（rank 帯） | **不一致** |
| Must | 3 軸 | 3-AND | UPPER∧DEV∧APT | **wr∈[2,6]**（±gap） | **不一致** |
| Aux | difficulty 中〜 | difficulty Aux | difficulty Aux | 不使用 | **部分**（GT が Aux すら見ない） |
| Forbidden | difficulty のみ | 同左 | 同左 | 測定外 | **非対象** |

---

## `midhole_world`

| 軸 | V43 | V44 | V69 | Intent GT | 判定 |
|---|---|---|---|---|---|
| Purpose | 中位まで勝ち筋 | MidOpen∧WeakMono | V44 Form | 中位帯が開く | **部分** |
| Must | 中位帯 + 上位独占弱 | mid_open↑ ∧ mono↓ | 同左 | wr∈[5,10]（±mid_open） | **部分**（WeakMono 欠落しがち） |
| Forbidden | late∧sust を本体に | Aux のみ | 同左 | late/sust 不使用 | **部分** |

---

## `rank7_world`

| 軸 | V43 | V44 | V69 | Intent GT | 判定 |
|---|---|---|---|---|---|
| Purpose | 展開・混戦が能力以上 | Chaos∧Pace∧Sub | V44 Form | 低 gap・能力どおりになりにくい | **部分**（文言のみ） |
| Must | chaos + 展開圧 + 劣後 | 3-AND | 同左 | gap↓ ∧ **wr 7–10** | **不一致**（chaos/pace 欠落） |
| Design share | 15% 参照 | — | — | **2.5%** (7) | **不一致** |

---

## `mixed_world`

| 軸 | V43 | V44 | V69 | Intent GT | 判定 |
|---|---|---|---|---|---|
| Purpose | 複数勝ち筋共存 | multi_path / unexplained | multi_path MATCH | 強スコア 2+ | **部分** |
| Must | 2+ 意味競合 | \|PRIMARY\|≥2 | 同左 | outcome スコアの 2+ | **不一致**（入力が Signal MATCH でない） |
| Forbidden | phase 単独 | 圧力単軸禁止 | 圧力 Aux | 圧力不使用 | **部分** |

---

## `bug_world`

| 軸 | V43 | V44 | V69 | Intent GT | 判定 |
|---|---|---|---|---|---|
| Purpose | 説明困難な特殊 | ExceptionFlag | exception 欠落⇒不成立 | 深穴 | **不一致** |
| Must | 例外標識 | exception↑ | 同左 | **wr≥11** | **不一致** |

---

## `unsatisfied` / 残余

| 軸 | V43 | V44 | V69 | Intent GT | 判定 |
|---|---|---|---|---|---|
| 意味 | （暗黙）未充足可 | Must 未充足 | \|M\|=0 | score 全 <0.5 | **部分** |
| vs core DEFAULT | Forbidden | 禁止 | 廃止 | GT は DEFAULT を測らない | **測定ギャップ** |

---

## サマリスコア（World × 一致度）

| World | V43↔V44 | V44↔V69 | V43/V44/V69↔Intent GT |
|---|---|---|---|
| core | 一致 | 一致 | **不一致** |
| midupper | 一致 | 一致 | **不一致** |
| midhole | 一致 | 一致 | 部分 |
| rank7 | 一致 | 一致 | **不一致** |
| mixed | 一致 | 一致 | 部分〜不一致 |
| bug | 一致 | 一致 | **不一致** |
| unsatisfied | 一致 | 一致 | 部分（定義は似るが GT 発生条件が異なる） |

**総合:** ①②③は同一系統。④のみ別系統（Outcome-band Intent）。
