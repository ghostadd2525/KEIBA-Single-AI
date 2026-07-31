# Version67 — Condition Analysis

**Date:** 2026-07-28  
**定義:**  
- **Precision** = P(Intent GT == Rule.world \| 条件 True)  
- **Recall** = P(条件 True \| Intent GT == Rule.world)  
**n:** 285

---

## ③ / ④ Condition Precision & Recall

### R1 系（world = mixed）

| Condition | Pass n | Pass率 | Precision | Recall | Missing率 |
|---|---:|---:|---:|---:|---:|
| R1.sfp≥0.72 | 56 | 19.6% | **10.7%** | 15.0% | 15.8% |
| R1.phase≥0.48 | 163 | 57.2% | 12.3% | 50.0% | 15.8% |
| R1.chaos≥0.42 | 157 | 55.1% | 10.2% | 40.0% | 15.8% |
| R1.difficulty≥0.42 | 225 | **78.9%** | 14.7% | **82.5%** | 15.8% |
| R1.OR_bundle | 226 | **79.3%** | 14.6% | 82.5% | — |
| R1.full | 56 | 19.6% | **10.7%** | 15.0% | — |

**測定:** `R1.full` の Pass n = `R1.sfp` の Pass n（56）。sfp が True のとき OR は事実上ブロックしない。

GT mixed の FN bottleneck: **sfp_fail 27** / both 7 / OR_only **0**。

### R7 系（world = midupper）

| Condition | Pass n | Pass率 | Precision | Recall | Missing率 |
|---|---:|---:|---:|---:|---:|
| R7.difficulty≥0.50 | 178 | **62.5%** | **34.3%** | **66.3%** | 15.8% |

単一条件 = Rule 全体。Precision 34% でも FP 117（コーパス）/ Trigger FP 57。

### R8 系（world = core）

| Condition | Pass n | Pass率 | Precision | Recall |
|---|---:|---:|---:|---:|
| R8.DEFAULT fires | 104 | 36.5% | **19.2%** | 44.4% |

---

## ⑤ Dead / 弱選択 Condition

| Condition | 判定 | 根拠 |
|---|---|---|
| R1.OR_bundle | **弱選択（ほぼ常時 True 寄り）** | Pass率 79.3%。R1 FP 50 中 49+ で chaos/difficulty 通過 |
| R1.difficulty≥0.42 | **弱選択** | Pass率 78.9%、Recall 高・Precision 低 |
| R1.phase / chaos OR 腕 | **R1 発火時に冗長** | sfp 通過後ほぼ追加制約にならない |
| R8.DEFAULT | **構造的常時候補** | 正条件なし。R1–R7 FAIL なら必ず True |
| 常に False の原子 | **なし**（対象 3 Rule 内） | Pass率 ≤5% の原子なし |

「Dead」= 完全固定 True/False ではなく、**選別に寄与しない／構造上不可避**を含む。
