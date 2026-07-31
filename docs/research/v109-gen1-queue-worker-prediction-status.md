# GEN1 — Queue / Worker / Prediction Status

## Queue Status
- Dedicated Prediction Queue: **NONE**
- Enqueue on HTTP 202: **NONE**

## Worker Status
| Worker | Status |
|---|---|
| PI API | Healthy |
| race_refresh timer/service | Not generating Aug1 features (default=today); EC2 journal not fetched |
| Result Automation | unhealthy FAILED (not prediction path) |
| Research Scheduler | idle (not prediction path) |
| EC2 via monitor-live | No Data |

## Prediction Status
| race_id | HTTP | Notes |
|---|---|---|
| 2026-08-01-01-02 | 202 | catalog yes / features no / cards=missing |
| 2026-08-01-* | missing | all cards |
| 2026-07-26-01-11 | 200 | control Ready |
| 2026-07-29-01-01 | 202 | today also pending |
