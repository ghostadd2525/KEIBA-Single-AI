# Version10 Design — Evidence Collection Platform

**Status:** Implemented (Phase1 P0)  
**Date:** 2026-07-27  
**Hard Lock:** PE / CE / AI推論 / Prediction Logic / ResultAutomation / Challenge / Research Runtime — **未変更**

---

## 0. 目的

Prediction 生成時点の Evidence を Netkeiba / JRA（PI 経由）から収集し、**Research 専用 Prediction Snapshot** として蓄積する。  
Prediction Bundle とは完全分離。`prediction_id` のみで関連付ける。

本フェーズは **AI 改善ではなく Evidence Platform 構築** が目的。  
半年程度の蓄積後 → Evidence Mining → Young Horse Intelligence → Tie Resolver へ利用（別フェーズ）。

---

## 1. アーキテクチャ

```
predictions (Product DB, 読取のみ)
        │ poll / enqueue (sidecar)
        ▼
research_collect_jobs
        │
        ▼
ResearchCollectorRunner (別プロセス)
        │ PI GET /v1/races/{race_id}/board
        ▼
Phase1 Collector (Priority A/B)
        │ Anti-Leak filter
        ▼
research_prediction_snapshots + evidence/research/prediction-snapshots/**/*.json
        │
        ▼
research_evidence_daily / Weekly Report
```

| 原則 | 内容 |
|------|------|
| 非同期 | Prediction 永続化後、サイドカーがポーリング |
| Fail-open | 収集失敗でも Prediction / UI / Challenge は止めない |
| Anti-Leak | `observed_at <= prediction.created_at` 違反は保存しない |
| 分離 | Snapshot は Research API のみ。Bundle へ書込禁止 |

---

## 2. Phase1（P0）Evidence

| Priority | Feature | source_id |
|----------|---------|-----------|
| **A** | 人気 `popularity` | jra_odds_api / shutuba |
| **A** | 単勝 `win_odds` | jra_odds_api |
| **A** | 想定人気 `expected_popularity` | derived_expected_pop |
| **B** | 厩舎 `trainer` | netkeiba_shutuba |

取得経路: PI `GET /v1/races/{race_id}/board`（JRA type=1 + shutuba entries）

---

## 3. 実装コンポーネント

| パス | 役割 |
|------|------|
| `app/data/migrations/011_research_evidence.sql` | Research テーブル |
| `app/research/repository.py` | Job / Snapshot / Source events / Daily metrics |
| `app/research/store.py` | JSON Primary store |
| `app/research/collector/phase1.py` | Phase1 収集 |
| `app/research/collector/assembler.py` | Snapshot 組立 |
| `app/research/collector/runner.py` | Poll + Process + Retry |
| `app/research/collector_runner.py` | CLI entry |
| `app/research/anti_leak.py` | リークガード |
| `app/research/quality.py` | coverage / freshness / completeness / consistency |
| `app/research/monitoring.py` | Ops KPI |
| `app/research/weekly_report.py` | 週次レポート |
| `app/research/api.py` | HTTP handlers |
| `services/pi-keibanet-api/.../service.py` | `trainer` 露出（entries_full） |

---

## 4. Collector 要件（実装）

| 要件 | 実装 |
|------|------|
| Prediction 後非同期 | `ResearchCollectorRunner.poll_and_enqueue()` が未 Snapshot の prediction を検知 |
| Prediction を止めない | AI プロセス内に埋め込まず CLI サイドカー |
| Retry | `max_attempts=5`、一時障害時 `status=pending` へ戻す |
| Timeout | `RESEARCH_PI_TIMEOUT_SEC`（既定 20s） |
| Partial 保存 | `capture_status=partial` で P0 未充足でも保存 |
| Missing 理由 | runner ごと `missing[]` |
| ObservedAt | ソース `odds_updated_at` または fetch 時刻 |
| Anti-Leak | `accept_observation()` で拒否、違反フィールドは null |

---

## 5. Research Store

### DB（`research_*` 接頭で Product と隔離）

- `research_collect_jobs`
- `research_prediction_snapshots`（`UNIQUE(prediction_id)`）
- `research_source_events`
- `research_evidence_daily`

### JSON

```
evidence/research/prediction-snapshots/{race_date}/{race_id}/{prediction_id}.json
```

---

## 6. API

| Method | Path | 用途 |
|--------|------|------|
| GET | `/v1/research/prediction-snapshots/{prediction_id}` | Snapshot 取得（Research） |
| GET | `/v1/admin/research/evidence/monitoring` | Ops KPI |

---

## 7. 運用

### サイドカー起動

```bash
cd services/win5-ai
export PI_BASE_URL=http://127.0.0.1:8081
export RESEARCH_EVIDENCE_COLLECTOR=1
python -m app.research.collector_runner --once   # 1 batch
python -m app.research.collector_runner --loop   # 常駐
python -m app.research.collector_runner --weekly-report
```

### 環境変数

| 変数 | 既定 | 意味 |
|------|------|------|
| `RESEARCH_EVIDENCE_COLLECTOR` | `1` | 収集 ON/OFF |
| `RESEARCH_COLLECTOR_POLL_SEC` | `15` | ポーリング間隔 |
| `RESEARCH_COLLECTOR_MAX_ATTEMPTS` | `5` | Retry 上限 |
| `RESEARCH_COLLECTOR_DEADLINE_MIN` | `15` | Anti-Leak 期限 |
| `PI_BASE_URL` / `EXPECT_KEIBANET_BASE_URL` | — | PI 必須 |
| `RESEARCH_EVIDENCE_ROOT` | `{repo}/evidence/research` | JSON ルート |

### 週次レポート

Research Scheduler **終了後**（別 cron 推奨）:

```bash
python -m app.research.collector_runner --weekly-report
```

出力: `evidence/research/reports/weekly/{YYYY-Www}.json`

---

## 8. 変更境界

| 領域 | 本実装 |
|------|--------|
| PE / CE / AI / Prediction Logic | **未変更** |
| ResultAutomation / Challenge | **未変更** |
| Research Runtime (v8 runner) | **未変更** |
| PI entries_full | `trainer` 露出のみ |

---

## 9. 参照

- `docs/design/v10-younghorse-intelligence.md`
- `docs/design/v10-evidence-quality-model.md`
- `docs/design/v92-prediction-snapshot.md`
- `docs/design/v93-research-collector.md`
- `docs/ops/v10-evidence-monitoring.md`
- `docs/audit/v10-evidence-validation.md`
