# 月次運用レポート — テンプレート（v1.0.0-stable）

**使い方:** 毎月コピーして `docs/ops/reports/YYYY-MM-ops-report.md` 等に保存（パスは運用都合で可）。  
**Baseline:** `v1.0.0-stable`  
**設計書:** [`v1.0-ops-monitoring-design.md`](./v1.0-ops-monitoring-design.md)

---

# 月次運用レポート — YYYY-MM

| 項目 | 値 |
|------|-----|
| 対象月 | YYYY-MM |
| 作成日 | YYYY-MM-DD |
| 作成者 | |
| Production Baseline | `v1.0.0-stable`（`08c7986`） |
| 月末の本番 SHA / tag | |

---

## 1. エグゼクティブサマリ（3–5 行）

- 可用性:
- 重大インシデント:
- 品質（real_ai / mock_fallback）:
- ポリシー（Flag OFF / KeibaNet HOLD）:
- 翌月の最優先アクション:

**総合判定:** 安定 / 注意 / 要改善

---

## 2. デプロイ・変更実績

| 日付 | 面 | 内容（tag/SHA） | 結果 |
|------|----|-----------------|------|
| | Pages | | Success / Rollback |
| | EC2 | | |

特記（overlay 同期漏れ、メンテ等）:

---

## 3. 可用性

| コンポーネント | 目標 | 実績（概算可） | 重大ダウン時間 | 備考 |
|----------------|------|----------------|----------------|------|
| Pages | | | | |
| BFF `/api/health` | | | | |
| EC2 AI `/health` | | | | |
| Tunnel | | | | |
| Prediction API | | | | |
| Result Automation | | | | |

計測方法（プローブ / ログ / 目視）:

---

## 4. 品質指標

| 指標 | 月初 | 月末 | 月内最悪 | コメント |
|------|------|------|----------|----------|
| Prediction 件数 | | | | |
| mock_fallback 率 | | | | KI-01 参照 |
| AI 成功率（real_ai 率） | | | | |
| API エラー率 | | | | |
| API p95（predictions） | | | | |
| Login 成功率（代理指標可） | | | | |

データ不足・供給メモ:

---

## 5. Auth / 招待

| 項目 | 値 |
|------|-----|
| 新規一時ID 発行数 | |
| setup 完了数 | |
| ログイン障害 | 有 / 無（詳細） |
| invitations seed 更新 | 有 / 無 |

---

## 6. Alert・インシデント

### 6.1 件数

| レベル | 件数 |
|--------|------|
| Critical | |
| Warning | |
| Info | |

### 6.2 Critical / 主要 Warning 一覧

| 日付 | ID | 概要 | 影響 | 対応 | TTR |
|------|----|------|------|------|-----|
| | C- | | | | |

### 6.3 再発・横展開

-

---

## 7. ポリシー遵守

| チェック | 結果 | 証拠 |
|----------|------|------|
| `WIN5_REPICK_V2_ENABLED` 未設定（OFF） | OK / NG | |
| RePick が本番経路に未配線 | OK / NG | |
| Real KeibaNet HOLD（`EXPECT_KEIBANET_*` なし） | OK / NG | |
| Collector 本接続ジョブ未稼働 | OK / NG | |

違反時の対応:

---

## 8. Result Automation / DB

| 項目 | 結果 |
|------|------|
| `result_automation` 月間の failed / stale 傾向 | |
| schema_migrations（001–008） | |
| DB バックアップ実施 | 実施日: |

---

## 9. Known Issues 状況

| ID | 状態 | 変化 | 1.1 Backlog |
|----|------|------|-------------|
| KI-01 mock_fallback | | 改善 / 横ばい / 悪化 | B1.1-01 |
| KI-02 overlay | | | B1.1-05 |
| KI-03 KeibaNet HOLD | HOLD 維持 | | B1.1-02 |
| KI-04 RePick OFF | OFF 維持 | | B1.1-03 |

---

## 10. 翌月アクション

| 優先 | アクション | 担当 | 期限 | Backlog |
|------|------------|------|------|---------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

---

## 11. 添付・参照

- プローブ生データ / スクリーンショット:
- インシデントログ:
- 関連 PR / tag:

---

## 署名

| 役割 | 氏名 | 日付 |
|------|------|------|
| 作成 | | |
| 確認 | | |
