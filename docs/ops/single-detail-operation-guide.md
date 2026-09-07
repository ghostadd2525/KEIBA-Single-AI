# Single Detail — Operation Guide (I4)

**Phase:** I4 Operational Readiness  
**Scope:** `single_ai_detail` Feature Flag path only  
**Non-goals:** Core / Consumer / Prediction / UI layout / Race List Cache / Production Cutover

---

## Purpose

Single AI Detail を **安全に観測・警報できる状態** にする。Cutover は Alert 完了後に I2 を再評価する。

## Surfaces

| Surface | Role |
|---|---|
| `GET /api/ops/single-detail` | Metrics snapshot + ALT-SD* evaluation |
| `GET /api/ops/dashboard` / `GET /api/ops/monitor` | Includes `single_detail_ops` probe + SD alerts merge |
| `POST /api/single/detail/:raceId` | Flag ON BFF resolve（metrics 記録点） |
| Log line `[single-detail-ops] {...}` | Structured resolve log |
| Flag `single_ai_detail` | Product gate（default OFF） |

## Daily checks

1. Flag default remains **OFF** in `beta.json` / `ui-features.js` until Cutover approved.
2. `GET /api/ops/single-detail`（admin or `X-Ops-Monitor-Key`）→ `alert_eval.deferred` or empty alerts.
3. Confirm list path never hits Single: `races.html` に `single-detail` なし（LOCK）。
4. On staging Flag ON rehearse: watch `rates.error_fallback_of_attempted`, `latency_ms_p95`, `timeouts`.

## Metric interpretation

| Metric | Meaning |
|---|---|
| `requests_total` / `flag_path_hits` | Detail Flag path hits（endpoint is Flag ON only） |
| `rates.flag_on_path` | Always ~1.0 for this endpoint; **not** site-wide Flag ON % |
| `single_attempted` | Core + AI proxy present → Single called |
| `expected_fallback` | `CORE_PAYLOAD_REQUIRED` / `AI_BASE_URL_MISSING`（正常系） |
| `error_fallback` | Single attempted but fell back to Prediction |
| `prediction_fallback` | All fallbacks（expected + error） |
| `latency_ms_p95` | End-to-end detail resolve latency |
| `timeouts` / `status_5xx` / `http_errors` | Failure classes |

Site-wide Flag ON rate requires FE beacon — **out of I4**（UI freeze）.

## Safe operations

- Rollback product path: set `single_ai_detail: false`（I3 Rollback）.
- Observability is additive; disabling Flag does not remove metrics module.
- Do not invent `core_payload` in production to force Single.

## Related

- [Metrics Definition](./single-detail-metrics.md)
- [Alert Rules](./single-detail-alert-rules.md)
- [Dashboard Design](./single-detail-dashboard.md)
- [Runbook](./single-detail-runbook.md)
- [Governance](../research/v109-i4-governance.md)
