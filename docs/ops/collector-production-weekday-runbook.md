# Collector 平日自動収集 — 本番運用手順書

**Status:** Production  
**更新:** 2026-07-21  
**前提:** C-0〜C-8 / RC-1 実装済み。O-1 Real KeibaNet 検証 GO 済み。

---

## 1. 目的

PI 接続制限（約 200 件/日）内で、**月曜〜金曜**に週末開催分の STATIC_CORE（`race_meta` / `entries_core`）を自動取得し、Raw → SQLite → FeatureBuilder まで ETL する。

---

## 2. アーキテクチャ（既存基盤の接続のみ）

```
expect-collect-weekday.timer (Mon-Fri 06:30 JST)
  → expect-collect-weekday.service (oneshot)
    → collect_weekday_runner.py
      → CollectPlanner（初回のみ）
      → CollectRetry
      → CollectScheduler.dequeue_pending（Budget 200/日）
      → KeibaNetCollector.run_job
      → EtlFromRaw.ingest_ready_* 
      → FridayGate（金曜のみ）
      → Coverage JSON
```

---

## 3. 環境変数（`/etc/expect-ai/collect.env`）

| 変数 | 必須 | 説明 |
|------|------|------|
| `EXPECT_KEIBANET_BASE_URL` | **Yes** | KeibaNet API ベース URL |
| `EXPECT_COLLECT_DAILY_LIMIT` | Yes | 日次上限（推奨 **200**） |
| `EXPECT_AI_DB_PATH` | Yes | Prediction 共有 SQLite |
| `EXPECT_COLLECT_MANIFEST_DIR` | Yes | 週次 Manifest |
| `EXPECT_COLLECT_RAW_DIR` | Yes | Raw Store |
| `EXPECT_COLLECT_COVERAGE_DIR` | Yes | 取得率レポート |
| `EXPECT_COLLECT_CALENDAR_DIR` | Yes | 開催カレンダー JSON 置き場 |
| `EXPECT_COLLECT_DRAW_CONFIRMED` | No | `1` で entries_core 強制 enqueue。未設定時は **木曜以降自動** |

---

## 4. 開催カレンダー

週次ファイル: `config/collect-calendars/week_YYYY_MM_DD.json`（`week_id` = 土曜日）

```json
{
  "calendar_version": "jra-calendar-2026-w30-prod",
  "week_id": "2026-07-25",
  "days": [
    { "race_date": "2026-07-25", "venues": { "新潟": 12, "中京": 12 } },
    { "race_date": "2026-07-26", "venues": { "新潟": 12, "中京": 12 } }
  ]
}
```

**毎週月曜前**に JRA 公式スケジュールで更新すること。

---

## 5. デプロイ手順

```bash
# 1. コード反映
cd /opt/expect-ai/current
git pull --ff-only origin main
cd services/win5-ai && python3 -m app.data.import_csv migrate

# 2. ディレクトリ
sudo mkdir -p /var/lib/expect-ai/collect/{manifests,raw,coverage}
sudo chown -R expect:expect /var/lib/expect-ai/collect

# 3. env
sudo install -m 640 -o root -g expect \
  infra/aws/systemd/collect.env.example /etc/expect-ai/collect.env
sudo chmod 640 /etc/expect-ai/collect.env
# vi /etc/expect-ai/collect.env  → EXPECT_KEIBANET_BASE_URL 設定

# 4. systemd
sudo cp infra/aws/systemd/expect-collect-weekday.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now expect-collect-weekday.timer

# 5. 初回手動実行
sudo systemctl start expect-collect-weekday.service
journalctl -u expect-collect-weekday.service -n 80 --no-pager
```

---

## 6. 完了条件（金曜 EOD）

| 条件 | 確認 |
|------|------|
| `race_meta` + `entries_core` が Prediction Ready | `coverage_*_latest.json` → `prediction_ready: true` |
| DB に races / entries 反映 | `sqlite3 $EXPECT_AI_DB_PATH "SELECT COUNT(*) FROM races;"` |
| `mock_fallback` 比率改善（KI-01） | `/api/data/coverage` または diagnostics |

---

## 7. トラブルシュート

| 症状 | 対処 |
|------|------|
| `EXPECT_KEIBANET_BASE_URL not set` | collect.env 設定 + daemon-reload |
| `calendar not found` | `week_*.json` を CALENDAR_DIR に配置 |
| Budget 枯渇（dequeued=0） | 正常 — 翌営業日に繰越。Manifest budget を確認 |
| entries_core 未 enqueue | 木曜前は race_meta のみ。`EXPECT_COLLECT_DRAW_CONFIRMED=1` または木曜以降待ち |
| ETL 0件 | Raw READY 確認 → `ingest_ready_*` 手動再実行 |

---

## 8. 関連ドキュメント

- [`operations-runbook.md`](./operations-runbook.md) §7
- [`collector-weekday-dispersion.md`](./collector-weekday-dispersion.md)
- [`collector-o1-real-keibanet-validation-plan.md`](./collector-o1-real-keibanet-validation-plan.md)
- [`data-foundation-phase-d.md`](./data-foundation-phase-d.md)
