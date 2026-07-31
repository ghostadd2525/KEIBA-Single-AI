# Version109 Phase C4 — Decision Service Governance

**Date:** 2026-07-29  
**Status:** Shadow implemented · **Production wiring forbidden**  
**Parents:** PLATFORM-V1-CONTRACT · ADR-009 · ADR-010 · ADR-011 · C1 · C2 · C3

---

```
【Production Diagnosis】
Decision Service Composer（Shadow）。Core 凍結。Production / Canary / Staging 配線なし。

【Server Diagnosis】
Status: PASS（Shadow library）
Evidence: app/consumer/decision_service/* · test_c4_decision_service.py

【Client Diagnosis】
Status: BLOCKED
Client Evidence: HTTP/Production 未配線（本フェーズ禁止）

Diff Summary: Composer が SingleResponse を組立。Reasoner ではない。
Root Cause: N/A
Expected Action: Staging/Canary は別 Gate

【Decision】
Action Type: Decision Service Composer (Shadow)
Implementation Required: Done (Shadow library)
Deployment Required: No
Configuration Required: No（Flag 既定 OFF）
Production Required: No
Rollback Required: No
Risk: Low
Expected Next Action: 別 Gate で Staging のみ検討
```

---

## 硬制約

| ID | 制約 |
|---|---|
| G109-C4-1 | Decision Service は Composer のみ。Reasoner ではない |
| G109-C4-2 | Core / Presentation / Ticket を変更・再計算して意味を変えない |
| G109-C4-3 | Natural Explanation / Decision Reason 生成禁止 |
| G109-C4-4 | Production 配線・Canary / Staging は本フェーズ禁止 |
| G109-C4-5 | Flag OFF 時は Legacy（registry のみ）と互換 |
| G109-C4-6 | Core Platform Version1 凍結・read-only |

---

## 成果物

| 成果物 | Path |
|---|---|
| Decision Service | `app/consumer/decision_service/service.py` |
| Composer | `app/consumer/decision_service/composer.py` |
| Single Response DTO | `app/consumer/decision_service/dto.py` |
| Consumer Integration | `app/consumer/single_api.py` |
| Integration Tests | `tests/consumer/test_c4_decision_service.py` |
| Governance | `docs/research/v109-c4-governance.md` |
| Implementation note | `docs/research/v109-c4-decision-service.md` |

---

## 一文

**組むだけで、考えない。Core の判断は触らない。**
