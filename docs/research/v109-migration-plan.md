# Version109 — Migration Plan（Consumer Development）

**Date:** 2026-07-28（更新: 2026-07-29）  
**Status:** **Single AI Version1 DEVELOPMENT COMPLETE** · **Operations Management Phase**  
**Parents:** V109 Roadmap · V107 Migration · V90 Decision Migration  
**Successor of:** V107 P0 Document Freeze（Consumer 側を本票が引き継ぐ）  
**Closure:** [`v109-single-ai-v1-development-complete.md`](./v109-single-ai-v1-development-complete.md) · [`v109-single-ai-v1-ops-phase.md`](./v109-single-ai-v1-ops-phase.md)

> **2026-07-29:** Single AI V1 開発フェーズ終了。新規機能追加停止。Flag `single_ai_detail` OFF 維持。恒久 Cutover は別 Gate。

---

## 不変条件

| ID | 条件 |
|---|---|
| CD-I0 | Prediction Rank/Score 非変更 |
| CD-I1 | World / NM / Affinity / EC / Evidence / Contract **定義**非変更 |
| CD-I2 | Version1 で Core Improvement を目的とした変更禁止 |
| CD-I3 | 不足はまず Consumer 解決 |
| CD-I4 | Core 変更は例外三条件の証明、または Version2 Platform Research 正式開始のみ |
| CD-I5 | Rollback = Consumer/Decision/PROMOTE Flag OFF。PE 副作用なし |
| CD-I6 | Version1 Core は安定運用優先。V2 研究は V1 経路と分離 |

---

## Phases（Consumer 主系列）

### C0 — Kickoff（本票）

| 項目 | 内容 |
|---|---|
| 文書 | Roadmap / Architectures / Integration / Governance |
| Core | FROZEN |
| 出口 | V109 レビュー完了 → 実装ブランチ許可（Consumer のみ） |

### C1 — Single Registry + Consumer API Skeleton

| 項目 | 内容 |
|---|---|
| 実装 | Decision Registry · `consumer-api/single/v1` 骨格（Flag OFF） |
| コード | `app/consumer/*` · `docs/research/v109-c1-implementation.md` |
| 出口 | 契約テスト（read-only · schema）— **PASS（2026-07-28）** |

### C2 — Presentation

| 項目 | 内容 |
|---|---|
| 実装 | structured Presentation（NL 禁止）。Flag OFF / Shadow |
| コード | `app/consumer/presentation/*` · `docs/research/v109-c2-presentation.md` |
| 出口 | Integration Test PASS（2026-07-28） |

### C3 — Ticket Policy

| 項目 | 内容 |
|---|---|
| 実装 | Policy Resolver（Template 解決）。Reason 禁止。Flag OFF / Shadow |
| コード | `app/consumer/ticket/*` · `docs/research/v109-c3-ticket-policy.md` |
| 出口 | Integration Test PASS（2026-07-28） |

### C4 — Decision Service（Composer）

| 項目 | 内容 |
|---|---|
| 実装 | SingleResponse 組立。Reasoner 禁止。Shadow only。Production 配線禁止 |
| コード | `app/consumer/decision_service/*` · `docs/research/v109-c4-*.md` |
| 出口 | Integration Test PASS（2026-07-29） |

### C5 — Single Shadow Validation

| 項目 | 内容 |
|---|---|
| 実装 | 機能追加なし。Consumer Validation only |
| コード | `app/consumer/shadow_validation.py` · `docs/research/v109-c5-*.md` |
| 出口 | **PASS 6/6（2026-07-29）** |

### C5.5 — Consumer UX Validation

| 項目 | 内容 |
|---|---|
| 実装 | 機能追加なし。Response 理解可能性の Shadow レビュー |
| 文書 | `docs/research/v109-c55-*.md` |
| 出口 | **PASS_WITH_NOTES（2026-07-29）** |

### C6 — Staging（Single Feature Flag）

| 項目 | 内容 |
|---|---|
| 実装 | Flag OFF/ON · Perf · Rollback · Logging。Production/Canary 禁止 |
| コード | `app/consumer/staging_validation.py` · `docs/research/v109-c6-*.md` |
| 出口 | **PASS 5/5（2026-07-29）** |

### C7 — Canary Readiness

| 項目 | 内容 |
|---|---|
| 実装 | 判定のみ。機能追加なし。Production 切替なし |
| コード | `app/consumer/canary_readiness.py` · `docs/research/v109-c7-*.md` |
| 出口 | **READY_WITH_GAPS（2026-07-29）** |

### A1 — Service Integration（Application）

| 項目 | 内容 |
|---|---|
| 実装 | HTTP / Validation / Serialization / OpenAPI / Health / Metrics / Logging / Config |
| 対象外 | Prediction · Core · Consumer 語義 · Presentation · Ticket · Decision · Contract · Production Deploy |
| コード | `app/service_integration/*` · `main.py` wiring · `docs/research/v109-a1-*.md` |
| 出口 | **IMPLEMENTED（2026-07-29）** · Production Deploy = 別 Gate |

### I1 — Existing Site Integration（Web）

| 項目 | 内容 |
|---|---|
| 実装 | Site → BFF `/api/single` → `/v1/site` → Single API。Auth / Race ID / Timeout / Version |
| 対象外 | Prediction · Core · World · Consumer · Presentation · Ticket · Contract · Production cutover |
| コード | `app/site_integration/*` · `functions/api/single/*` · `public/assets/api/single.js` · `docs/research/v109-i1-*.md` |
| 出口 | **IMPLEMENTED（2026-07-29）** · UI opt-in · Core PROMOTE = 別 Gate |

### UI1 — Existing UI Adaptation

