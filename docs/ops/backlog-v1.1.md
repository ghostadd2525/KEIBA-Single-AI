# Backlog — Version 1.1

**基準:** Stable Baseline `v1.0.0-stable`（`08c7986`）— **FROZEN**（[`v1.0-freeze-declaration.md`](./v1.0-freeze-declaration.md)）  
**フェーズ:** Version 1.0 クローズ後の次期開発候補  
**更新:** 2026-07-21  
**引継ぎ元:** [`v1.0-completion-report.md`](./v1.0-completion-report.md)

Version 1.1 は **本番安定（1.0 Freeze）を維持したまま** 既知課題を潰すリリース。  
RePick 製品 ON や予想ロジック既定変更は、別ゲートなしでは入れない。  
**`v1.0.0-stable` への直接改変は禁止。** 作業は本 Backlog / `research/*` のみ。

---

## 優先度定義

| 優先度 | 意味 |
|--------|------|
| P0 | 運用リスク・データ品質の本丸（1.1 で着手推奨） |
| P1 | 接続・供給の拡張（HOLD 解除条件付き） |
| P2 | UX / 監視の改善 |
| P3 | research。製品 Flag ON は条件付き |

---

## Backlog

### B1.1-01 — feature / market データ充実による `mock_fallback` 削減（P0）

- **問題:** KI-01。本番一覧の大半が `mock_fallback`
- **ゴール:** 対象開催における `real_ai` 比率の改善（数値目標は着手時に設定）
- **作業例:** feature CSV / market 供給、欠落理由のダッシュボード化、カバレッジ監視
- **依存:** データ供給。Collector Real は B1.1-02（HOLD 中は代替ソース可）
- **完了条件:** スモークで `provider=python` かつ合意した `real_ai` 比率を満たす

### B1.1-02 — Collector Real KeibaNet 接続（P1 / HOLD 解除）

- **問題:** KI-03。RC-1 はコードのみ、本接続 HOLD
- **ゴール:** O-1 検証 PASS 後、Controlled → 本番 Collector の段階的有効化
- **必須:** [`collector-o1-real-keibanet-validation-plan.md`](./collector-o1-real-keibanet-validation-plan.md)
- **禁止（解除前）:** 本番 `.env` への常時 `EXPECT_KEIBANET_*`、無計画な timer enable
- **完了条件:** 検証レポート承認 + Go-Live チェックリスト署名

### B1.1-03 — RePick V2（research 扱い）（P3）

- **問題:** KI-04。AB Exit FAIL、Flag OFF
- **扱い:** **research のみ**（`research/repick-v2/` + docs）。製品経路・Flag ON は 1.1 必須ではない
- **許可:** Failure / Trigger Narrowing（V2.1）の机上・オフライン実験
- **禁止:** 本番 `WIN5_REPICK_V2_ENABLED=1`、Exit 未達での既定 ON
- **製品化条件:** Exit Criteria 全合格 + Stop Criteria 遵守 + 明示リリース承認

### B1.1-04 — UI 改善（P2）

- **候補:** 一時ID URL の自動入力、fallback 理由の利用者向け表示、メンテナンス/エラーの分かりやすさ、モバイル VQA 残件
- **制約:** Auth / 招待契約を壊さない。デザインシステム既存トーンを維持
- **完了条件:** 対象画面の受け入れチェック + 回帰（ログイン/setup/予想一覧）

### B1.1-05 — 運用監視・デプロイ耐性（P0/P2）

- **問題:** KI-02。overlay 手作業漏れで AI ダウンしうる
- **作業例:**
  - デプロイ手順のチェックリスト化（Runbook 準拠）の徹底
  - overlay 同期を含むデプロイスクリプト（ops のみ、承認後）
  - `mock_fallback` 比率・health・Pages deploy の監視アラート
  - OPS Monitor / Result Automation の定常運用
- **完了条件:** 手順どおりの再デプロイで overlay 起因の起動失敗が再発しないこと

---

## 1.1 に入れないもの（明示）

| 項目 | 理由 |
|------|------|
| RePick V2 製品既定 ON | Exit 未達 |
| Prediction V2 F01 市場特徴の製品化 | ROI Archived |
| Real KeibaNet の検証なし Go-Live | HOLD 方針 |

---

## 進め方

1. 運用フェーズでは **v1.0.0-stable** を本番基準に固定
2. 1.1 作業は feature branch → PR → ステージング検証 → 新タグ（例: `v1.1.0`）
3. 各 Backlog 開始時に Issue を切り、Known Issues ID（KI-xx）をリンクする

Issue テンプレ: [`ISSUE-TEMPLATE.md`](./ISSUE-TEMPLATE.md)
