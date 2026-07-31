# Version109 Phase A1 — Governance

**Date:** 2026-07-29  
**Parents:** PLATFORM-V1-CONTRACT · ADR-009/010/011 · C7 · Single AI Version1  
**Status:** Application Integration **APPROVED for Staging/Shadow** · Production **NOT APPROVED**

---

```
【Production Diagnosis】
A1 = Single AI Library を HTTP Application 化する。Production Deploy なし。

【Server Diagnosis】
Status: PASS（実装・単体）
Evidence: app/service_integration/* · main.py wiring · unittest 10/10 OK

【Client Diagnosis】
Status: BLOCKED
Network: 公開 Canary / Production UI 経路未検証（本フェーズ対象外）
Console: N/A
Timing: N/A
Response Body: Handler 単体で envelope + schema 確認
Cache: N/A
PredictionBundle Parse: N/A（対象外）
Render Flow: N/A
Unhandled Promise: N/A
JavaScript Error: N/A
Client Evidence: Presentation/Consumer UI は対象外。ブラウザ本番確認は未実施。

Diff Summary: HTTP/OpenAPI/Health/Metrics/Config 追加。Core/Consumer/Contract 非変更。
Root Cause: N/A（意図的 Application 追加）
Expected Action: Staging Shadow 利用可。Production Deploy は別 Gate。

【Decision】
Action Type: Service Integration (Application)
Implementation Required: Yes（完了）
Deployment Required: No（Production） / Optional（Local·Staging）
Configuration Required: Yes（SINGLE_AI_* / 既存 AI_API_KEY）
Production Required: No
Rollback Required: No（未本番）
Risk: Low（Flag OFF + force Shadow）
Expected Next Action: Staging smoke → Alerts/traffic-split Gate → C9
```

---

## 硬制約

| ID | 制約 |
|---|---|
| G109-A1-1 | Prediction / Core / Contract 変更禁止 |
| G109-A1-2 | Consumer / Presentation / Ticket / Decision 語義変更禁止 |
| G109-A1-3 | Application は `build_single_response` 呼出のみ |
| G109-A1-4 | Production Deploy / Canary traffic 禁止 |
| G109-A1-5 | `force=true` を Production 既定にしない |
| G109-A1-6 | natural_explanation / decision_reason 生成禁止（null 固定） |

---

## 承認境界

| 層 | A1 |
|---|---|
| Library (C1–C7) | 利用のみ |
| HTTP Application | **本フェーズ** |
| Staging smoke | 許可 |
| Production Deploy | **別 Gate** |
| Canary traffic | **別 Gate（C9）** |

---

## 成果物

| 成果物 | Path |
|---|---|
| Service Integration | `v109-a1-service-integration.md` |
| Monitoring | `v109-a1-monitoring.md` |
| Deployment | `v109-a1-deployment.md` |
| Governance | `v109-a1-governance.md` |
| Code | `app/service_integration/` |
| Tests | `tests/service_integration/test_a1_service_integration.py` |
