# Version 5 — Conversation Observability Report

**Date:** 2026-07-25  
**Status:** Production Observability READY  
**Constraint:** Conversation Platform Freeze 維持（構造・Agent・Knowledge Runtime・Security Guard・Prediction・Memory・Product UI 未変更）

---

## 1. Approach

観測は **ops 層のみ**に追加した。

| Layer | Change |
|-------|--------|
| Platform (`conversation/v4`, `v5`) | **未変更** |
| API boundary (`app/main.py`) | chat 後に metrics 記録 · health/metrics/dashboard ルート追加 |
| Ops module | `app/ops/conversation_observability.py`（新規） |
| BFF | `/api/ops/conversation` · probe `conversation_health` · Alert ALT-C* |
| Ops UI | `ops.html` Conversation Metrics セクション |

---

## 2. Endpoints

| Method | Path | Role |
|--------|------|------|
| GET | `/v1/conversation/health` | Extended Conversation Health（components + metrics snapshot） |
| GET | `/v1/ops/conversation/metrics` | Metrics snapshot |
| GET | `/v1/ops/conversation/dashboard` | Categories + health + alerts |
| GET | `/v1/ops/conversation/alerts` | Active alerts |
| GET | `/api/ops/conversation` | BFF proxy（Pages） |

---

## 3. Stop condition

本番で次を確認できること:

- Conversation（request / error_rate / latency p50·p95·p99）
- Ollama（model / response_time / timeout）
- Knowledge Runtime（search / hit·miss · health probe）
- Security Guard（block / allow / reasons）

→ `ops.html` Conversation Metrics および `/api/ops/conversation` で確認。

---

## 4. Artifacts

- [Metrics Specification](./v5-conversation-metrics-spec.md)
- [Dashboard Specification](./v5-conversation-dashboard-spec.md)
- [Health Check](./v5-conversation-health-check.md)
- [Alert Policy](./v5-conversation-alert-policy.md)
- [Runbook](../ops/conversation-observability-runbook.md)
