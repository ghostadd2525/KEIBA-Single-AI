# Version10 Ops — Evidence Collector Monitoring

**Date:** 2026-07-27  
**Scope:** Ops Dashboard / API による Research Evidence Collector 可視化

---

## 1. 表示項目

| KPI | 説明 | ソース |
|-----|------|--------|
| **Collector Status** | enabled / disabled | `RESEARCH_EVIDENCE_COLLECTOR` |
| **Success Rate** | ソースイベント成功率（7日） | `research_source_events` |
| **Missing Rate** | 1 − complete/total snapshots | `research_prediction_snapshots` |
| **Retry Count** | ジョブ Retry 累計 | `research_collect_jobs.retry_count` |
| **Source Latency** | PI board 取得平均 ms | `research_source_events.latency_ms` |
| **Source Availability** | 成功イベント比率 | 同上 |
| **Evidence Coverage** | predictions に対する snapshot 率 | snapshots / predictions |

---

## 2. Ops Console

**Monitor セクション** に **Evidence Collector** カードを追加。

| 項目 | 値 |
|------|-----|
| Live API | `GET /api/ops/evidence-collector` |
| Static fallback | `public/ops-data/evidence-collector.json` |
| Client | `public/assets/ops-console-v89.js` |

カード note 例:

```
success=0.95 · missing=0.12 · retries=3 · updated=2026-07-27T...
```

---

## 3. AI Backend API

```
GET /v1/admin/research/evidence/monitoring
```

レスポンス例:

```json
{
  "collector_status": "enabled",
  "success_rate": 0.92,
  "missing_rate": 0.35,
  "retry_count": 2,
  "source_latency_ms_avg": 840.5,
  "source_availability": 0.92,
  "evidence_coverage": {
    "predictions_total": 120,
    "snapshots_total": 45,
    "snapshots_complete": 12,
    "snapshots_partial": 33,
    "snapshot_rate": 0.375
  },
  "anti_leak_violations_total": 0
}
```

---

## 4. Publish（静的 JSON）

```bash
node scripts/ops/v10/publish-evidence-collector.mjs
```

本番 Pages デプロイ前、または EC2 cron で実行し `public/ops-data/evidence-collector.json` を更新。

---

## 5. アラート目安（運用）

| 条件 | 推奨アクション |
|------|----------------|
| `anti_leak_violations_total > 0` | 即調査（時刻設定 / PI キャッシュ） |
| `success_rate < 0.8`（7日） | PI / Tunnel 疎通確認 |
| `snapshot_rate` が週次で横ばい | Collector サイドカー起動確認 |
| `retry_count` 急増 | Netkeiba rate limit / timeout |

---

## 6. 週次レポート連携

`python -m app.research.collector_runner --weekly-report` 実行後:

- `evidence/research/reports/weekly/{week_id}.json`
- `research_evidence_daily` テーブル更新

Research Scheduler 本体は変更しない。Scheduler 終了後の **独立 cron** で実行。

---

## 7. 参照

- `docs/design/v10-evidence-collection-platform.md`
- `functions/api/ops/evidence-collector.js`
- `app/research/monitoring.py`
