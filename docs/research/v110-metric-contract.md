# Version110 — Metric Contract（解釈 A · V1 定義）

**Date:** 2026-07-29  
**Status:** ADOPTED（Interpretation A）  
**Parent:** `v110-prediction-completeness-charter.md`  
**Out of scope:** ROI · Ticket · Decision · `unsatisfied` 削減 · Affinity 昇格率

---

## 定義 ID

全レポートは `definition_id: v1_interpretation_a` を明記する。

Version2 Positive-only 定義は **本票では使用禁止**（混在報告禁止）。

---

## 指標

### Prediction Returned（PR-100）— 主目標

| 項目 | 内容 |
|---|---|
| 定義 | 対象 `race_id` に対し公式 Prediction（Rank/Score 本文）が返った割合 |
| 目標 | **1.0** |
| 不合格 | Bundle 不在 · Feature 未ロード · 収集 NOT READY · **NM/Residual を理由にした withhold（禁止）** |
| 非混同 | Ticket SKIP / Decision 見送りは含めない |

### Prediction Coverage（PC-C）

| 項目 | 内容 |
|---|---|
| 定義 | Rank/Score が全出走に有効なレース割合 |
| 目標 | **1.0** |
| 既存 | V99/V100 `prediction_complete` |

### World Coverage（WC-C）

| 項目 | 内容 |
|---|---|
| 定義 | `world_id` が非 null（**`unsatisfied` 含む**）の割合 |
| 目標 | **1.0** |

### Unassigned Race（UA-0）

| 項目 | 内容 |
|---|---|
| 定義 | `world_id` **欠損**レース数 |
| 目標 | **0** |
| 非定義 | `unsatisfied` を Unassigned に数えない |

---

## 観測（非 KPI）

Near Miss / Affinity / Residual / transition — Completeness 説明用。  
**昇格成功率が KPI になってはならない。**
