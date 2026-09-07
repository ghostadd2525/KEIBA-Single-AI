# Version 3 — Production Integration Design（A-05）

**Date:** 2026-07-24  
**Status:** Design Complete · **実装なし**  
**PRR:** HOLD · Go/No-Go: NO-GO（即時投入不可）  
**Candidate:** A-05 Favorite-Safe Coverage Admission  
**Parents:** [`v3-prr-final-decision.md`](./v3-prr-final-decision.md) · [`v3-a05-shadow-s1-report.md`](./v3-a05-shadow-s1-report.md)

---

## 1. Purpose

A-05 を正式な本番候補として統合するための設計を定義する。  
本 Round は設計のみ。コード実装 · Flag 既定変更 · Production 配線 · Rollout 実行 · Phase 3 は行わない。

---

## 2. Design Principles

| 原則 | 内容 |
|------|------|
| P1 | **A-03 を含む Baseline v3 の本番投入は禁止**（Offline FAIL） |
| P2 | 公式 Admission 候補は **A-05**（A-03 と同時 ON 禁止） |
| P3 | Feature Flag **既定は常に OFF**（Canary は Mesh 限定 ON） |
| P4 | Purchase は本番経路のみ · Shadow は非購入 |
| P5 | 失敗時は fail-open / Flag OFF で現行 Control に戻す |
| P6 | PRR HOLD 解除と別承認なしに配線・ON しない |

---

## 3. Target Official Stack（配線時の意図）

| Stage | Mode | Flag（Canary 時のみ Mesh ON） |
|-------|------|-------------------------------|
| Representation | 現行本番 / Lab Baseline | 既定どおり（勝手に ON しない） |
| **Admission** | **A-05** | `F_V3_A05_ADM_FAVSAFE_ENABLED` |
| Selection | A-04（任意・既存方針） | `F_V3_A04_SEL_HISTORY_ENABLED` |
| Evaluation | A-01 | `F_V3_RANK_D1_ENABLED` |
| Purchase | **既存本番 Purchase** | V3 Purchase 新実装はしない |

| 明示 OFF / 禁止 | `F_V3_A03_POOL_ADMIT_ENABLED` · `F_V3_RANK_D2_ENABLED` · A-03∧A-05 |
|------------------|------|

**公式移行:** Lab Baseline v3 の Admission を A-03 → **A-05** に置換したスタックを本番候補とする。  
詳細 Migration: [`v3-production-integration-migration-plan.md`](./v3-production-integration-migration-plan.md)

---

## 4. Deliverables Index

| 提出物 | パス |
|--------|------|
| Production Integration Design | 本文書 |
| Integration Specification | [`v3-production-integration-spec.md`](./v3-production-integration-spec.md) |
| Migration Plan | [`v3-production-integration-migration-plan.md`](./v3-production-integration-migration-plan.md) |
| Rollout Checklist | [`v3-production-integration-rollout-checklist.md`](./v3-production-integration-rollout-checklist.md) |
| Rollback Checklist | [`v3-production-integration-rollback-checklist.md`](./v3-production-integration-rollback-checklist.md) |

---

## 5. Integration Architecture（要約）

```text
Client / Ops
    │
    ▼
Prediction API (既存)
    │
    ├─ Control Path（現行本番 Decision）──── Purchase（既存）
    │
    └─ Optional Mesh Branch（承認後）
           │
           ├─ Canary % : Admission A-05 → Eval/Sel 方針どおり → Purchase
           │
           └─ Shadow % : A-05 並列評価 → ログのみ（非購入 · fail-open）
```

詳細: Spec §2–§4。

---

## 6. Non-Goals（本 Round）

| 非目標 |
|--------|
| コード実装 |
| Feature Flag 既定値変更 |
| Production 配線実行 |
| Feature Flag ON |
| Production Rollout 実行 |
| Phase 3 |
| 新アルゴリズム |

---

## 7. Stop Condition

**Production Integration Design 完了。ここで停止する。**  
コード実装 · Flag ON · Production Rollout · Phase 3 には着手しない。
