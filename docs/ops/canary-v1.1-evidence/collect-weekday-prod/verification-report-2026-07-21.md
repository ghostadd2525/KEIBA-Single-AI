# Collector 平日自動収集 — 本番稼働確認レポート

**日付:** 2026-07-21  
**実施者:** Cursor Agent  
**対象週:** `week_id=2026-07-25`（7/25-26 開催）

---

## 1. 実施内容

| # | 項目 | 結果 |
|---|------|------|
| 1 | 本番運用設定（collect.env.example） | ✅ 作成 |
| 2 | Scheduler 有効化（systemd timer） | ✅ 定義作成（EC2 反映要） |
| 3 | 平日自動収集 runner | ✅ `collect_weekday_runner.py` |
| 4 | ETL 自動実行 | ✅ ingest_ready_race_meta / entries_core 組込 |
| 5 | Coverage 記録 | ✅ `EXPECT_COLLECT_COVERAGE_DIR` |
| 6 | ローカル smoke | ✅ `test_collect_weekday_runner` PASS |

---

## 2. ローカル検証（Mock KeibaNet）

```
tests.ops.test_collect_weekday_runner.CollectWeekdayRunnerTest.test_run_collect_day_mock ... ok
Ran 1 test in 0.952s — OK
```

- Planner → Scheduler → Collector → ETL → Coverage 一連動作確認済み
- `EXPECT_COLLECT_DAILY_LIMIT=200` で dequeue 動作

---

## 3. 本番 EC2 反映（要オペレータ実行）

本環境から EC2 SSH 不可のため、以下を **本番サーバで実行** してください。

```bash
cd /opt/expect-ai/current && git pull --ff-only origin main
# collect.env 設定 → timer enable → 手動 start
# 詳細: docs/ops/collector-production-weekday-runbook.md
```

### 確認コマンド

```bash
systemctl is-active expect-collect-weekday.timer
journalctl -u expect-collect-weekday.service -n 30 --no-pager
cat /var/lib/expect-ai/collect/coverage/coverage_2026_07_25_latest.json
curl -sS http://127.0.0.1:8000/api/data/coverage -H "Authorization: Bearer ..."
```

---

## 4. 既知の制約

| 項目 | 内容 |
|------|------|
| KeibaNet URL | `EXPECT_KEIBANET_BASE_URL` は本番 secret。リポジトリに含めない |
| 開催カレンダー | 毎週手動更新（`config/collect-calendars/`） |
| entries_core | 枠順確定前（〜水曜）は race_meta のみ enqueue |
| FeatureBuilder | entries_core ETL は races/entries/horses。`features` CSV は別途 Phase E |

---

## 5. 次アクション

1. EC2 で collect.env + timer 有効化
2. 2026-07-21 手動 `systemctl start expect-collect-weekday.service`
3. 金曜 EOD: `prediction_ready` + DB races 件数確認
4. `/api/predictions` で `real_ai` 比率トレンド記録（KI-01）

---

## 6. 変更ファイル一覧

| パス | 内容 |
|------|------|
| `services/win5-ai/app/ops/collect_weekday_runner.py` | 平日オーケストレーション runner |
| `infra/aws/systemd/expect-collect-weekday.service` | oneshot service |
| `infra/aws/systemd/expect-collect-weekday.timer` | Mon-Fri 06:30 JST |
| `infra/aws/systemd/collect.env.example` | 本番 env テンプレ |
| `config/collect-calendars/week_2026_07_25.json` | 初回週カレンダー |
| `tests/ops/test_collect_weekday_runner.py` | smoke test |
| `docs/ops/collector-production-weekday-runbook.md` | 運用手順書 |
| `docs/ops/operations-runbook.md` §7 | HOLD → Production 更新 |
