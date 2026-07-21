# GameDay Live E2E — Production Dry Run

**Phase:** OPS-Hardening（H-3）  
**目的:** Production 環境で開催日パイプラインを人手なし完走できることを確認する。  
**方針:** 新機能なし。既存機能の統合確認のみ。Prediction Core は変更しない。

---

## 0. 前提

| 項目 | 確認 |
|------|------|
| EC2 Python AI + cloudflared | 稼働 |
| Cloudflare Pages（BFF） | デプロイ済 |
| `AI_BASE_URL` / API Key / `OPS_MONITOR_KEY` | 設定済 |
| systemd: `expect-ai`, `expect-result-automation.timer`, `expect-ops-monitor.timer` | enable |
| 対象日 `RACE_DATE` | JST YYYY-MM-DD（開催日または dry-run 用） |
| 結果 CSV | ResultProvider が読めるパスに配置 |

**推奨:** 初回は `maintenance_mode: true` のまま内部 API のみ検証し、公開切替は最後に行う。

---

## 1. 実行手順

### Step A — 開催日開始（公開）

```bash
# beta.json: maintenance_mode false → Pages デプロイ（公開する場合）
# またはメンテのまま API のみ検証
curl -sS "https://<pages>/api/health" | jq .
```

期待: `status` が `ok` または RA 問題時 `degraded`。`result_automation` フィールドあり。

### Step B — ETL

```bash
curl -sS -H "X-Api-Key: $EXPECT_AI_API_KEY" \
  "$AI_BASE_URL/v1/admin/etl/status?date=$RACE_DATE" | jq .
# 必要なら schedule / import-day を実行（既存 Admin API）
```

期待: 最新 ETL が `failed` でない。

### Step C — Prediction

```bash
curl -sS -H "X-Api-Key: $EXPECT_AI_API_KEY" \
  "$AI_BASE_URL/v1/predictions?date=$RACE_DATE" | jq '.ok, (.data|length)'
```

期待: HTTP 200、対象日の race が取得できる（件数 > 0）。

### Step D — Conversation

```bash
curl -sS -X POST -H "X-Api-Key: $EXPECT_AI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message":"health ping","session_id":"gameday-e2e"}' \
  "$AI_BASE_URL/v1/conversation/chat" | jq .
```

期待: エラーなく応答。

### Step E — Result Automation

```bash
# EC2
cd /opt/expect-ai/current/services/win5-ai
python -m app.ops.result_automation_runner \
  --date "$RACE_DATE" --trigger manual --force
```

期待: `run_status` が `COMPLETED` または `DEGRADED`（意図した degraded 理由がある場合）。

### Step F — Manifest

```bash
ls -la "$EXPECT_IMPROVEMENT_EVIDENCE_DIR/manifest/$RACE_DATE/"
# run.json summary.json index.json
jq . "$EXPECT_IMPROVEMENT_EVIDENCE_DIR/manifest/$RACE_DATE/summary.json"
```

期待: 3 ファイル存在。`summary.run_id` が DB 最新 run と一致。

### Step G — Evidence

```bash
find "$EXPECT_IMPROVEMENT_EVIDENCE_DIR" -path "*/$RACE_DATE/*" -name "*.json" | head
npm run evidence:sync -- --date "$RACE_DATE"
```

期待: miss / feature_missing 等が出力され、sync が成功。

### Step H — Statistics / Self Evaluation

```bash
sqlite3 "$EXPECT_AI_DB_PATH" \
  "SELECT COUNT(*) FROM race_evaluations WHERE race_id LIKE '${RACE_DATE}%';"
sqlite3 "$EXPECT_AI_DB_PATH" \
  "SELECT id, created_at FROM self_evaluation_runs ORDER BY id DESC LIMIT 3;"
```

期待: evaluations ≥ 1（結果がある場合）、self_evaluation_runs が増えている。

### Step I — OPS-Monitor

```bash
curl -sS -H "X-Ops-Monitor-Key: $OPS_MONITOR_KEY" \
  "https://<pages>/api/ops/monitor" | jq '.data.status, .data.checks[] | {name, ok, error}'
```

期待: `result_automation.ok == true`（FAILED / stale / manifest 欠落なし）。全体 `status: ok`。

### Step J — Recovery

```bash
# 1) ACTIVE を模擬（または過去 orphan を利用）
# 2) orphan → FAILED
python -m app.ops.result_automation_runner --mode recover

# 3) parent_run_id 付き retry
FAILED_ID=$(sqlite3 "$EXPECT_AI_DB_PATH" \
  "SELECT id FROM result_automation_runs WHERE status='FAILED' ORDER BY id DESC LIMIT 1;")
python -m app.ops.result_automation_runner \
  --date "$RACE_DATE" --trigger retry --parent-run-id "$FAILED_ID" --force
```

期待: 新 `run_id`、`parent_run_id == FAILED_ID`。Monitor が再実行後に健全化。

### Step K — 公開終了（任意）

```bash
# maintenance_mode: true → デプロイ
```

---

## 2. チェックリスト（記録用）

| # | 項目 | PASS | メモ（日時・実行者） |
|---|------|:----:|----------------------|
| 1 | ETL | ☐ | |
| 2 | Prediction | ☐ | |
| 3 | Conversation | ☐ | |
| 4 | Result Automation | ☐ | |
| 5 | Manifest | ☐ | |
| 6 | Evidence | ☐ | |
| 7 | Statistics | ☐ | |
| 8 | Self Evaluation | ☐ | |
| 9 | OPS-Monitor（含 result_automation） | ☐ | |
| 10 | Recovery（orphan→FAILED→retry） | ☐ | |

**完了条件:** 上記 10 項目すべて PASS。失敗時は Issue を記録し `ops-hardening-runbook.md` の復旧手順へ。

---

## 3. 失敗時の切り分け

| 症状 | 確認 |
|------|------|
| Monitor `result_automation` 失敗 | `GET /v1/admin/results/status` の `issues` |
| ACTIVE 残存 | `--mode recover` → retry |
| Manifest 欠落 | `--evidence-only --force` |
| ETL failed | ETL Admin + Monitor `etl` |
| Prediction 空 | Coverage / データソース（Core は変更しない） |

---

## 4. 実行記録テンプレート

```
Date (JST):
Operator:
Environment: production | staging
RACE_DATE:
maintenance_mode during run:
Checklist PASS count: /10
Monitor URL snapshot:
Notes:
```
