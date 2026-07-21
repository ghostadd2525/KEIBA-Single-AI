# OPS-Hardening Runbook

**Phase:** OPS-Hardening  
**目的:** Production Readiness Report の High Issue（H-1 / H-2 / H-3）を解消し、Production Ready 条件を満たす。  
**対象外:** Prediction Core 変更、新機能追加。

---

## 1. 解消した High Issue

| ID | 内容 | 対応 |
|----|------|------|
| **H-1** | OPS-Monitor が result_automation FAILED を検知しない | `/v1/admin/results/status` + BFF `probeResultAutomation` + `/api/health` 要約 |
| **H-2** | ACTIVE run がプロセス異常終了後に残る | 起動時 `fail_orphan_active_runs` → FAILED。parent_run_id 付き retry 可能 |
| **H-3** | 本番 Live E2E 未実施 | [`gameday-live-e2e.md`](./gameday-live-e2e.md) 手順とチェックリスト |

---

## 2. Monitor（H-1）

### 監視項目

| 条件 | 判定 |
|------|------|
| ACTIVE が `EXPECT_RA_ACTIVE_STALE_MINUTES`（既定 60）以上継続 | unhealthy |
| 直近 lookback（2 日）の最新 run が FAILED | unhealthy |
| 直近最新 run が DEGRADED | degraded（ok=false） |
| COMPLETED/DEGRADED なのに `manifest/.../run.json` 欠落 | unhealthy |
| COMPLETED/DEGRADED なのに `manifest/.../summary.json` 欠落 | unhealthy |

### エンドポイント

```bash
# Python（詳細）
curl -H "X-Api-Key: $EXPECT_AI_API_KEY" \
  "$AI_BASE_URL/v1/admin/results/status"

# Python liveness + RA 要約
curl "$AI_BASE_URL/health"

# BFF 統合監視（incident 記録）
curl -H "X-Ops-Monitor-Key: $OPS_MONITOR_KEY" \
  "https://<pages>/api/ops/monitor"

# BFF health（RA 要約付き）
curl "https://<pages>/api/health"
```

### Incident

`result_automation` チェック失敗時、既存 `logFailedChecks` 経由で `service: result_automation` が記録される。

---

## 3. Run Recovery（H-2）

### 動作

`result_automation_runner` 起動時（`--mode auto|date|recover`）:

1. ACTIVE 行を検索
2. 合法遷移で **FAILED** に更新（`error_json.reason = orphan_active_on_startup`）
3. `parent_run_id` 列は変更しない（孤児自身の id を次 run の parent に使える）

### コマンド

```bash
# orphan のみ FAILED 化
python -m app.ops.result_automation_runner --mode recover

# 自動スケジューラ（orphan 処理後に post/morning/recovery）
python -m app.ops.result_automation_runner --mode auto

# 明示 retry（親 run_id 指定）
python -m app.ops.result_automation_runner \
  --date YYYY-MM-DD --trigger retry --parent-run-id <id> --force
```

### 確認

```sql
SELECT id, status, parent_run_id, error_json
FROM result_automation_runs
ORDER BY id DESC LIMIT 5;
```

---

## 4. チェックリスト（Hardening 完了）

- [ ] `GET /v1/admin/results/status` が 200 で `ok` / `issues` を返す
- [ ] `GET /api/ops/monitor` の checks に `result_automation` がある
- [ ] `GET /api/health` に `result_automation` 要約がある
- [ ] ACTIVE 残存を `--mode recover` で FAILED 化できる
- [ ] FAILED 化した run_id を `parent_run_id` に指定して retry できる
- [ ] Live E2E 手順 [`gameday-live-e2e.md`](./gameday-live-e2e.md) を 1 回実行し記録した
- [ ] Production Readiness Report の High Issue が 0 件

---

## 5. 関連ファイル

| パス | 役割 |
|------|------|
| `app/ops/run_recovery.py` | orphan FAILED 化 + health 収集 |
| `app/ops/result_automation_runner.py` | 起動時 recover |
| `functions/_lib/opsMonitor.js` | `probeResultAutomation` |
| `functions/api/health.js` | RA 要約 |
| `docs/ops/gameday-live-e2e.md` | Live E2E |

---

## 6. ロールバック

Hardening のみのため、問題時は:

1. Monitor: Pages を前リビジョンへ（probe 追加のみ）
2. Recovery: runner を前版へ戻しても ACTIVE 手動 UPDATE で同等対応可

```sql
UPDATE result_automation_runs
SET status='FAILED', finished_at=datetime('now'),
    error_json='{"reason":"manual_orphan"}'
WHERE status NOT IN ('COMPLETED','DEGRADED','FAILED','SUPERSEDED');
```