| 項目 | 内容 |
|---|---|
| 実装 | Single→PredictionBundle View Mapper。既存 bind/レイアウト非変更。内部用語非表示 |
| 対象外 | Prediction/Core/Consumer/Contract/Presentation Contract/UIデザイン変更 |
| コード | `app/ui_adaptation/*` · `functions/_lib/singleToBundleMapper.js` · `docs/research/v109-ui1-*.md` |
| 出口 | **IMPLEMENTED（2026-07-29）** · Production UI cutover = 別 Gate |

### UI2 — Existing UI Shadow Validation

| 項目 | 内容 |
|---|---|
| 実装 | Bundle↔既存UIスロット互換 Shadow 検証。UI変更なし |
| 成果 | Validation / Screenshot / Visual Diff / Compatibility / Governance |
| コード | `app/ui_adaptation/shadow_validation.py` · `docs/research/v109-ui2-*.md` · `ui2-artifacts/` |
| 出口 | **PASS 100%（2026-07-29）** |

### I2 — Production Cutover Gate

| 項目 | 内容 |
|---|---|
| 種別 | 設計・監査のみ。実装・Cutover 実行なし |
| Product Requirement | Race List Cache 変更禁止（一覧 Single 禁止） |
| 成果 | Cutover Report / Release·Rollback Checklist / Ops / Readiness / Governance |
| 出口 | **NOT READY — CUTOVER BLOCKED（2026-07-29）** |

### I3 — Detail Page Wiring

| 項目 | 内容 |
|---|---|
| 実装 | 詳細のみ `single_ai_detail` Flag。OFF=Prediction / ON=Single detail+fallback |
| LOCK | 一覧・Race List Cache 永久固定 |
| コード | `single-detail.js` · `/api/single/detail/:id` · `race.html` · `docs/research/v109-i3-*.md` |
| 出口 | **IMPLEMENTED · Flag default OFF（2026-07-29）** |

### I4 — Operational Readiness

| 項目 | 内容 |
|---|---|
| 種別 | Monitoring / Alert / Metrics / Dashboard設計 / Logging / Docs |
| 非変更 | Core / Consumer / Prediction / UI / Race List Cache |
| コード | `singleDetailObservability.js` · `/api/ops/single-detail` · `probeSingleDetailOps` · `docs/ops/single-detail-*.md` |
| Alert | ALT-SD01..05（latency / timeout / 5xx / error fallback / HTTP error） |
| 出口 | **OPS READY · Cutover は I2 再評価（2026-07-29）** |

### I5 — Staging Rehearsal

| 項目 | 内容 |
|---|---|
| 種別 | Flag ON 手順リハーサル · 運用エビデンス（製品コード非追加） |
| 確認 | Flag ON/OFF · Single API · Fallback · Timeout · Rollback · Alert · Metrics · Runbook |
| 成果 | `v109-i5-*.md` · `i5-artifacts/` · I2 re-eval |
| 出口 | **Repo/Harness PASS · Production Cutover NO-GO（未デプロイ/live未検証）** |

### R1 — Release Preparation

| 項目 | 内容 |
|---|---|
| Deploy | I3+I4 を Flag OFF で Production Pages へ |
| Live | 限定 Flag ON rehearse（ADMIN）→ **OFF 復帰** |
| Fix | ui-features cache-bust · `ready()` 後 Flag 判定 |
| 出口 | **Release GO（Flag OFF shipped）· Cutover NO-GO** · `v109-r1-*.md` · I2 final gate |

### CLOSE — Development Complete → Ops Management

| 項目 | 内容 |
|---|---|
| 宣言 | Single AI Version1 開発完了 · 新規機能停止 |
| Flag | `single_ai_detail` **OFF 維持** |
| Cutover | **別 Gate**（Platform 正常化 · 運用承認 · Release Decision） |
| 文書 | `v109-single-ai-v1-development-complete.md` · `v109-single-ai-v1-ops-phase.md` · `v109-single-ai-v1-governance-closed.md` |
| 出口 | **OPS MANAGEMENT PHASE ACTIVE（2026-07-29）** |

### UI3 — PredictionBundle Contract Fix

| 項目 | 内容 |
|---|---|
| 問題 | `PredictionBundle が契約と一致しません`（ExpectContractGuard） |
| 修正 | Mapper + `ensurePredictionBundleContract`（narrative / race_no 等） |
| 非変更 | Core / Consumer / Prediction / UI / Cache |
| 出口 | **IMPLEMENTED（2026-07-29）** · `v109-ui3-*.md` |

### C8 — Win5 Consumer

| 項目 | 内容 |
|---|---|
| 順 | API → Candidate → Coverage → Race Selection |
| 出口 | W-CC 準拠 Shadow |

### C9 — Canary Traffic / Production

| 項目 | 内容 |
|---|---|
| 状態 | **未承認**（C7 Blockers 解消後） |
| ゲート | HTTP / metrics / alerts / split + 明示承認 |

---

## 並列: PROMOTE Gate（非必須で Consumer 開始可）

| Phase | 内容 |
|---|---|
| P1 | Shadow serialize only |
| P2 | staging `W_CORE_PAYLOAD_V103` |
| 規則 | Consumer C1–C3 は PROMOTE OFF でも進行可（CONDITION C2） |

---

## V107 対応

| V107 | V109 |
|---|---|
| P0 Document Freeze | **完了 → C0** |
| P1 Core Shadow | **PROMOTE 別 Gate（P1）** |
| P2 Consumer Shadow | **C1–C4** |
| P3–P4 Staging/Canary | **C5** |

---

## Related

- `v109-product-roadmap.md`
- `v107-migration-plan.md`
- `v90-migration-adr.md`
