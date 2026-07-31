# Version 3 — Production Rollback Plan

**Date:** 2026-07-24  
**Review ID:** `v3-production-readiness-review/1.0`  
**Parent:** [`v3-production-readiness-report.md`](./v3-production-readiness-report.md)  
**Decision:** **HOLD**（配線前のため現行本番への適用操作は不要）

---

## 1. 目的

将来 V3 Baseline スタックを配線した場合に、V2 安定状態へ戻す手順を定義する。  
**本 Round では配線がないため、本番ロールバックは発生しない。**

---

## 2. 安定状態（Rollback 先）

| 項目 | 値 |
|------|-----|
| Production Accuracy | **Version 2 · PE-V2-A ON**（Hit 218 Control） |
| V3 Flag | すべて **OFF**（コード既定） |
| V3 パイプライン | 非実行 / 未 import |

---

## 3. ロールバックレベル

### L1 — Feature Flag OFF（第一選択）

| 手順 | 内容 |
|------|------|
| 1 | `F_V3_RANK_D1_ENABLED` → OFF |
| 2 | `F_V3_A03_POOL_ADMIT_ENABLED` → OFF |
| 3 | `F_V3_A04_SEL_HISTORY_ENABLED` → OFF |
| 4 | `F_V3_RANK_D2_ENABLED` が誤 ON なら OFF |
| 5 | Flag 実効スナップショットを保存 |

| 期待 | V3 介入が identity 化し、V2 経路（または V3 OFF 時の既存経路）に戻る |
|------|------|
| RTO | 設定反映速度に依存（目標: 即時〜数分） |
| 検証 | pick が Rollback 前の V2 期待と一致 · エラー率平常 |

### L2 — 経路切離し

| 手順 | 内容 |
|------|------|
| 1 | Prediction 入口で V3 Lab/スタック呼び出しをバイパス |
| 2 | PE-V2-A のみに固定 |
| 3 | V3 Shadow ジョブ停止 |

| いつ | L1 で pick/エラーが回復しない、または Flag Mesh 不具合 |
|------|------|

### L3 — デプロイ戻し

| 手順 | 内容 |
|------|------|
| 1 | V3 配線コミットを revert / 前リリースへ |
| 2 | L1 Flag OFF を維持確認 |
| 3 | 回帰スモーク（Control 相当） |

| いつ | L1/L2 でも隔離が破れ V2 本体が汚染された場合 |
|------|------|

---

## 4. トリガー（Abort 条件 · 案）

| 条件 | レベル |
|------|--------|
| churn_hit > 0（合意窓） | L1 |
| Hit が合意下限を下回る | L1 |
| p95 / エラー率の合意閾値超過 | L1 → L2 |
| V2 Control 経路の破壊兆候 | L2 → L3 |
| Delete/Purchase 境界の変化検知 | L1 即時 + 調査 |

---

## 5. コミュニケーション

| 対象 | 内容 |
|------|------|
| Ops | Flag 状態 · レベル · 時刻 |
| Product | 精度影響の暫定見積 |
| 記録 | Abort 理由・メトリクス・復旧確認を Release ノートへ |

---

## 6. 現行（配線前）チェックリスト

| 項目 | 状態 |
|------|------|
| V3 本番配線 | **なし** → Rollback 操作不要 |
| Flag 既定 OFF | **確認済** |
| V2 Production 非変更 | **確認済** |

---

## 7. 停止

Rollback Plan 定義完了。本 Round では実行しない。
