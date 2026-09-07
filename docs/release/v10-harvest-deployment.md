# Version10 Release — Harvest Deployment

**Date:** 2026-07-27 (JST)  
**Status:** Harvest 稼働中（EC2 Production）  
**Scope:** Evidence Collection Platform の本番デプロイ + 58 Prediction Backfill  
**Hard Lock:** PE / CE / AI / Prediction Logic / ResultAutomation / Challenge / Research Runtime — **未変更**

---

## 0. 結果サマリ

| 指標 | 値 |
|------|-----|
| Prediction 件数 | **58** |
| Snapshot 件数 | **58** |
| complete | **51** |
| failed（レガシー/キャナリー race_id） | **7** |
| Evidence JSON | **58** |
| `research_snapshot_features` | **2520** rows |
| `research_snapshot_quality` | **58** rows |
| 人気 Coverage（runner） | **100%** |
| 単勝 Coverage（runner） | **100%** |
| 想定人気 Coverage（runner） | **100%** |
| 厩舎 Coverage（runner） | **100%** |
| Collector systemd | **active (enabled)** |

**Harvest 成立条件:** 達成（本番 Win5 race_id 51件は complete + Feature ≥95%。全 Snapshot 行は 58/58）

---

## 1. 実施作業

### 1.1 Migration

適用: `011_research_evidence` / `012_research_snapshot_features`

| テーブル | 状態 |
|----------|------|
| `research_prediction_snapshots` | ✅ |
| `research_collect_jobs` | ✅ |
| `research_source_events` | ✅ |
| `research_evidence_daily` | ✅ |
| `research_snapshot_features` | ✅ |
| `research_snapshot_quality` | ✅ |

### 1.2 コード配置（EC2）

- `services/win5-ai/app/research/**`
- migrations `011` / `012`
- PI `service.py`（`trainer` 露出）
- `infra/aws/systemd/expect-research-evidence-collector.service`

### 1.3 PI 疎通

```
PI_BASE_URL=http://127.0.0.1:8081
GET /health → ok
board sample: odds/popularity/trainer すべて取得可
```

### 1.4 systemd

```
expect-research-evidence-collector.service
EnvironmentFile=/etc/expect-ai/research-evidence.env
ExecStart=python3 -m app.research.collector_runner --loop
```

### 1.5 Backfill

```bash
python3 -m app.research.collector_runner --backfill
# 結果: done=51, failed=7, snapshots=58
```

`RESEARCH_HARVEST_ASOF=1` — 過去 Prediction 向けに observed_at を prediction_created_at に帰属（Anti-Leak 形式を維持）。

---

## 2. Failed 7件（除外妥当）

| prediction_id | race_id | 理由 |
|---------------|---------|------|
| 1–3 | `2026-04-12-福島-11` | 非 Win5 ID → PI 400 |
| 4–5 | `20260725_sapporo_1` | 旧 collector ID → PI 400 |
| 6–7 | `2099-01-01/02-99-99` | キャナリー fixture → PI 404 |

これらは本番レース Evidence 対象外。Snapshot 行は failed として残置（監査用）。

---

## 3. 運用

```bash
sudo systemctl status expect-research-evidence-collector
sudo journalctl -u expect-research-evidence-collector -f
```

新規 Prediction はポーリングで自動 enqueue → Snapshot 化。

---

## 4. 参照

- `docs/audit/v10-harvest-production-validation.md`
- `docs/design/v10-evidence-collection-platform.md`
