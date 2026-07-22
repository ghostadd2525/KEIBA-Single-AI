# Version 2 — Release Checklist（Production 切替前）

**Date:** 2026-07-22  
**Status:** Release Candidate 付帯  
**正本 RC:** [`v2-rc-report.md`](./v2-rc-report.md)  
**目的:** Production 切替 **前**の確認項目。本チェックリスト自体はコード変更を含まない。

---

## 0. 前提

- [x] Version 2 の 4 Final Report を受領・クローズ確認済  
- [x] 本 RC ドキュメント一式をレビュー済  
- [x] ロールバック方針: **全 v2 Flag OFF**（+ 必要なら PE Flag OFF）で v1.1 相当に戻せることを理解済  

---

## 1. 互換性・契約

- [x] PredictionBundle 2.0 クライアントが壊れていないこと（既存 E2E / smoke）  
- [x] PI `/v1/races` · `/v1/predictions` · `/health` が本番で 200/契約どおり  
- [x] RaceCardSummary 利用時も **契約フィールド追加なし**であることの再確認  
- [x] Flag 配信後も Bundle / PI 契約維持（本番疎通）  

---

## 2. Accuracy（EC2 / Core）

- [ ] 採用構成: `WIN5_POOL_ENTRY_V2_ENABLED=ON`  ← **SSH 不可のため未了（手動）**  
- [ ] 不採用: `WIN5_REPICK_V2_ENABLED=OFF` · `WIN5_CE_V2_ENABLED=OFF`  ← **未確認**  
- [ ] サンプル予測で Hit 系メトリクス / ログに異常がないこと  ← EC2 後  
- [x] Delete Boundary を変更していないこと（コード変更なし）  

---

## 3. UI Enhancement

- [x] 段階 ON: `v2_race_cards` + `v2_race_list_ui`（本番 beta）  
- [x] `config/beta.json` / `public/config/beta.json` 同期  
- [x] ON 後: HTML / Admin API で RaceCardSummary 確認  
- [ ] OFF に戻して v1.1 一覧に戻ることを確認（ロールバック試験）— 切替直後は未実施  

---

## 4. Explainability

- [x] BFF `EXPLAIN_V2_ENABLED` → Web `v2_explain` ON  
- [ ] Core `WIN5_EXPLAIN_V2_ENABLED` ON  ← **EC2 手動待ち**  
- [x] race API に explain オブジェクト存在（Admin）  
- [ ] Kaoba: `context.v2_explain` 付与時のみ構造化理由 — 開催日/ログイン後フォロー  

---

## 5. Operations

- [ ] EC2 `ops-monitor.env`: `PI_HEALTH_URL`  ← SSH 待ち  
- [ ] `expect-ops-monitor.timer` 動作確認  ← SSH 待ち  
- [x] Pages: `PI_BASE_URL` 稼働（health.pi / monitor）  
- [x] `v11_ops_dashboard` + `v2_ops_dashboard` + Admin で Dashboard 取得  
- [x] Slack 未設定でも probe 動作（no-op）  
- [x] Runbook 文書存在  

---

## Production Release 記録

**完了レポート:** [`docs/releases/v2-production-release-report.md`](./v2-production-release-report.md)  
**実施日:** 2026-07-22  
**Pages deploy:** Success（`a8d47c7b.keiba-single-ai.pages.dev` → expect-keiba.com）

---

## 6. セキュリティ・権限

- [ ] `/api/ops/monitor` の `OPS_MONITOR_KEY`  
- [ ] `/api/ops/dashboard` が非管理者に 403 / Flag OFF で 404  
- [ ] Slack webhook URL がリポジトリ・フロントに埋まっていないこと  
- [ ] `admin_user_ids` が意図どおり  

---

## 7. 監視・アラート（切替直後）

- [ ] ALT-E02/E05 の試験（可能なら staging）または Runbook 机上確認  
- [ ] `/api/health` の `pi` フィールド確認  
- [ ] incidents / metrics のローテーション容量（EC2）  

---

## 8. コミュニケーション

- [ ] リリースノート（本 ChangeLog）をステークホルダ共有  
- [ ] Known Limitations（V3 持ち越し）を共有  
- [ ] ロールバック手順の連絡先・所要時間の合意  

---

## 9. Go / No-Go

| 判定 | 条件 |
|------|------|
| **GO** | 上記必須項目（契約・Flag OFF 恒等・Accuracy 採用 Flag・監視生存）がすべてチェック済 |
| **NO-GO** | PI 不通 · Bundle 破壊 · Flag OFF でも v1.1 と不一致 · PE 以外の不採用 Flag が誤 ON |

---

## 10. 切替後（参考・本 RC 範囲外）

- [ ] 24h: PI probe / Slack / Dashboard の誤検知確認  
- [ ] 開催日: race-cards · explain · favorites の実利用確認  
- [ ] Accuracy: Purchase 副作用の継続観測  

---

**Checklist 完了後にのみ Production Flag 切替を実施すること。**
