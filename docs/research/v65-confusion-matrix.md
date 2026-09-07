# Version65 — Confusion Matrix

**Date:** 2026-07-28  
**行列:** 行 = Intent GT / 列 = AI Legacy  
**n:** 285

---

## ⑦ AI Confusion Matrix（非ゼロ）

| GT \\ AI | core | midupper | midhole | mixed | GT計 |
|---|---:|---:|---:|---:|---:|
| core | **20** | 17 | 3 | 5 | 45 |
| midupper | 31 | **36** | 4 | 21 | 92 |
| midhole | 20 | 20 | **1** | 9 | 50 |
| rank7 | 1 | 2 | 0 | 4 | 7 |
| mixed | 17 | 15 | 2 | **6** | 40 |
| bug | 6 | 9 | 3 | 7 | 25 |
| unsatisfied | 9 | 11 | 2 | 4 | 26 |
| **AI計** | 104 | 110 | 15 | 56 | 285 |

※ AI 列に rank7 / bug / unsatisfied は **存在しない**（全 0）。

---

## 主な誤分類

| パターン | n | 含意 |
|---|---:|---|
| GT midupper → AI core | 31 | 中上位意図を core へ |
| GT midupper → AI mixed | 21 | |
| GT midhole → AI core | 20 | 中位帯を core/DEFAULT 側へ |
| GT midhole → AI midupper | 20 | |
| GT core → AI midupper | 17 | 能力決着意図を midupper へ |
| GT mixed → AI core | 17 | |
| GT bug → AI midupper/core/mixed | 25 | bug 経路なし |
| GT rank7 → 非 rank7 | 7 | rank7 経路なし（本コーパス Legacy） |

対角合計（一致）= **63**。
