# Collector 平日自動収集 — 本番稼働確認レポート

**日付:** 2026-07-21  
**実施者:** Cursor Agent  
**対象週:** `week_id=2026-07-25`（7/25-26 開催）  
**反映コミット:** `bd13181`

---

## 1. 実施結果サマリー

| # | 項目 | 結果 |
|---|------|------|
| 1 | main へ push | ✅ `bd13181` |
| 2 | EC2 git pull | ✅ Fast-forward |
| 3 | collect.env 設定 | ✅ `/etc/expect-ai/collect.env` |
| 4 | EXPECT_KEIBANET_BASE_URL | ⚠️ `https://race.netkeiba.com`（**API 非対応 → 404**） |
| 5 | systemd timer 有効化 | ✅ `enabled`（月〜金 06:30 JST） |
| 6 | service 手動起動 | ✅ 正常終了（exit 2: failed jobs あり） |
| 7 | journalctl | ✅ ログ出力確認 |
| 8 | Coverage 生成 | ✅ `coverage_2026_07_25_latest.json` |
| 9 | ETL → SQLite | ⚠️ READY 0件のため ingest 0 |
| 10 | prediction_ready | ❌ `false`（KeibaNet 404 のため） |

---

## 2. journalctl 抜粋（2026-07-21 初回実行）

- Planner: 48 races × 2 artifact → enqueue 完了
- Collect: **dequeued=68**（200/日上限内）、全件 `HTTP 404 from KeibaNet`
- Budget: used=68, remaining=132
- ETL: races=0, entries=0
- Coverage: `prediction_ready: false`, `total_races_expected: 48`

---

## 3. ブロッカー — EXPECT_KEIBANET_BASE_URL

指定 URL `https://race.netkeiba.com/top/?rf=navi` は **netkeiba 公開 Web ページ**であり、Collector が要求する **KeibaNet PI JSON API** ではありません。

Collector が呼ぶエンドポイント例:

```
GET {BASE_URL}/v1/static/race_meta?date=2026-07-25&venue=新潟&race_no=1
GET {BASE_URL}/v1/static/entries_core?...
```

`https://race.netkeiba.com/v1/static/race_meta` → **HTTP 404**（検証済み）

**必要な値:** O-1 検証済みの **PI 接続用ベース URL**（partner API ホスト）。netkeiba トップページ URL ではありません。

---

## 4. 本番 EC2 状態（インフラ）

```bash
# timer
systemctl is-enabled expect-collect-weekday.timer  # enabled

# collect.env（秘密値はマスク）
grep -E '^EXPECT_' /etc/expect-ai/collect.env

# coverage
cat .../var/collect/coverage/coverage_2026_07_25_latest.json
```

---

## 5. 次アクション

1. **正しい PI API ベース URL** を `/etc/expect-ai/collect.env` の `EXPECT_KEIBANET_BASE_URL` に設定
2. `sudo systemctl start expect-collect-weekday.service` で再実行
3. `jobs_ready` 増加・ETL ingest > 0・金曜 EOD で `prediction_ready: true` を確認

---

## 6. 変更ファイル一覧（bd13181）

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
