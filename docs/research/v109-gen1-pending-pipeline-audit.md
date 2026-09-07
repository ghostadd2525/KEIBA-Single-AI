# Phase GEN1 — Pending Pipeline Audit

**Race ID:** `2026-08-01-01-02`  
**Audit time:** 2026-07-29 JST  
**Environment:** Production (`https://expect-keiba.com`)  
**Scope:** Prediction generation pipeline（UI4 は対象外・正常前提）

---

## Executive Verdict

Ready にならない主因は **UI / Contract ではなく Features 未生成**。

本システムに「202 PENDING を見て自動 enqueue する Prediction Queue Worker」は無い。  
`GET /api/predictions/:id` は **既存 features 上でオンデマンド CE** するだけ。  
`2026-08-01` の features が無いため永遠に `prediction_available=false` → HTTP 202。

加えて、監査日時点で **当日 `2026-07-29` も PENDING**。`expect-pi-race-refresh` 系の健全性が疑わしい。

---

## 1. Pipeline Trace（期待 vs 実測）

### Expected path（Ready まで）

```text
[Catalog] /v1/races?date=YYYY-MM-DD  status=published
        │
        ▼
[Timer] expect-pi-race-refresh.timer  (*/15min, window 08:00–20:00 JST)
        │  default --date = today JST
        ▼
[Worker] prod_race_refresh.py  (oneshot, NOT a queue consumer)
        │  shutuba → runners → history → build_features
        ▼
[Save] demo_daily_outputs/{date}/demo_runners_pace_market_features.csv
        │
        ▼
[Read path] GET /v1/predictions/{race_id}
        │  FeatureLoader → CorePipeline.evaluate
        ▼
[BFF] map → PredictionBundle → HTTP 200
```

### Observed for `2026-08-01-01-02`

| Step | Expected | Observed | Pass? |
|---|---|---|---|
| 1. Catalog 掲載 | published | `/api/races?date=2026-08-01` に存在・`status=published`・`numeric_race_id=202604020302` | YES |
| 2. 生成ジョブ開始（202 後） | ページ閲覧で enqueue | **enqueue 無し**（BFF/PI とも read-only） | N/A（設計上無い） |
| 3. Queue 投入 | キューあり | **Prediction Queue は存在しない** | — |
| 4. Worker 起動 | queue worker | **race_refresh oneshot のみ**（日付は default=today） | NO for Aug1 |
| 5. Prediction 生成 | CE on features | features 無し → `prediction_available=false` | NO |
| 6. Prediction 保存 | Ready Bundle / cache | 保存対象なし（candidates 無し） | NO |
| 7. 202→200 | Ready | 継続 202 `pi_prediction_unavailable_pending` | NO |

### Live API evidence

```json
GET /api/predictions/2026-08-01-01-02
→ HTTP 202
{
  "error": {"code":"PREDICTION_PENDING","details":{
    "race_id":"2026-08-01-01-02",
    "numeric_race_id":"202604020302",
    "reason":"pi_prediction_unavailable_pending"
  }},
  "meta": {
    "prediction_status":"pending",
    "engine_source":"pi_catalog_projection",
    "fallback_reason":"pi_prediction_unavailable_pending",
    "model_version":null,
    "inference_generated_at":null
  }
}
```

Race cards:

```text
2026-08-01-01-02 prediction.status = "missing"  (全 Aug1 カード missing)
```

Coverage:

```text
2026-08-01 total=0 real_ai=0 mock=0 coverage=0
2026-07-29 total=0 …（当日も features/coverage ゼロ）
2026-07-26 total=4 …（過去日。同日 race は HTTP 200 Ready 確認済み）
```

---

## 2. Queue Status

| Item | Status |
|---|---|
| Dedicated Prediction Queue | **なし** |
| Job enqueue on HTTP 202 | **なし** |
| Async generate-then-store worker | **なし** |
| Effective “queue” | `expect-pi-race-refresh.timer` の日付単位 oneshot |

**結論:** PENDING 表示後にジョブが開始されないのはバグというより **現行設計**。Ready 化は features がディスクに載った後の次回 GET に依存する。

---

## 3. Worker Status

| Unit | Role | Observed via Ops |
|---|---|---|
| `expect-pi-race-refresh.timer` | 15分毎・features 生成 | EC2 直接 journal は本監査から未取得。**挙動証拠:** Aug1 features 未反映 / 当日も PENDING |
| `expect-pi-keibanet-api` | PI API（Healthy） | monitor-live: PI Healthy |
| `expect-result-automation.timer` | 結果同期（予想生成ではない） | **unhealthy** FAILED runs 7/27–7/29 |
| `expect-collect-weekday.timer` | 収集 | カタログは Aug1 あり → collect 側は動いている可能性高 |
| `expect-v8-research-scheduler.timer` | Research week | idle / next_run 過去・予想生成非関与 |
| Cloudflare Pages BFF | 読取のみ | degraded（RA 起因）だが PI ok |

monitor-live 抜粋:

- Pages: degraded  
- PI: Healthy  
- AI: Healthy  
- EC2: **No Data**  
- ResultAutomation: Failed  
- ResearchScheduler: Healthy/idle  

---

## 4. Prediction Status

| race_id | HTTP | Meaning |
|---|---|---|
| `2026-08-01-01-02` | **202** | Catalog のみ。CE 不可 |
| `2026-08-01-*` (cards) | prediction=`missing` | 全日 missing |
| `2026-07-26-01-11` | **200** | Ready（対照） |
| `2026-07-29-01-01` | **202** | 当日も Ready 化失敗 |

PI 内部（コード正本）:

```text
FeatureLoader → None
  → error: features_unavailable
  → BFF: PREDICTION_PENDING
```

---

## 5. Is this race_id a generation target?

