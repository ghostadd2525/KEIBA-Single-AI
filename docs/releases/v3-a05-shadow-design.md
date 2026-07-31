# Version 3 — A-05 Shadow Evaluation Design

**Date:** 2026-07-24  
**Status:** Design Complete · Design **PASS** · Shadow **implemented**（[`v3-a05-shadow-implementation.md`](./v3-a05-shadow-implementation.md) · 評価窓未開始）  
**Candidate:** A-05（Favorite-Safe Coverage Admission）  
**Flag:** `F_V3_A05_ADM_FAVSAFE_ENABLED`（既定 OFF · 変更しない）  
**PRR:** HOLD 継続  
**Parents:** [`v3-a05-validation-report.md`](./v3-a05-validation-report.md) · [`v3-admission-correction-design.md`](./v3-admission-correction-design.md)

---

## 1. Purpose

A-05 を本番候補として評価するため、**購入に影響しない Shadow 比較**の設計を定義する。

本 Round 時点で Shadow **実装は完了**（[`v3-a05-shadow-implementation.md`](./v3-a05-shadow-implementation.md)）。  
評価窓・Production 配線・Flag 既定変更・Phase 3 は行わない。

---

## 2. Prerequisites（設計前提）

| 項目 | 状態 |
|------|------|
| A-05 Accuracy | PASS（Offline 59→66 · wr1=0） |
| A-05 Validation | PASS（2-round 再現） |
| A-03 | 凍結 · Shadow で同時 ON 禁止 |
| Production / Prediction 経路 | V2（または現行本番）が正 · A-05 未配線 |
| PRR | HOLD（本設計は HOLD 解除の青写真） |

---

## 3. Design Contents（索引）

| 項目 | 詳細 |
|------|------|
| Shadow アーキテクチャ | Spec §2 |
| Control / Shadow 比較 | Spec §3 · 本文 §5 |
| 評価期間 | Spec §4 |
| 収集メトリクス | Spec §5 |
| Shadow Hard Gate | Acceptance Criteria |
| Rollout 条件 | [`v3-a05-shadow-rollout-plan.md`](./v3-a05-shadow-rollout-plan.md) |
| Rollback 条件 | [`v3-a05-shadow-rollback-plan.md`](./v3-a05-shadow-rollback-plan.md) |
| 異常検知 | Spec §7 |
| Production 移行条件 | Acceptance Criteria §4 |

**Shadow Specification:** [`v3-a05-shadow-spec.md`](./v3-a05-shadow-spec.md)  
**Acceptance Criteria:** [`v3-a05-shadow-acceptance-criteria.md`](./v3-a05-shadow-acceptance-criteria.md)

---

## 4. Shadow アーキテクチャ（要約）

```text
本番リクエスト / レース入力
        │
        ├──────────────────────────────┐
        ▼                              ▼
  Control Path                   Shadow Path（非購入）
  (現行本番 pick)                A-05 Flag 論理 ON（Shadow 専用）
  購入・API 応答に使用            pick / journal のみ記録
        │                              │
        └────────── Compare ───────────┘
                     │
              Shadow Metrics Store
              (Hit / Purchase* / ROI* / churn / wr1 …)
```

\* Purchase / ROI は **Shadow 仮想フラット賭け**（本番購入を実行しない）。

原則:

1. **本番応答・購入は Control のみ**  
2. Shadow は同一入力の並列評価（または直後の非同期評価）  
3. `F_V3_A05_ADM_FAVSAFE_ENABLED` の**リポジトリ既定は OFF のまま**  
4. Shadow 実行時のみ、Shadow ランタイムが A-05 を論理 ON（本番 Flag Mesh とは分離）  
5. A-03 と A-05 の同時論理 ON は禁止  

---

## 5. Control / Shadow 比較方法（要約）

| Arm | 定義 |
|-----|------|
| **Control** | 現行本番 top-1（A-05 OFF · 既存経路） |
| **Shadow** | 同一 runners に A-05 Admission のみ適用した top-1 |

比較単位: レース。ラベル確定後に Hit / worsened 等を retrospectively 集計。

詳細: Spec §3。

---

## 6. Non-Goals

| 非目標 | 理由 |
|--------|------|
| 本 Round の Shadow コード実装 | 停止条件 |
| Flag 既定 ON | Production リスク |
| Prediction API / UI 変更 | スコープ外 |
| Baseline v3（A-03+A-04+A-01）一括 Shadow | 本設計は **A-05 単体** |
| Phase 3 | 別承認 |

---

## 7. Deliverables

| 提出物 | パス |
|--------|------|
| Shadow Design | 本文書 |
| Shadow Specification | [`v3-a05-shadow-spec.md`](./v3-a05-shadow-spec.md) |
| Rollout Plan | [`v3-a05-shadow-rollout-plan.md`](./v3-a05-shadow-rollout-plan.md) |
| Rollback Plan | [`v3-a05-shadow-rollback-plan.md`](./v3-a05-shadow-rollback-plan.md) |
| Acceptance Criteria | [`v3-a05-shadow-acceptance-criteria.md`](./v3-a05-shadow-acceptance-criteria.md) |

---

## 8. Stop Condition

**Shadow Evaluation Design 完了。ここで停止する。**  
Shadow 実装 · Production 配線 · Phase 3 には着手しない。
