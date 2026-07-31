# Phase I5 — Staging Rehearsal Report

**Date:** 2026-07-29  
**Mode:** Staging Rehearsal（Production と同手順の Flag ON 検証）  
**Cutover:** **未実行**  
**Freeze:** Core / Consumer / Prediction / UI layout / Race List Cache / Contract

---

## Verdict

| 項目 | 結果 |
|---|---|
| **Repo Staging Rehearsal** | **PASS** |
| **Client Harness（Flag ON 手順）** | **PASS（8/8）** |
| **Alert / Metrics unit** | **PASS（ALT-SD01..05 発火確認）** |
| **Production live Flag ON** | **NOT EXECUTED**（I3/I4 未デプロイ + Research Week OPS_CLOSED） |
| **Production Cutover** | **NO-GO**（下記 Recommendation） |

---

## 確認項目

| # | 項目 | Status | Evidence |
|---|---|---|---|
| 1 | Feature Flag ON | **PASS**（harness） | `single_ai_detail` ON → Single detail path |
| 2 | Single API 呼出 | **PASS**（harness） | `POST /api/single/detail/:id` |
| 3 | Prediction Fallback | **PASS** | no-core envelope + error path |
| 4 | Timeout | **PASS** | AbortError → `prediction_fallback` / `TIMEOUT` |
| 5 | Rollback | **PASS** | Flag OFF → Single HTTP なし |
| 6 | Alert 発火 | **PASS**（unit） | ALT-SD01..05 |
| 7 | Metrics 更新 | **PASS**（unit） | `recordSingleDetailEvent` → snapshot |
| 8 | Dashboard 反映 | **PARTIAL** | probe 配線 PASS · 本番 `/api/ops/*` は OPS_CLOSED |
| 9 | Runbook 手順 | **PASS** | docs/ops/single-detail-*.md 存在・手順整合 |

---

## Production baseline（Client Diagnosis）

| 観測 | 結果 |
|---|---|
| `https://expect-keiba.com/race` | 詳細 UI 表示可 · **single-detail.js 未配線**（Prediction のみ） |
| Prod `config/beta.json` | `single_ai_detail` **キーなし** → DEFAULT OFF |
| Prod `races.html` | `expect_race_list_cache_v4` 維持 · Single なし |
| `/api/ops/single-detail` | **503 OPS_CLOSED**（Research Week） |
| Repo `public/race.html` | I3 配線済み（未デプロイ差分） |

→ 本番で Flag ON リハーサルは **デプロイ前に不可**。本 I5 は **repo + harness + ops unit** で手順エビデンスを取得。

---

## Artifacts

| File |
|---|
| `docs/research/i5-artifacts/rehearsal-harness.html` |
| `docs/research/i5-artifacts/client-harness-result.json` |
| `docs/research/i5-artifacts/staging-rehearsal-report.json` |
| `services/win5-ai/tests/site_integration/test_i5_staging_rehearsal.py` |

## Related deliverables

- [Alert Validation](./v109-i5-alert-validation.md)
- [Rollback Validation](./v109-i5-rollback-validation.md)
- [Operation Validation](./v109-i5-operation-validation.md)
- [Production Recommendation](./v109-i5-production-recommendation.md)
- [Governance](./v109-i5-governance.md)
- [I2 Re-evaluation](./v109-i2-cutover-reevaluation-after-i5.md)
