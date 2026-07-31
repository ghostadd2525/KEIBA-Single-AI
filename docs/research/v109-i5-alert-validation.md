# Phase I5 — Alert Validation

**Date:** 2026-07-29  
**Scope:** ALT-SD01..05（I4）発火・閾値・非誤報

---

## Method

1. `node scripts/ops/test-single-detail-observability.mjs`
2. Expected-fallback（`CORE_PAYLOAD_REQUIRED` ×25）→ **ALT-SD04 非発火**
3. Timeout/5xx 合成（×20）→ **ALT-SD01..05 発火**

## Results

| Alert | Severity | Condition | Result |
|---|---|---|---|
| ALT-SD01 | warning | p95 > 8s | **PASS**（発火） |
| ALT-SD02 | critical | timeout_rate > 5% | **PASS**（発火） |
| ALT-SD03 | critical | status_5xx ≥ 3 | **PASS**（発火） |
| ALT-SD04 | warning | error_fallback_of_attempted > 50% | **PASS**（発火）· expected FB では非発火 |
| ALT-SD05 | warning | http_error_rate > 10% | **PASS**（発火） |

## Live Dashboard

| Surface | Status |
|---|---|
| Code: `probeSingleDetailOps` + alert merge | PASS |
| Prod `GET /api/ops/single-detail` | **BLOCKED** — OPS_CLOSED / Research Week |
| Slack dispatch | 既存 `dispatchAlerts` 配線（本番キー依存・本 rehearse 未送信） |

## Conclusion

Alert **rules + evaluator** は運用可能。本番ダッシュボードでの実トラフィック緑確認は **I3/I4 デプロイ後 + OPS 再開後** に再実施。
