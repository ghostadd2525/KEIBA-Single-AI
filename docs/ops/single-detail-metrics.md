# Single Detail — Metrics Definition (I4)

**Schema:** `expect-single-detail-metrics/1.0`  
**Source:** `functions/_lib/singleDetailObservability.js`  
**Endpoint:** `GET /api/ops/single-detail` → `data.metrics`

---

## Counters

| Field | Type | Definition |
|---|---|---|
| `requests_total` | count | Resolves recorded on `/api/single/detail` |
| `flag_path_hits` | count | Same as requests（endpoint = Flag ON path） |
| `single_attempted` | count | `core_payload` present and AI proxy used |
| `single_success` | count | `detail_source=single` |
| `prediction_fallback` | count | Returned Prediction bundle as fallback |
| `expected_fallback` | count | Reasons: `CORE_PAYLOAD_REQUIRED`, `AI_BASE_URL_MISSING` |
| `error_fallback` | count | `single_attempted` and fallback（timeout/5xx/map/etc.） |
| `timeouts` | count | `timed_out` or reason `TIMEOUT` |
| `http_errors` | count | Error-class fallbacks / hard errors |
| `status_5xx` | count | Recorded `http_status >= 500` |
| `by_fallback_reason` | map | Reason → count |

## Latency

| Field | Definition |
|---|---|
| `latency_ms_avg` | Mean of rolling samples（max 200） |
| `latency_ms_p50` | p50 of samples |
| `latency_ms_p95` | p95 of samples |

Samples are **in-isolate**（Cloudflare Worker / Pages Function memory）. Multi-isolate aggregation is best-effort via log drain + probe snapshots.

## Rates

| Field | Formula |
|---|---|
| `rates.flag_on_path` | `flag_path_hits / requests_total`（≈1.0） |
| `rates.single_success` | `single_success / requests_total` |
| `rates.prediction_fallback` | `prediction_fallback / requests_total` |
| `rates.expected_fallback` | `expected_fallback / requests_total` |
| `rates.error_fallback_of_attempted` | `error_fallback / single_attempted` |
| `rates.timeout` | `timeouts / requests_total` |
| `rates.http_error` | `http_errors / requests_total` |

## Monitoring map（要件対応）

| 監視項目 | Metric |
|---|---|
| Single API latency | `latency_ms_p95` / `latency_ms_avg` |
| Timeout | `timeouts`, `rates.timeout` |
| 5xx | `status_5xx` |
| Fallback率 | `rates.error_fallback_of_attempted`（警報）+ `rates.prediction_fallback`（観測） |
| Flag ON率 | `flag_path_hits` + endpoint traffic；site-wide は FE beacon 未実装 |
| Prediction Fallback件数 | `prediction_fallback` |
| HTTP Error | `http_errors`, `rates.http_error` |

## Logging

Each resolve emits:

```text
[single-detail-ops] {"ts":"...","layer":"single_detail","event":"resolve","latency_ms":...,"detail_source":"...","single_attempted":bool,"fallback_reason":"...","http_status":N,"timed_out":bool}
```
