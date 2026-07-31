# Version 3 — A-05 Shadow Rollback Plan

**Date:** 2026-07-24  
**Status:** Plan Only · **配線前のため現行本番操作は不要**  
**Parent:** [`v3-a05-shadow-design.md`](./v3-a05-shadow-design.md)

---

## 1. 目的

A-05 Shadow（および将来の限定配線）を安全に停止・切り戻す手順を定義する。

Shadow 段階では本番 pick は Control のままのため、**第一選択は Shadow 停止のみ**。

---

## 2. 安定状態（Rollback 先）

| 項目 | 値 |
|------|-----|
| 本番 pick | Control（A-05 OFF） |
| `F_V3_A05_ADM_FAVSAFE_ENABLED` 既定 | **False** |
| Shadow Runner | 停止 |
| A-03 | OFF（A-05 と同時 ON しない） |

---

## 3. ロールバックレベル

### L0 — Shadow 停止（第一選択 · Shadow 期間）

| 手順 | 内容 |
|------|------|
| 1 | Shadow Runner / ジョブを停止 |
| 2 | 比較パイプラインへの新規書き込み停止 |
| 3 | アラートを Ack · インシデント記録 |

| 期待 | 本番 pick / 購入は無変化 |
|------|------|
| RTO | 即時〜数分 |

### L1 — Feature Flag OFF（Canary / 誤 ON 時）

| 手順 | 内容 |
|------|------|
| 1 | 本番 Mesh 上の `F_V3_A05_ADM_FAVSAFE_ENABLED` → OFF |
| 2 | A-03 が誤って連動 ON なら OFF |
| 3 | Flag スナップショット保存 |

| いつ | 本番経路に A-05 が誤適用された場合 |
|------|------|

### L2 — 経路切離し

| 手順 | 内容 |
|------|------|
| 1 | Prediction 入口で V3 Admission Shadow/本番呼び出しをバイパス |
| 2 | Control のみに固定 |
| 3 | Shadow 全停止 |

| いつ | L0/L1 後も Control 異常、または隔離破れ |
|------|------|

### L3 — デプロイ戻し

| 手順 | 内容 |
|------|------|
| 1 | Shadow/配線コミットの revert |
| 2 | Flag 既定 OFF 確認 |
| 3 | 回帰スモーク |

| いつ | コード混入により隔離が破れた場合 |
|------|------|

---

## 4. Rollback トリガー

| 条件 | レベル |
|------|--------|
| `worsened_winner_rank1 ≥ 1`（日次または累積） | **L0 即時** |
| `churn_hit > 0` が Hard Gate 窓で発生 | L0 |
| `ΔHit ≤ 0` が合意連続日 | L0 → 設計見直し |
| Shadow error_rate / p95 超過 | L0 |
| 本番 Flag 誤 ON / A-03 同時 ON | **L1** |
| Control 経路汚染兆候 | **L2** |
| 隔離破壊がコード起因 | **L3** |

---

## 5. コミュニケーション

| 対象 | 内容 |
|------|------|
| 開発 | トリガー · レベル · ログ所在 |
| 運用 | Shadow 停止が購入に影響しないことの確認 |
| PRR | HOLD 中は L1+ 本番操作は原則発生しない |

---

## 6. Stop

Rollback Plan の文書化まで。本番操作・Shadow 停止ドリル実装は行わない。
