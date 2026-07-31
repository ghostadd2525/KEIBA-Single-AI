# Version 3 — Production Integration Rollback Checklist

**Date:** 2026-07-24  
**Status:** Checklist Only · **本番操作なし（配線前）**  
**Parent:** [`v3-production-integration-design.md`](./v3-production-integration-design.md)

---

## 1. 安定状態（戻し先）

| 項目 | 値 |
|------|-----|
| Decision | 現行 Production Control |
| Purchase | Control pick のみ |
| `F_V3_A05_ADM_FAVSAFE_ENABLED` | **OFF** |
| `F_V3_A03_POOL_ADMIT_ENABLED` | **OFF**（再 ON しない） |
| `F_V3_A04_*` / `F_V3_RANK_D1_*` | OFF（V3 Canary 解除） |
| Shadow | 停止またはログのみ（購入非接続） |

---

## 2. トリガー → レベル

| トリガー | レベル |
|----------|--------|
| worsened_winner_rank1 ≥ 1 | **L1** |
| churn_hit > 0（合意窓） | **L1** |
| ΔHit 継続マイナス | L1（Canary 停止） |
| Shadow/Canary error_rate・p95 超過 | L1 |
| Purchase に shadow_pick 混入 | **L1 → L2** |
| A-03∧A-05 検知 | **L1**（両方 OFF） |
| Control 経路汚染 | **L2** |
| コード欠陥・隔離破壊 | **L3** |

---

## 3. L0 — Shadow 停止

- [ ] Shadow Runner / ジョブ停止  
- [ ] 新規 Shadow ログ書込停止  
- [ ] 本番 Decision / Purchase が無変化であることを確認  

---

## 4. L1 — Feature Flag OFF（第一選択）

- [ ] Mesh: `F_V3_A05_ADM_FAVSAFE_ENABLED` → OFF  
- [ ] Mesh: `F_V3_A04_SEL_HISTORY_ENABLED` → OFF（Canary で使っていた場合）  
- [ ] Mesh: `F_V3_RANK_D1_ENABLED` → OFF（同上）  
- [ ] `F_V3_A03_POOL_ADMIT_ENABLED` → OFF（**ON に戻さない**）  
- [ ] Flag スナップショット保存  
- [ ] 応答が Control に戻ったことをサンプリング  
- [ ] Purchase が Control pick のみであることを確認  

---

## 5. L2 — 経路切離し

- [ ] Prediction 入口で V3 Admission/Canary 分岐をバイパス  
- [ ] Control のみに固定  
- [ ] Shadow 全停止  
- [ ] エラー率・レイテンシが平常か確認  

---

## 6. L3 — デプロイ戻し

- [ ] 配線コミット revert / 前リリース  
- [ ] 既定 Flag OFF 再確認  
- [ ] 回帰スモーク（Control）  
- [ ] インシデント報告  

---

## 7. 事後

- [ ] トリガー・タイムライン記録  
- [ ] wr1 / churn レース Diff 保存  
- [ ] A-03 再有効化を提案しない（禁止）  
- [ ] PRR / Integration Design へのフィードバック  

---

## 8. Stop

Checklist 定義のみ。本番 Rollback 操作は配線前のため不要・未実施。
