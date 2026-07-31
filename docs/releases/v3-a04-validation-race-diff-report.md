# Version 3 — A-04 Validation Race Diff Report

**Date:** 2026-07-24  
**Validation ID:** `v3-a04-validation/1.0`  
**Control:** Lab Baseline v2（A-01 + A-03）Hit 255  
**Treatment:** Baseline v2 + `F_V3_A04_SEL_HISTORY_ENABLED` Hit 279  
**Parent:** [`v3-a04-validation-report.md`](./v3-a04-validation-report.md)  
**JSON:** `research/v3_lab/baselines/a04_validation/a04_race_diff.json`

---

## 1. 要約（Hard Gate パネル）

| 区分 | n |
|------|---|
| 改善 | **24**（Boundary 14 + Reorder 10） |
| 悪化 | **0** |
| churn_hit | **0** |
| unchanged_hit | 255 |
| unchanged_miss | 6（Delete） |

A-04 solo パネルも同一層構成（Boundary14 + Reorder10 · 悪化0）で再現。

---

## 2. 改善レース（Boundary 14）

| race_id | winner_rank | 層 |
|---------|-------------|-----|
| a03-285-247 | 3 | Boundary |
| a03-285-248 | 3 | Boundary |
| a03-285-249 | 3 | Boundary |
| a03-285-250 | 3 | Boundary |
| a03-285-251 | 3 | Boundary |
| a03-285-252 | 3 | Boundary |
| a03-285-253 | 3 | Boundary |
| a03-285-254 | 3 | Boundary |
| a03-285-255 | 3 | Boundary |
| a03-285-256 | 3 | Boundary |
| a03-285-257 | 3 | Boundary |
| a03-285-258 | 3 | Boundary |
| a03-285-259 | 3 | Boundary |
| a03-285-260 | 3 | Boundary |

---

## 3. 改善レース（Reorder 10）

| race_id | winner_rank | 層 |
|---------|-------------|-----|
| a03-285-261 | 2 | Reorder |
| a03-285-262 | 2 | Reorder |
| a03-285-263 | 2 | Reorder |
| a03-285-264 | 2 | Reorder |
| a03-285-265 | 2 | Reorder |
| a03-285-266 | 2 | Reorder |
| a03-285-267 | 2 | Reorder |
| a03-285-268 | 2 | Reorder |
| a03-285-269 | 2 | Reorder |
| a03-285-270 | 2 | Reorder |

---

## 4. 悪化レース

なし。

---

## 5. 非対象（残 miss）

Delete 6（`a03-285-280` … `285`）は両アームとも miss（Accuracy 対象外）。

---

## 6. 再現確認

Validation 2 ラウンドおよび両パネルで Boundary14 / Reorder10 / 悪化0 が一致。
