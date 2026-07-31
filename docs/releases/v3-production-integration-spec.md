# Version 3 — Production Integration Specification（A-05）

**Date:** 2026-07-24  
**Status:** Specification · **実装なし**  
**Parent:** [`v3-production-integration-design.md`](./v3-production-integration-design.md)  
**PRR:** HOLD

---

## 1. Scope

| In Scope（設計） | Out of Scope |
|------------------|--------------|
| API 配線設計 | API コード変更 |
| Purchase 統合方針 | Purchase ロジック実装 |
| Operations / 監視 | Ops ツール実装 |
| Flag 運用 | 既定値変更 |
| 切替・RB・リスク | 実行 |

---

## 2. 統合アーキテクチャ

### 2.1 Logical Components

| コンポーネント | 責務 |
|----------------|------|
| Prediction Ingress | 既存リクエスト受信 · 応答は Control または承認済み Canary |
| Decision Engine | 現行本番 or V3 Lab Admission/Eval/Sel（Mesh） |
| A-05 Admission | Favorite-Safe Coverage（本番候補） |
| Purchase Adapter | **既存本番 Purchase のみ** · Shadow 非接続 |
| Shadow Sidecar | 並列 A-05 · ログ · fail-open（既存 Lab Shadow と整合） |
| Flag Mesh | 環境別 ON/OFF · 既定 OFF · A-03 mutex |
| Metrics / Alerting | Hit proxy · wr1 · churn · error · promote_rate |

### 2.2 Path Modes

| Mode | Decision | Purchase | 用途 |
|------|----------|----------|------|
| M0 Control | 現行本番 | 実行 | 現状安定 |
| M1 Shadow | Control 応答 + A-05 ログ | Control のみ | 継続監視 |
| M2 Canary | 一部トラフィック A-05 スタック | Canary 分のみ実行 | 限定導入 |
| M3 Full | 全量 A-05 スタック | 全量 | 最終（別承認） |

PRR HOLD 中は **M0 +（任意）M1** まで。M2+ は前提充足後。

---

## 3. API 変更点一覧（設計）

| # | 変更点 | 種別 | 備考 |
|---|--------|------|------|
| A1 | Prediction 応答スキーマに `decision_source`（control\|v3_a05） | 追加（後方互換） | 任意・段階導入 |
| A2 | 内部のみ `admission_policy_id` / `a05_journal` をログ | 非公開フィールド可 | API 公開必須ではない |
| A3 | Shadow 用非同期フック（同一入力コピー） | 内部 | 応答レイテンシに影響させない |
| A4 | Feature Flag 解決を Prediction 入口で読取 | 内部 | **既定 false** |
| A5 | A-03 Flag が ON のとき A-05 を拒否 / Hard Fail | 内部ガード | mutex |
| A6 | 公開 REST/GraphQL の破壊的変更 | **なし** | 互換維持 |
| A7 | UI 契約変更 | **なし**（本設計対象外・別レビュー） | Explain も別 |

**原則:** 外部クライアント契約は壊さない。差分は内部配線とオプショナルメタ。

---

## 4. Purchase 統合

| 規則 | 内容 |
|------|------|
| Q1 | Purchase 実行主体は **本番 Decision の pick のみ** |
| Q2 | Shadow pick は **購入キューに入れない** |
| Q3 | Canary では Canary Decision の pick のみ購入 |
| Q4 | V3 専用 Purchase マッパー新設はしない（既存本番を再利用） |
| Q5 | ロールバック時は Control Decision → 既存 Purchase に即復帰 |

```text
if mode == Shadow:
    respond(control_pick); purchase(control_pick); log(shadow_pick)
elif mode == Canary and in_canary_bucket:
    respond(a05_stack_pick); purchase(a05_stack_pick)
else:
    respond(control_pick); purchase(control_pick)
```

---

## 5. Operations 運用フロー

### 5.1 日常

1. 開催前: Flag Mesh スナップショット確認（A-05 既定 OFF、A-03 OFF）  
2. 開催中: Shadow/Canary メトリクスダッシュボード監視  
3. 開催後: 着順結合 → Hit / wr1 / churn 集計  
4. 異常時: Rollback Checklist 実行  

