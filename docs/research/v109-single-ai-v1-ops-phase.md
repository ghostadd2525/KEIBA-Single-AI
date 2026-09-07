# Single AI Version1 — Operations Management Phase Charter

**Effective:** 2026-07-29  
**Parent:** [`v109-single-ai-v1-development-complete.md`](./v109-single-ai-v1-development-complete.md)  
**Phase:** **OPERATIONS MANAGEMENT**（開発フェーズ終了後）

---

## Mission

Single AI Version1 を **安全に運用・監視**する。  
新機能開発は行わない。Flag は **OFF** を既定とする。

## Daily / Weekly ops

| 頻度 | 作業 |
|---|---|
| 随時 | `/api/health` · `/api/ops/monitor`（`single_detail_ops`） |
| 随時 | ADMIN: `/api/ops/single-detail`（sample / alerts） |
| 障害時 | `docs/ops/single-detail-runbook.md`（ALT-SD01..05） |
| 変更時 | Flag ON にしない（Cutover Gate まで） |

## Ownership

| 領域 | Owner |
|---|---|
| Flag / Cutover | Release Decision + Ops 承認 |
| Alerts ALT-SD* | Ops on-call |
| Race List Cache LOCK | Product（変更禁止） |
| Core / Consumer / Prediction | Frozen（V1） |

## Escalation

1. Flag OFF のまま Prediction 経路で継続（ユーザー影響最小化）
2. Runbook に従い upstream / tunnel / BFF を切り分け
3. 恒久 ON は議論しても **Gate 未充足なら実行しない**

## Exit to Cutover Gate（条件のみ · 自動遷移しない）

- Platform 正常化
- 運用承認
- Release Decision（明示 GO）

満たすまで本フェーズに留まる。
