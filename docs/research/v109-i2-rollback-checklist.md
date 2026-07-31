# Phase I2 — Rollback Checklist

**Date:** 2026-07-29  
**原則:** 一覧キャッシュは触らない。詳細 Flag のみ戻す。

---

## Immediate Rollback（目標 < 1 分）

| Step | Action | 効果 |
|---|---|---|
| 1 | `W_CONSUMER_SINGLE_ENABLED=0` | Consumer 組立停止（503 / フォールバック前提） |
| 2 | `SITE_SINGLE_HTTP_ENABLED=0` | `/v1/site/*` 503 |
| 3 | `SINGLE_AI_HTTP_ENABLED=0` | `/v1/single/*` 503 |
| 4 | （将来 FE Flag）詳細 Single OFF | `Prediction.getWithMeta` のみ |

プロセス再起動が必要な環境では env 反映後に再起動。

## Do NOT during Rollback

| 禁止 |
|---|
| `expect_race_list_cache_v4` のクリアを必須化しない（任意・ユーザー端末） |
| `expect_pb_prefetch_v1` 仕様変更 |
| 一覧 HTML / JS の緊急改修で Single 残滓を増やす |
| Core / Prediction / Contract 変更 |

## Verify after Rollback

| Check | 期待 |
|---|---|
| 一覧表示 | Cache / 従来 Prediction・RaceCards で動作 |
| 詳細表示 | Prediction Bundle 表示 |
| `/v1/site/single` | 503 SERVICE_DISABLED または未使用 |
| エラー率 | Single 起因スパイク消失 |

## Escalation

Alert 発報 → Immediate Rollback → Cache Audit 再確認 → 原因が一覧経路なら **Single 再接続禁止** を再宣言。