### 5.2 監視項目

| Metric | 閾値（設計） | アクション |
|--------|--------------|------------|
| worsened_winner_rank1 | = 0（窓） | 即 Rollback L1 |
| churn_hit | = 0（Canary 窓） | L1 |
| ΔHit vs Control | > 0（評価窓） | 未達なら Canary 停止 |
| Shadow/Canary error_rate | ≤ 合意上限 | fail-open · 調査 |
| promote_rate | 監視帯（例 ≤0.25） | 逸脱で調査 |
| p95 latency | 現行比悪化上限 | L1/L2 |
| A-03∧A-05 | 発生 0 | 即両方 OFF |

### 5.3 アラート

- A1: wr1 ≥ 1  
- A2: Flag 既定または Mesh の意図せぬ ON  
- A3: Purchase に shadow_pick 混入検知  
- A4: mutex 違反  

---

## 6. Feature Flag 運用

| Flag | 既定（リポジトリ） | 本番 Mesh |
|------|-------------------|-----------|
| `F_V3_A05_ADM_FAVSAFE_ENABLED` | **False（変更禁止）** | Canary のみ限定 ON |
| `F_V3_A03_POOL_ADMIT_ENABLED` | False | **常時 OFF 推奨** |
| `F_V3_A04_SEL_HISTORY_ENABLED` | False | スタック方針に従い Canary |
| `F_V3_RANK_D1_ENABLED` | False | スタック方針に従い Canary |
| Shadow runtime env | false | M1 時のみ |

| 運用ルール |
|------------|
| 既定値を True にしない |
| 変更は Mesh オーバレイのみ · 監査ログ必須 |
| A-03 ON 時は A-05 を適用しない（ハードガード） |
| ロールバック第一手は全 V3 Accuracy Flag OFF |

---

## 7. 切替手順（概要）

| Step | 内容 | 前提 |
|------|------|------|
| T0 | 統合設計承認 · PRR 条件付き GO | 本設計 + Final Review |
| T1 | Staging 配線（応答は Control） | 実装 Round |
| T2 | Staging Shadow M1 | 非購入 |
| T3 | Staging Canary M2 | Rollback ドリル済 |
| T4 | Prod Shadow M1 | PRR 許可 |
| T5 | Prod Canary M2（小%） | 別承認 |
| T6 | 拡大 → M3 | 別承認 |

詳細チェックリスト: Rollout Checklist。

---

## 8. ロールバック条件（概要）

| 条件 | レベル |
|------|--------|
| wr1 ≥ 1 | L1 Flag OFF |
| churn_hit > 0（合意窓） | L1 |
| Purchase 異常 / shadow 混入 | L1 → L2 |
| Control 経路汚染 | L2 経路切離し |
| コード欠陥 | L3 デプロイ戻し |

詳細: Rollback Checklist。

---

## 9. 統合リスク評価

| リスク | 等級 | 緩和 |
|--------|------|------|
| A-03 誤配線 | Critical | mutex · Baseline 禁止 · 監視 |
| Canary 本命破壊 | High | wr1 即 RB · FavSafe |
| API レイテンシ | Med | Shadow 非同期 · タイムアウト |
| Purchase 二重/誤購入 | High | Shadow 非接続 · 契約テスト |
| Flag 既定汚染 | High | 既定 OFF 凍結 · CI 検査（将来） |
| 説明責任（Explain） | Med | 別レビュー必須 |

---

## 10. 本番移行チェックリスト（要約）

Rollout Checklist 全文を正とする。必須ゲート例:

- [ ] PRR が HOLD から条件付き GO  
- [ ] 公式スタックが A-05（A-03 除外）で文書凍結  
- [ ] Staging Rollback ドリル PASS  
- [ ] 監視・アラート接続  
- [ ] Purchase が Shadow 非接続であることを検証  
- [ ] 既定 Flag がすべて OFF  

---

## 11. Stop

本 Spec は設計まで。実装・配線・Flag ON は行わない。
