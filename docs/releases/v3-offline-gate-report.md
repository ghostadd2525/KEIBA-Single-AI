# Version 3 — Offline Gate Report

**Date:** 2026-07-24  
**Gate ID:** `v3-offline-gate/1.0`  
**Subject:** Lab Baseline v3（A-01 + A-03 + A-04）on **real labeled_test 285R**  
**Decision:** **FAIL**  
**Scope:** Offline evaluation only · アルゴリズム非変更 · Flag 既定値非変更 · 本番配線なし  
**Artifacts:** `research/v3_lab/baselines/offline_gate/`  
**Harness:** `research/v3_lab/offline_gate.py`

---

## 1. 目的

Lab Baseline v3 を実データで再評価し、Production Readiness の **Offline Gate** を判定する。  
Shadow / Mesh / Production 配線 / Phase 3 には着手しない。

---

## 2. Decision

| 項目 | 結果 |
|------|------|
| **Offline Gate** | **FAIL** |
| Shadow 進行許可 | **No** |
| Production wiring | **False**（不許可のまま） |

| Hard Gate | 結果 |
|-----------|------|
| n = 285 | PASS |
| Treatment Hit > Control Hit | **FAIL**（42 ≯ 59） |
| churn_hit = 0 | **FAIL**（churn = **29**） |

---

## 3. 評価定義

| Arm | 定義 |
|-----|------|
| **Control** | Lab Flag 全 OFF · identity top-1（`model_rank=1`） |
| **Treatment** | Baseline v3 · `F_V3_RANK_D1_ENABLED` + `F_V3_A03_POOL_ADMIT_ENABLED` + `F_V3_A04_SEL_HISTORY_ENABLED` |
| Hit | top pick == winner（Lab 定義） |
| Purchase | 実データでは全レース `purchase_eligible=true`（Delete 境界未適用） |
| ROI | トップ pick に 100 円平坦 · `(return-stake)/stake` |

### 参照（比較不可の別指標）

| 参照 | 値 | 注 |
|------|-----|-----|
| V2 PE-V2-A Hit | **218** | purchase/pool 生存 Hit · Lab top-1 と非互換 |
| Lab Treatment top-1 Hit | **42** | 本 Gate の Treatment |

合成 Lab Hit 279 の外挿は **主張しない**。

---

## 4. Metric Summary

| 指標 | Control | Treatment | Δ |
|------|---------|-----------|---|
| Hit | **59** | **42** | **−17** |
| Purchase | 59 | 42 | −17 |
| rank710 | 37 | 29 | −8 |
| rank46 | 101 | 101 | 0 |
| other | 88 | 113 | +25 |
| ROI | 0.0246 | 0.1807 | +0.1561 |
| churn_hit | — | **29** | — |

詳細: `baselines/offline_gate/offline_gate_metric_summary.json`

---

## 5. Race Diff（要約）

| 区分 | n |
|------|---|
| 改善 | **12** |
| 悪化 | **29** |
| 異常フラグ | 6（deep-rank hit 5 · odds≤1 pick 1） |

| 観察 | 内容 |
|------|------|
| 悪化の典型 | Control が当てた **winner_rank=1** を Treatment が別馬へ promote |
| 改善の典型 | winner_rank 7–13 の深め回収（少数） |

詳細: [`v3-offline-gate-race-diff-report.md`](./v3-offline-gate-race-diff-report.md)

---

## 6. データ品質

| 項目 | 値 |
|------|-----|
| ソース | `phase154` labeled_test + `demo_daily_outputs` |
| jobs | 285 |
| corpus built | **285** |
| status ok / degraded | 268 / 17 |
| 主 issue | `odds_le_1_present` ×17 |
| winner 未一致 | 0 |
| bundle 欠落 | 0 |

詳細: `baselines/offline_gate/data_quality.json`

---

## 7. 異常ケース

| 種別 | n | 解釈 |
|------|---|------|
| treatment_hit_deep_rank_ge_10 | 5 | 深位 promote 成功例（少数） |
| treatment_pick_odds_le_1 | 1 | オッズ欠損/異常レース |

合成コーパス向けの A-03/A-04 promote が、実データの本命場で過剰発火している可能性が高い。

---

## 8. Risk Summary

| ID | 内容 | 等級 |
|----|------|------|
| OG-R1 | 実データで Hit 退行（−17） | **高** |
| OG-R2 | churn 29（本命 Hit 破壊） | **高** |
| OG-R3 | 合成 Lab（Hit 279）との乖離 | **高** |
| OG-R4 | V2 PE Hit 218 と Lab top-1 の指標非互換 | 中（定義上） |
| OG-R5 | odds≤1 の degraded 17R | 低〜中 |

詳細: [`v3-offline-gate-risk-summary.md`](./v3-offline-gate-risk-summary.md)

---

## 9. Production Readiness への含意

| 項目 | 状態 |
|------|------|
| Offline Gate（B1） | **FAIL** |
| A-04 Validation（B2） | PASS（維持） |
| Shadow / Mesh（B3） | **着手禁止**（本 Gate FAIL） |
| PRR Decision | **HOLD 継続**（強化） |

---

## 10. 提出物

| 提出物 | パス |
|--------|------|
| Offline Gate Report | 本ドキュメント |
| Metric Summary | §4 + JSON |
| Race Diff Report | `v3-offline-gate-race-diff-report.md` |
| Risk Summary | `v3-offline-gate-risk-summary.md` |
| Decision | **FAIL** |

---

## 11. 変更範囲

| 追加 | Offline Gate harness · 実コーパスキャッシュ · 文書 |
|------|------|
| **未変更** | A-01/A-02/A-03/A-04 ロジック · Feature Flag 既定 · Production · API · UI · Ops · Explain |

---

## 12. Follow-up（解析のみ）

Lab Hit 279 との乖離は **Lab / Offline Divergence Analysis** で説明済み（実装なし）。  
主因候補: Admission A-03 実データ過剰発火。詳細: [`v3-lab-offline-divergence-report.md`](./v3-lab-offline-divergence-report.md)。

---

## 13. 停止

**Offline Gate 完了。Decision = FAIL。**  
Shadow / Mesh · Production 配線 · Phase 3 には着手しない。
