# ISSUE-REPICK-V2-001: RePick v2 実装（Flag + sidecar + journal + AB）

- Priority: **P0**
- Status: **done**（実装完了 / **AB FAIL → Flag OFF 維持**）
- Baseline: Phase255 / V1 — Flag OFF = 恒等
- Series: Version2 Product（Win5 Optimizer / RePick 段）
- Created: 2026-07-21
- Closed: 2026-07-21

## ゲート

| 文書 | Status |
|------|--------|
| [設計レビュー](../repick-v2-design-review.md) | 条件付き承認 |
| [Exit Criteria](../repick-v2-exit-criteria-contract.md) | **Approved** |
| [Stop Criteria](../repick-v2-stop-criteria-contract.md) | **Active** |
| [AB Report](../repick-v2-ab-report.md) | **AB_PASS=False / Flag OFF** |

---

## 実装要約

1. `v2_repick_v2.py` — `WIN5_REPICK_V2_ENABLED` 既定 OFF、匿名 G1′ NEAR、N不変 max1、journal  
2. `demo_ticket_optimizer_core.py` — thin hook  
3. `test_repick_v2.py` — Unit PASS（5/5）  
4. `_run_repick_v2_ab_evaluation.py` — 正式 AB 実行  

**非変更:** Collector / ETL / Prediction V1 / Pool / Entry / Delete

## 結果

| 項目 | 結果 |
|------|------|
| Unit | PASS |
| AB | **FAIL**（churn_hit/g1/race + Control Hit 215≠216） |
| R_G1 | 4/11（改善率ゲートのみ PASS） |
| Canary | 不可 |
| Flag | **OFF 維持** |
| Stop 連続 FAIL | 1（ST-F1 未達） |

詳細: [repick-v2-ab-report.md](../repick-v2-ab-report.md)
