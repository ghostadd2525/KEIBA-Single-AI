# Version45 — World Compliance（①–⑦ 詳細）

**Date:** 2026-07-28  
**Parent:** `v45-trigger-spec-gap.md`

---

## `core_world` — Compliance **0%**

| # | 監査項目 | V44 | Production | 判定 |
|---|---|---|---|---|
| ① | Positive Match | `CORE_MUST` 正検出 | 正条件なし。最終 `return "core_world"` | **FAIL** |
| ② | DEFAULT 経路 | 禁止 | R8 / else → core | **FAIL**（経路が存在） |
| ③ | Must Signal | top_gap↑ AND ability_separation↑ | いずれも classify 未使用 | **FAIL** |
| ④ | Aux Signal | grade / 長距離 / sfp↓ support | core 経路で未使用 | **FAIL** |
| ⑤ | Forbidden 不使用 | DEFAULT・高chaos・高sfp・late∧sust を正にしない | DEFAULT が定義本体 | **FAIL** |
| ⑥ | Logic Form | GapHigh AND SeparationLarge AND NOT Exclude | 残余代入 | **FAIL** |
| ⑦ | 未充足時 | unsatisfied | core に落とす | **FAIL** |

点数: 0/7 → **0%**

---

## `midupper_world` — Compliance **36%**

| # | 監査項目 | V44 | Production | 判定 |
|---|---|---|---|---|
| ① | Positive Match | 正の MIDUPPER_MATCH | R2 / R7 で正帰還あり | **PARTIAL**（形式のみ） |
| ② | DEFAULT 経路 | midupper への DEFAULT なし | なし（difficulty 正条件） | **PASS** |
| ③ | Must | UPPER ∧ DEV ∧ APT | 上位能力帯・適性なし。sfp/difficulty のみ | **FAIL** |
| ④ | Aux | difficulty / sfp / top_gap 中が support | difficulty・sfp が本体条件 | **PARTIAL**（信号は出るが役割違反） |
| ⑤ | Forbidden 回避 | difficulty のみ禁止 | R7 = difficulty のみ → midupper | **FAIL** |
| ⑥ | Logic Form | 3軸 AND | sfp∧difficulty / difficulty | **FAIL** |
| ⑦ | 未充足時 | 当該不成立（global は unsatisfied） | 不成立なら次ルールへ（global は core） | **PARTIAL** |

点数: 0.5+1+0+0.5+0+0+0.5 = 2.5/7 → **36%**

---

## `midhole_world` — Compliance **36%**

| # | 監査項目 | V44 | Production | 判定 |
|---|---|---|---|---|
| ① | Positive Match | 正検出 | R4 あり | **PARTIAL** |
| ② | DEFAULT 経路 | なし | なし | **PASS** |
| ③ | Must | mid_eval_band_open ∧ top_monopoly↓ | 未使用 | **FAIL** |
| ④ | Aux | late_stop / sustained は Aux | R4 の **Must 本体** | **PARTIAL** |
| ⑤ | Forbidden 回避 | late∧sust を定義本体にしない | 定義本体が late∧sust | **FAIL** |
| ⑥ | Logic Form | MidBandOpen AND WeakTopMonopoly | late_stop AND sustained | **FAIL** |
| ⑦ | 未充足時 | 上記と同様 | 次ルールへ / 最終 core | **PARTIAL** |

点数: 2.5/7 → **36%**

---

## `rank7_world` — Compliance **64%**

| # | 監査項目 | V44 | Production | 判定 |
|---|---|---|---|---|
| ① | Positive Match | 正検出 | R5 chaos∧high_pace | **PASS** |
| ② | DEFAULT 経路 | なし | なし | **PASS** |
| ③ | Must | chaos↑ ∧ pace_conflict↑ ∧ ability_subordinate | chaos・high_pace あり。top_gap↓ **なし** | **PARTIAL** |
| ④ | Aux | 多頭 / 短〜中距離 / difficulty | classify の rank7 条件に未使用 | **FAIL** |
| ⑤ | Forbidden 回避 | 高 TopGap 正条件にしない / difficulty のみにしない | R5 は遵守 | **PASS** |
| ⑥ | Logic Form | 3項 AND + Exclude | 2項 AND（ability_subordinate 欠） | **PARTIAL** |
| ⑦ | 未充足時 | 同上 | 同上 | **PARTIAL** |

点数: 1+1+0.5+0+1+0.5+0.5 = 4.5/7 → **64%**

---

## `mixed_world` — Compliance **36%**

| # | 監査項目 | V44 | Production | 判定 |
|---|---|---|---|---|
| ① | Positive Match | 正検出 | R1 / R3 あり | **PARTIAL** |
| ② | DEFAULT 経路 | なし | なし | **PASS** |
| ③ | Must | multi_path OR unexplained | 競合カウント・説明不能フラグなし | **FAIL** |
| ④ | Aux | 複合圧力バンドル | sfp/phase/chaos/difficulty が本体 | **PARTIAL** |
| ⑤ | Forbidden 回避 | phase 単独定義禁止 | R3 = phase 単独 → mixed | **FAIL** |
| ⑥ | Logic Form | MULTI_PATH | 圧力 AND/OR・phase 単体 | **FAIL** |
| ⑦ | 未充足時 | 同上 | 同上 | **PARTIAL** |

点数: 2.5/7 → **36%**

---

## `bug_world` — Compliance **50%**

| # | 監査項目 | V44 | Production | 判定 |
|---|---|---|---|---|
| ① | Positive Match | ExceptionFlag 正検出 | R6 あり | **PARTIAL** |
| ② | DEFAULT 経路 | bug≠残余 | 残余は core（bug ではない） | **PASS** |
| ③ | Must | exception_flag | なし | **FAIL** |
| ④ | Aux | 極端 chaos∧difficulty | R6 本体 = chaos∧difficulty | **PARTIAL** |
| ⑤ | Forbidden 回避 | 「非該当=bug」禁止 / 高chaosのみ禁止 | 非該当→core。R6 は両信号 | **PASS** |
| ⑥ | Logic Form | ExceptionFlag AND NOT residual | 極端値 AND | **FAIL** |
| ⑦ | 未充足時 | 同上 | 同上 | **PARTIAL** |

点数: 0.5+1+0+0.5+1+0+0.5 = 3.5/7 → **50%**

---

## Compliance Ranking

| Rank | World | Compliance |
|---:|---|---:|
| 1 | rank7_world | 64% |
| 2 | bug_world | 50% |
| 3 | midupper_world | 36% |
| 3 | midhole_world | 36% |
| 3 | mixed_world | 36% |
| 6 | core_world | **0%** |
| — | **平均** | **37%** |
