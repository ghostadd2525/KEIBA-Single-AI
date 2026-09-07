# Version109 Phase I1 — Governance

**Date:** 2026-07-29  
**Parents:** PLATFORM-V1-CONTRACT · A1 · Single AI Version1  
**Status:** Site Web Integration **APPROVED for Staging/Shadow** · Production cutover **NOT APPROVED**

---

```
【Production Diagnosis】
I1 = 既存サイトから Single AI を呼ぶ Web Integration。AI/Core 改善なし。

【Server Diagnosis】
Status: PASS（実装・単体）
Evidence: app/site_integration/* · BFF /api/single/* · unittest

【Client Diagnosis】
Status: PARTIAL
Network: BFF same-origin /api/single 追加（opt-in）
Console: ExpectApi.Single 追加。既存 race.html は未配線（意図的）
Timing: timeout_ms / X-Request-Timeout-Ms
Response Body: site-integration/single/v1 envelope
Cache: BFF health/version no-store 既定に準拠
PredictionBundle Parse: 非変更（並存）
Render Flow: Prediction bind 非変更
Unhandled Promise: N/A（未配線ページ）
JavaScript Error: N/A
Client Evidence: 既存画面の自動切替なし。結合は Migration Guide の opt-in。

Diff Summary: Site HTTP + BFF adapter + opt-in FE client。禁止領域非変更。
Root Cause: N/A（意図的 Web Integration）
Expected Action: Staging smoke → Core PROMOTE 別 Gate → UI opt-in

【Decision】
Action Type: Existing Site Integration
Implementation Required: Yes（完了）
Deployment Required: No（Production） / Optional（Pages + AI Staging）
Configuration Required: Yes（既存 AI_BASE_URL / AI_API_KEY）
Production Required: No
Rollback Required: No（未本番切替）
Risk: Low（Prediction 並存・opt-in）
Expected Next Action: Staging health → Shadow call → PROMOTE/UI Gate
```

---

## 硬制約

| ID | 制約 |
|---|---|
| G109-I1-1 | Prediction / Core / World 変更禁止 |
| G109-I1-2 | Consumer / Presentation / Ticket / Contract 変更禁止 |
| G109-I1-3 | Site Integration は Single API 呼出のみ |
| G109-I1-4 | Core 捏造禁止（core_payload 必須 until PROMOTE） |
| G109-I1-5 | `/api/predictions` 契約非破壊 |
| G109-I1-6 | Production cutover / force 既定化 禁止 |

---

## サイト変更量

| 領域 | 変更 |
|---|---|
| Prediction UI | 0 |
| Bundle 契約 | 0 |
| BFF Single routes | 追加のみ |
| FE ExpectApi.Single | 追加（未配線） |
| AI Python | site_integration 追加のみ |