| Layer | Target? |
|---|---|
| Race catalog / published shutuba | **YES**（published, numeric_id 解決済） |
| race_refresh default date (= today 2026-07-29) | **NO**（未来日 `2026-08-01`） |
| Manual `prod_race_refresh.py --date 2026-08-01` | **YES（可能）** — 未実施の証拠 |
| On-demand CE without features | **不可** |

---

## 6. Result Automation / Scheduler / Cron（切り分け）

| System | Relation to Ready | Status | Notes |
|---|---|---|---|
| Result Automation | **非関与**（着後評価・精算） | unhealthy FAILED | Ready 非遷移の直接原因ではない |
| Research Scheduler | Research/approval | idle | 非関与 |
| Public ops CLOSED (Research Week〜8/1 0:00) | 公開ゲート | CLOSED | ADMIN API は到達。features 生成を代替しない |
| race_refresh cron/timer | **本命** | 要 EC2 確認 | default date=today → Aug1 非対象 |

---

## 7. Root Cause

### Primary

**`2026-08-01` の Feature CSV が未生成のため、PI `CorePipeline.evaluate` が失敗し、BFF が永続的に 202 PENDING を返す。**

根拠:

1. Catalog はあるが race-cards `prediction.status=missing`  
2. coverage `2026-08-01` 全ゼロ  
3. `race_refresh` は default **today** のみ自動実行 → 監査日は 7/29、対象日は 8/1  
4. HTTP 202 応答後に enqueue する仕組みが無い  

### Secondary（同日兆候）

**当日 `2026-07-29` も PENDING** → race_refresh / FeatureLoader 本番健全性の追加疑い（timer 停止・window 外誤認・horse_number ゲート・データパス不整合等）。EC2 journal 確認が必要。

### Non-causes（除外）

| Suspect | Why excluded |
|---|---|
| UI4 | Pending 表示は正しい |
| Contract Guard | Ready Bundle 未到達 |
| Result Automation FAILED | 結果パイプライン。予想生成ではない |
| Research Scheduler | 予想生成ではない |

---

## 8. Recovery Plan

### Immediate（当該 race を Ready にする）

1. EC2 で確認:
   ```bash
   systemctl status expect-pi-race-refresh.timer expect-pi-race-refresh.service
   journalctl -u expect-pi-race-refresh.service -n 200 --no-pager
   ls -la /opt/expect-ai/platform/data/demo_daily_outputs/2026-08-01/ || true
   ls -la /opt/expect-ai/platform/data/var/race_refresh/2026-08-01/ || true
   ```
2. Features 強制生成:
   ```bash
   cd /home/ubuntu/KEIBA-Single-AI/services/pi-keibanet-api
   python3 scripts/prod_race_refresh.py --date 2026-08-01 --force
   ```
3. レポート確認: `features_generated` / `feature_ready_race_ids` に `2026-08-01-01-02` が含まれること  
4. 検証:
   ```bash
   curl -sS "$PI/v1/predictions/2026-08-01-01-02" | jq '.prediction_available,.error'
   curl -sS -H "Authorization: Bearer $ADMIN" \
     https://expect-keiba.com/api/predictions/2026-08-01-01-02
   ```
   期待: `prediction_available=true` / HTTP **200**

### Stabilization（当日も PENDING の二次調査）

1. `prod_race_refresh.py --date 2026-07-29 --force` の error / horse_number skip を確認  
2. RA FAILED は別インシデントとして切り分け（予想 Ready とは分離してチケット化）  
3. 必要なら Research Week 明け（8/1 0:00）後の通常 race-day 運用で timer が当日を拾うことを確認

### Optional product follow-up（本監査スコープ外）

- 「未来開催日の published レースを refresh 対象に含める」仕様変更  
- または「PENDING 時に refresh enqueue」— **現行禁止領域（Prediction/Core）に触れるため別 Decision**

---

## Decision

| Item | Value |
|---|---|
| Action Type | Pipeline Audit |
| Implementation Required | No（コード変更不要・Ops 復旧） |
| Deployment Required | No |
| Configuration Required | Maybe（timer enable / date force） |
| Production Required | Yes — EC2 上で refresh 実行・確認 |
| Rollback Required | No |
| Risk | Low（手動 refresh）/ Medium（当日 refresh 全体障害の場合） |
| Expected Next Action | EC2 で `--date 2026-08-01 --force` を実行し Ready を確認 |

---

## Corroboration（codebase explore）

[Explore prediction pending pipeline](87b71f7b-f82c-4f4f-a5a2-2100530ee51a) の結論と一致:

| Point | Detail |
|---|---|
| Pending の正本 | BFF `pendingPredictionResult` が `fallback_reason=pi_prediction_unavailable_pending` を固定付与（PI はその文字列を返さない） |
| PI 未準備形 | `features_unavailable` / `prediction_runtime_unavailable` → BFF が 202 に包む |
| Collector `prediction_ready` | STATIC_CORE 充足フラグであり **HTTP 200 PredictionBundle とは別概念** |
| Feature ゲート | horse_number integrity 未達だと Feature CSV を書かない（追加確認ポイント） |
| 3分 SLA 文書 | **存在しない**（近いのは refresh 15分・UI retry・可用性アラート） |
| Ops API | race-refresh キュー深さ / race_id 単位 pending 一覧の専用 API は無い |

---

## Artifacts

- 本ファイル: `docs/research/v109-gen1-pending-pipeline-audit.md`
- 関連正本: `docs/ops/v2-operations-race-refresh-addendum.md`
- Code: `services/pi-keibanet-api/pi_keibanet/service.py` (`get_prediction`)  
- Code: `services/pi-keibanet-api/scripts/prod_race_refresh.py`  
- Code: `functions/_lib/adapters/predictionAdapter.js` (202 PENDING)
