# Monitoring — 監視項目一覧

Phase F 運用監視の参照ドキュメント。

---

## エンドポイント

```http
GET /v1/admin/monitoring
GET /v1/data/coverage
GET /v1/admin/etl/status
GET /v1/admin/dashboard
```

---

## 監視項目

### 1. ETL 失敗率

| 項目 | 説明 |
|------|------|
| `etl.total_runs` | 直近 100 実行 |
| `etl.failed_runs` | status=failed |
| `etl.failure_rate_pct` | failed / total × 100 |
| `etl.latest` | 最新 run 詳細 |

**対応:** `stopped_at_step`, `error_reason`, `missing_data_json` を確認 → CSV/ソース修正 → `POST /v1/admin/etl/schedule` 再実行

---

### 2. Coverage 推移

| 項目 | 説明 |
|------|------|
| `coverage.race_total` | カタログ総数 |
| `coverage.real_ai` | 実 AI 件数 |
| `coverage.mock` | フォールバック件数 |
| `coverage.coverage` | real_ai % |
| `coverage_trend[]` | validation_runs 履歴 |

**対応:** `missing_races` / `missing_features` を ETL で解消

---

### 3. fallback_reason 推移

| 項目 | 説明 |
|------|------|
| `fallback_reason_trend` | reason → count |

主要 reason:
- `race_not_found` → races CSV / DB 不足
- `market_feature_missing` → features 不足
- `platform_missing` → AI_PLATFORM_ROOT 未設定

---

### 4. Prediction エラー

| 項目 | 説明 |
|------|------|
| `prediction_errors` | exception / prediction_failed / timeout |
| `log_errors` | logs テーブル error 件数 |

---

### 5. API 応答時間

| 項目 | 説明 |
|------|------|
| `api_performance.by_name` | path 別 p50/p95/avg (ms) |

記録先: `var/ops/metrics.jsonl`  
各 HTTP レスポンス送信時に自動記録。

---

### 6. DB サイズ

| 項目 | 説明 |
|------|------|
| `db.size_bytes` | SQLite ファイルサイズ |
| `db.size_mb` | MB 換算 |

環境変数: `EXPECT_AI_DB_MAX_MB`（デフォルト 500）

---

## アラート

`monitoring.alerts[]` に自動生成:

| code | level | 条件 |
|------|-------|------|
| `etl_high_failure_rate` | warning | ETL 失敗率 > 20% |
| `low_coverage` | info | coverage < 5% |
| `prediction_errors` | warning | prediction エラー > 0 |
| `slow_api` | warning | 任意 API p95 > 5000ms |
| `db_size` | warning | DB > 上限 |

---

## 推奨監視サイクル

| 頻度 | 確認 |
|------|------|
| 毎時 | `/health`, `/v1/admin/monitoring` alerts |
| 開催日 AM | ETL schedule + coverage |
| 開催日 PM | fallback_reason 推移 |
| 週次 | DB サイズ, baseline 再測定 |
