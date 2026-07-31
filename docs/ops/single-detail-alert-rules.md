# Single Detail — Alert Rules (I4)

**IDs:** ALT-SD01 … ALT-SD05  
**Evaluator:** `evaluateSingleDetailAlerts`  
**Wired via:** `/api/ops/single-detail`, `single_detail_ops` probe → Slack `dispatchAlerts`

---

## Sample gate

Alerts are **deferred** until `requests_total >= min_requests`（default **20**）.  
ALT-SD04 additionally requires `single_attempted >= min_single_attempts`（default **10**）.

## Thresholds（default）

| Key | Default | Alert |
|---|---|---|
| `latency_p95_ms` | 8000 | ALT-SD01 |
| `timeout_rate` | 0.05 | ALT-SD02 |
| `status_5xx_min` | 3 | ALT-SD03 |
| `error_fallback_rate` | 0.50 | ALT-SD04（of attempted） |
| `http_error_rate` | 0.10 | ALT-SD05 |

## Rules

| ID | Severity | Condition | Notes |
|---|---|---|---|
| ALT-SD01 | warning | `latency_ms_p95 > 8000` | Slow Single/detail path |
| ALT-SD02 | critical | `rates.timeout > 0.05` | User sees Prediction fallback after wait |
| ALT-SD03 | critical | `status_5xx >= 3` | Upstream / proxy failures |
| ALT-SD04 | warning | `error_fallback_of_attempted > 0.5` | Excludes expected no-core fallback |
| ALT-SD05 | warning | `rates.http_error > 0.1` | Broad HTTP error class |

## Non-alert observations

- High `expected_fallback` with low `single_attempted` → Core not supplied（staging normal until PROMOTE）.
- `rates.flag_on_path ≈ 1` on this endpoint is expected.

## Notification

- Failed probes / critical SD alerts flow through existing ops Slack (`OPS_SLACK_WEBHOOK_URL`).
- `/api/ops/single-detail` returns HTTP **503** when any **critical** alert is active（after sample gate）.
