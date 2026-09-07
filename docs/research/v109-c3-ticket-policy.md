# Version109 Phase C3 — Ticket Policy (Policy Resolver)

**Date:** 2026-07-28  
**Status:** Implemented (library) · Flag default OFF · Shadow only  
**Parents:** PLATFORM-V1-CONTRACT · C1 Registry · C2 Presentation

---

## 一文

**Ticket Policy は Reasoning Engine ではない。`policy_id` → Ticket Template の解決のみ。**

---

## 成果物

| 成果物 | Path |
|---|---|
| Ticket DTO | `app/consumer/ticket/dto.py` |
| Ticket Resolver | `app/consumer/ticket/resolver.py` |
| Template Registry | `app/consumer/ticket/templates.py` |
| Market Resolver | `app/consumer/ticket/market.py` |
| Integration Test | `tests/consumer/test_c3_ticket_policy.py` |

---

## 流れ

```text
Registry.policy_id
    → Template Registry (static)
    → fill with read-only prediction.ranks
    → Market Resolver (odds/budget annotate)
    → TicketPlan (reason=null)
```

Near Miss は Ready 分散テンプレを **使わない**（DL-C6 / V95）。

---

## 禁止（遵守）

Prediction / World / Near Miss / Affinity / EC / Policy 変更なし。  
Reason 生成なし（`reason=null`）。

---

## Flag

`W_CONSUMER_TICKET_ENABLED` **既定 OFF**  
Shadow: `force_ticket=True` または Consumer `force=True` + `include_tickets=True`

---

## Next

Win5 Consumer / Staging（Roadmap Track W / C4+）  
