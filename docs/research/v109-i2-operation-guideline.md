# Phase I2 — Operation Guideline

**Date:** 2026-07-29  
**Audience:** Ops / Release owner  
**Cutover Status:** **BLOCKED**（本 Guideline は準備用）

---

## 1. Traffic Topology（必須）

```text
[一覧 races.html]
  → Race List Cache (v4) / RaceCards / Prediction list+prefetch
  → Single API 禁止

[詳細 race.html]（将来 Flag ON 時のみ）
  → Single (/api/single or /v1/site) → UI1 Mapper → Bundle → 既存 bind
  → 失敗時 Prediction.getWithMeta

[Shadow / Admin]
  → /v1/single/* · /v1/ui/prediction-bundle 任意
```

## 2. Feature Flags

| Flag | Default | 用途 |
|---|---|---|
| `W_CONSUMER_SINGLE_ENABLED` | OFF | Consumer 組立 |
| `SITE_SINGLE_HTTP_ENABLED` | 環境依存 | Site HTTP |
| `SINGLE_AI_HTTP_ENABLED` | 環境依存 | A1 facade |
| （将来）FE detail Single | OFF | ページ切替 |

**Production:** 一覧関連 Flag を新設しない。詳細のみ。

## 3. Monitoring（現状と必要）

| Signal | 現状 | Cutover 前に必要 |
|---|---|---|
| `/v1/site/health` | あり | 本番 probe |
| `/v1/single/metrics` | in-process | dashboard 接続 |
| List cache hit | クライアントのみ | 任意観測 |
| Single error/timeout rate | log | **Alert** |
| Flag snapshot in logs | あり | Alert 次元に含める |

## 4. Logging

`[single-ai-http]` JSON · flags · version · race_id · latency  
一覧経路に Single ログが出たら **異常**（接続リーク）。

## 5. Version

| Layer | Version |
|---|---|
| Platform | Core Platform Version1 FROZEN |
| Site API | i1/1.0 · site-integration/single/v1 |
| UI View | PredictionBundle 2.0 |
| UI Shadow | UI2 PASS 100% |

## 6. Incident Heuristics

| 症状 | まず疑う | 対応 |
|---|---|---|
| 一覧が遅い / HTTP 増 | Single リーク | 即 Rollback + Cache Audit |
| 詳細だけ失敗 | Site/Consumer Flag | Flag OFF → Prediction |
| Bundle 形崩れ | Mapper / base_bundle | Flag OFF |
