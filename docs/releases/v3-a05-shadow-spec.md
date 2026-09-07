# Version 3 — A-05 Shadow Specification

**Date:** 2026-07-24  
**Status:** Specification · **実装なし**  
**Parent:** [`v3-a05-shadow-design.md`](./v3-a05-shadow-design.md)  
**Flag:** `F_V3_A05_ADM_FAVSAFE_ENABLED`

---

## 1. Scope

| In Scope | Out of Scope |
|----------|--------------|
| A-05 Admission Shadow 設計 | Shadow 実装コード |
| Control vs Shadow 比較定義 | Production Flag 既定変更 |
| メトリクス / Hard Gate | Prediction API / UI / Ops 実装 |
| 異常検知ルール | A-01/A-03/A-04 同時 Shadow（別設計） |

---

## 2. Shadow アーキテクチャ

### 2.1 Components（論理）

| コンポーネント | 責務 |
|----------------|------|
| **Ingress** | 本番と同一のレース入力（runners / context）を取得 |
| **Control Emitter** | 現行本番 pick を記録（変更しない） |
| **Shadow Runner** | A-05 のみ適用し Shadow pick + Admission journal を生成 |
| **Comparer** | Control vs Shadow の race-level diff |
| **Label Joiner** | 確定着順・払戻結合（事後） |
| **Metrics Aggregator** | 窓集計 · Hard Gate 判定 |
| **Alerting** | 異常検知 → Rollback Plan トリガー |

### 2.2 Isolation Rules

| 規則 | 内容 |
|------|------|
| I1 | Shadow 失敗は本番応答に影響しない（fail-open） |
| I2 | Shadow は購入・決済・UI 表示に接続しない |
| I3 | 本番 Feature Flag 既定値を変更しない |
| I4 | Shadow ランタイムの A-05 ON は本番 Flag Mesh と分離 |
| I5 | A-03 論理 ON との同時実行禁止 |
| I6 | 結果列は Shadow 入力に使わない（リーク禁止 · Lab と同規約） |

### 2.3 Data Contract（レースレコード）

必須フィールド（設計）:

```text
race_id
control_pick, shadow_pick
control_policy, shadow_policy (= AP-V3-A05-favorite-safe-coverage | identity)
a05_promote, favsafe_blocked, favsafe_reason
field_size, top_margin, top_odds
winner_id, winner_rank          # 事後結合
control_hit, shadow_hit         # 事後
pick_changed
odds_of_picks (control/shadow)  # ROI 仮想計算用
```

---

## 3. Control / Shadow 比較方法

### 3.1 Arm 定義

| Arm | Pick 定義 |
|-----|-----------|
| Control | 本番経路の top-1（A-05 OFF） |
| Shadow | 同一入力 → Admission A-05 → Evaluation/Selection は本番と同一の下流（または Lab と同様 identity top-1） |

**本 Shadow の一次定義（推奨）:**  
下流は Control と同じ Evaluation/Selection/Purchase 契約とし、**差分は Admission A-05 のみ**とする。  
（Offline Accuracy の Control vs A-05 と整合。）

### 3.2 比較手順

1. レース入力をスナップショット  
2. Control pick を記録  
3. Shadow Runner で A-05 pick を記録（非同期可）  
4. 着順確定後に Hit / worsened / ROI を計算  
5. 日次・週次で Hard Gate を評価  

### 3.3 Diff 分類

| クラス | 定義 |
|--------|------|
| unchanged_hit | 両方 Hit |
| unchanged_miss | 両方 Miss |
| improved | Control Miss → Shadow Hit |
| worsened | Control Hit → Shadow Miss |
| pick_churn | pick 変更（Hit 成否不問） |
| worsened_winner_rank1 | worsened かつ `winner_rank==1` |

---

## 4. 評価期間

| フェーズ | 期間（設計） | 目的 |
|----------|--------------|------|
| S0 Dry-run | 3–7 日 | パイプライン健全性 · 欠損率 |
| S1 Shadow Gate | **最低 14 日** または **合意レース数 N≥285** の大きい方 | Hard Gate 判定 |
| S2 安定観察 | 追加 7–14 日（任意） | 季節・場バイアス確認 |

| カレンダー | 開催日を優先（平日のみ等の偏りを避ける） |
|------------|------|
| 中断 | 異常検知で Shadow 停止しても本番は継続 |

---

## 5. 収集メトリクス

| Metric | 定義 | 用途 |
|--------|------|------|
| **Hit** | pick == winner | 主指標 |
| **ΔHit** | Shadow Hit − Control Hit | Hard Gate |
| **Purchase** | 仮想: Hit かつ購入適格とみなす件数（本番購入は実行しない） | 監視 |
| **ROI** | 仮想 flat 100円/レース · `(return−stake)/stake` | 監視 |
| **improved** | Control Miss → Shadow Hit 件数 | 品質 |
| **worsened** | Control Hit → Shadow Miss 件数 | Hard Gate |
| **worsened_winner_rank1** | worsened かつ winner_rank=1 | **必須 Hard** |
| **churn_hit** | Control Hit → Shadow Miss（= worsened と同義の集計） | Hard Gate |
| **pick_churn** | pick 変更件数 | 監視 |
| **promote_rate** | A-05 journal.promote 率 | 過発火監視 |
| **favsafe_block_rate** | favsafe ブロック率 | 保護動作 |
| **latency_p95 / error_rate** | Shadow Runner | 運用健全性 |
| **input_mismatch_rate** | Control/Shadow 入力不一致 | データ品質 |

ROI / Purchase は **Shadow 仮想**であり、本番会計と混同しない。

---

## 6. Shadow Hard Gate（仕様）

詳細閾値は Acceptance Criteria。Spec 上の必須:

| ID | 条件 |
|----|------|
| SH-1 | `worsened_winner_rank1 = 0`（評価窓全体） |
| SH-2 | `ΔHit > 0` |
| SH-3 | `churn_hit = 0`（= worsened 0 と整合） |
| SH-4 | 入力一致 · リークなし · A-03 同時 ON なし |
| SH-5 | Shadow エラー率が合意上限以下 |
| SH-6 | 本番 Control 経路のエラー/レイテンシが Shadow 開始前後で悪化しない |

SH-1–SH-3 は Offline Validation と同一思想。

---

## 7. 異常検知条件

| 検知 | 条件（設計） | アクション |
|------|--------------|------------|
| A1 本命破壊 | 任意日次で `worsened_winner_rank1 ≥ 1` | Shadow 即停止 · 調査 |
| A2 Hit 退行 | 累積 `ΔHit ≤ 0` が継続（合意日数） | 停止候補 |
| A3 過発火 | `promote_rate` が Offline 校正帯を大幅超過 | 調査 · 閾値レビュー |
| A4 入力不一致 | mismatch_rate > 合意閾値 | 停止 |
| A5 Shadow 障害 | error_rate / p95 超過 | fail-open 維持 · Shadow 停止 |
| A6 本番汚染兆候 | Control 経路の異常が Shadow 開始と相関 | **即 Rollback L2**（経路確認） |
| A7 Flag 漏洩 | 本番既定または Mesh で A-05 が誤 ON | 即 OFF · インシデント |

---

## 8. 明示的にやらないこと（実装時も）

- A-05 を Prediction 応答に直接接続  
- UI に Shadow pick を露出（内部ダッシュボードは可）  
- Explainability 本番文言の変更  
- A-03 と A-05 の同時 Shadow  

---

## 9. Stop

本 Spec は設計まで。Shadow Runner / 配線コードは作成しない。
