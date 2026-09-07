# Version107 — Governance（Product Integration）

**Date:** 2026-07-28  
**Parents:** ADR-011 · ADR-008/009/010 · V103 · V105 · V106  
**Status:** Design only · **実装禁止**  
**Version tag 注記:** 本票群は Product Integration（`ADR-011` / `v107-consumer-api` / `v107-architecture-diagram` / `v107-migration-plan`）。他 V107 票があればスコープ共有しない。

---

```
【Production Diagnosis】
Product Integration Architecture 設計。Core Platform 固定。実装なし。

【Server Diagnosis】
Status: PASS（設計文書化）
Evidence: ADR-011 · V103 · V106 PARTIAL_READY · ADR-008 flags.py

【Client Diagnosis】
Status: BLOCKED
Client Evidence: 実配線未実施（設計のみ）

Diff Summary: Core API と Consumer API を分離。Single/Win5 モジュール境界を固定。
Root Cause: N/A
Expected Action: 実装は別 Decision（P1 Shadow から）

【Decision】
Action Type: Product Integration Architecture
Implementation Required: No
Deployment Required: No
Configuration Required: No
Production Required: No
Rollback Required: No
Risk: Low
Expected Next Action: 承認後 P1 Core Payload Shadow（別 Gate）
```

---

## Decision Gate

| Item | Value |
|---|---|
| Action Type | Product Integration Design |
| Implementation Required | **No** |
| Prediction / World / NM / Affinity / EC 変更 | **No** |
| Core Contract / Evidence Governance 変更 | **No** |
| 新 Semantic / Feature | **No** |
| Production Flag ON | **No** |
| Risk | Low |

---

## 硬制約

| ID | 制約 |
|---|---|
| G107-1 | Core は Platform。Product 都合で意味を変えない |
| G107-2 | Consumer 不足を Core Semantic 追加で埋めない |
| G107-3 | Ticket/Coverage/Selection を Core API に載せない |
| G107-4 | EV-P / EV-S / EV-D を API レスポンスで混線させない（ラベル必須） |
| G107-5 | Affinity/EC の禁止用途を Flag ON で解禁しない |
| G107-6 | V90 Decision Migration と Flag 归因を分離 |
| G107-7 | 本フェーズ実装禁止 |

---

## 正式採用セット（前提確認）

| 文書 | 役割 |
|---|---|
| ADR-009 | Core Completeness |
| ADR-010 | Explanation Confidence |
| V103 | Contract Surface / Payload |
| V105 | Evidence Governance |
| V106 | Consumer Readiness |
| **ADR-011** | Product Integration |

---

## 成果物

| 成果物 | Path |
|---|---|
| Product Integration ADR | `docs/adr/ADR-011-product-integration.md` |
| Consumer API | `docs/research/v107-consumer-api.md` |
| Architecture Diagram | `docs/research/v107-architecture-diagram.md` |
| Migration Plan | `docs/research/v107-migration-plan.md` |
| Governance | `docs/research/v107-governance.md` |

---

## 一文

**Core を変えず、Consumer で繋ぐ。Flag で守り、Registry で導く。**
