# Phase I5 — Operation Validation

**Date:** 2026-07-29

---

## Runbook dry-run

| Runbook step | Status | Notes |
|---|---|---|
| Flag ON（staging beta） | PASS（手順・harness） | 本番 beta は未キー / OFF |
| `GET /api/ops/single-detail` | PARTIAL | コード PASS · 本番 OPS_CLOSED |
| Metrics 解釈（expected vs error FB） | PASS | I4 metrics def |
| ALT-SD* → runbook anchor | PASS | docs/ops/single-detail-runbook.md |
| Rollback Flag OFF | PASS | |
| List LOCK 確認 | PASS | races.html / cache v4 |

## Metrics update

| Metric | Validated |
|---|---|
| latency p95 | unit |
| timeout / 5xx / http_error | unit |
| prediction_fallback count | unit |
| error_fallback_of_attempted | unit |
| flag_on_path | unit（endpoint 近似） |

## Dashboard

| Item | Status |
|---|---|
| Design doc | PASS |
| `single_detail_ops` in monitor | PASS（repo） |
| Live ops console tile | PARTIAL（本番閉鎖） |

## Scope lock

| Frozen | Confirmed |
|---|---|
| Core / Consumer / Prediction / UI | No product code change in I5 |
| Race List Cache | Untouched |
| race.html only | List out of scope |
