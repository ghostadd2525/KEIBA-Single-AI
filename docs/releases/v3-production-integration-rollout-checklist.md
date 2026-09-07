# Version 3 — Production Integration Rollout Checklist

**Date:** 2026-07-24  
**Status:** Checklist Only · **実行チェックは未実施**  
**Parent:** [`v3-production-integration-design.md`](./v3-production-integration-design.md)  
**PRR:** HOLD → 条件付き GO になるまで本リストの Prod 項目は着手不可

---

## 0. ゲート（すべて必須）

- [ ] PRR Final が HOLD から **条件付き GO** に更新された  
- [ ] Go/No-Go が即時 NO-GO から **条件付き GO** に更新された  
- [ ] 公式スタックが **A-05（A-03 除外）** で文書凍結された  
- [ ] 本 Integration Design / Spec が承認された  

---

## 1. 設計・安全

- [ ] A-03 本番禁止が Ops Runbook に明記  
- [ ] A-03∧A-05 mutex が仕様・テスト計画にある  
- [ ] Flag 既定 OFF がリポジトリで確認できる  
- [ ] Shadow 非購入が仕様にある  
- [ ] Purchase は Decision pick のみ  

---

## 2. Staging

- [ ] Prediction Staging に A-05 経路を配線（応答は当面 Control 可）  
- [ ] Shadow M1: fail-open · ログ出力  
- [ ] Canary M2 小% の Flag Mesh 動作確認  
- [ ] レイテンシ p95 が合意内  
- [ ] 監視ダッシュボード（Hit/wr1/churn/error/promote）接続  
- [ ] **Rollback ドリル PASS**（Rollback Checklist）  

---

## 3. Production Shadow（M1）

- [ ] Prod 配線承認  
- [ ] Mesh: A-05 既定 OFF · Shadow runtime のみ許可  
- [ ] A-03 OFF 確認  
- [ ] 購入が Control のみであることをサンプリング検証  
- [ ] 最低観察窓（例: 7日 or N 合意）で wr1=0  

---

## 4. Production Canary（M2）

- [ ] 別承認チケット  
- [ ] Canary % 定義（例: 1% → 5% → 20%）  
- [ ] A-05（+方針どおり A-01/A-04）Mesh ON  
- [ ] 各段階で Hard Gate: wr1=0 · churn=0 · ΔHit>0  
- [ ] 異常時即 Rollback Checklist 実行可能な体制  

---

## 5. Full（M3）— 最終

- [ ] Canary 全段階 PASS  
- [ ] Ops / Explain / UI 影響レビュー完了  
- [ ] 公式 Baseline 文書を A-05 系に更新  
- [ ] 事後監視計画（週次 wr1）  

---

## 6. 明示的に今やらないこと

- [x] ~~本 Round でコード実装~~ → **禁止のため実施しない**  
- [x] ~~Flag 既定 ON~~ → **禁止**  
- [x] ~~Prod Rollout 実行~~ → **禁止**  

---

## 7. Stop

Checklist の定義まで。チェック実行・配線は行わない。
