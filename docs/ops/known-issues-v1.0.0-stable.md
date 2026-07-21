# Known Issues — v1.0.0-stable

**Baseline:** `v1.0.0-stable` / `08c7986`  
**更新:** 2026-07-21（本番 GO 時点）

運用上「既知」として扱う。Hotfix 必須ではないが、Version 1.1 で優先対応するものは Backlog へ紐づける。

---

## KI-01 — `mock_fallback` が多い

| 項目 | 内容 |
|------|------|
| 症状 | `GET /api/predictions` で多数が `engine_source=mock_fallback`（GO 時点例: 195/200）。`real_ai` は少数 |
| 影響 | UI/API は 200 で応答するが、実推論比率が低い |
| 原因 | feature / market 等のデータ不足（例: `market_feature_missing`, `feature_missing`, `race_not_found`）。BFF や Flag の誤設定ではない（`provider=python`, `engine=real`） |
| 回避 | データがある開催・レースでは `real_ai` が出る。全面 mock のみなら AI/Tunnel 障害を疑う |
| 解消方針 | Version 1.1: feature/market データ充実、Collector 供給（Real は HOLD 解除後） |
| Backlog | [`backlog-v1.1.md`](./backlog-v1.1.md) — B1.1-01 |

---

## KI-02 — EC2 デプロイ後に overlay 同期が必要

| 項目 | 内容 |
|------|------|
| 症状 | `git pull` 後 `systemctl restart expect-ai` すると `ModuleNotFoundError: ai_platform.core.features.feature_loader` で起動失敗しうる |
| 影響 | AI ダウン（Pages は生きていても予想が落ちる） |
| 原因 | Prediction Core overlay（`services/win5-ai/platform/core-overlay`）が `AI_PLATFORM_ROOT` に未反映のまま、import 順の都合で overlay 自動適用前に bridge が必要になる |
| 回避 / 手順 | 毎回 **overlay 同期 → migrate → restart**（[`operations-runbook.md`](./operations-runbook.md) §2–§4） |
| 解消方針 | 1.1 で起動順序・デプロイスクリプト化を検討（コード変更は別チケット） |
| Backlog | B1.1-05（運用監視・デプロイ自動化） |

---

## KI-03 — Collector Real KeibaNet は HOLD

| 項目 | 内容 |
|------|------|
| 症状 | 本番で Real KeibaNet 常時収集は行わない |
| 影響 | 週次データ自動取得の本運用は未開始。RC-1 コードは同梱済み |
| 原因 | Real 接続検証（O-1）未完。RC-1 PASS と Go-Live は分離 |
| 回避 | Controlled / 計画ドキュメントのみ。`.env` に `EXPECT_KEIBANET_*` を入れない |
| 解消方針 | O-1 完了後、明示 GO で Version 1.1 以降に接続 |
| Backlog | B1.1-02 |
| 参照 | [`collector-rc1-release-review.md`](./collector-rc1-release-review.md) · [`collector-o1-real-keibanet-validation-plan.md`](./collector-o1-real-keibanet-validation-plan.md) |

---

## KI-04 — RePick V2 は OFF（research）

| 項目 | 内容 |
|------|------|
| 症状 | 本番予想経路に RePick V2 は効かない |
| 影響 | Hit率改善は停止中。製品挙動は baseline identity |
| 原因 | AB Exit FAIL / over-fire。Feature Flag 既定 OFF。platform に未配線 |
| 回避 | `WIN5_REPICK_V2_ENABLED` を本番に設定しない。コードは `research/repick-v2/` のみ |
| 解消方針 | research 継続可。製品 ON は Exit 全合格 + 別リリース。**1.1 の必須スコープ外** |
| Backlog | B1.1-03（research 扱い・製品化は条件付き） |

---

## その他（参考・低優先）

| ID | 内容 |
|----|------|
| KI-05 | 一時IDは1回限り。seed 追加は Pages 再デプロイが必要 |
| KI-06 | 起動ログに pandas `UserWarning`（regex）が出ることがある。致命ではない |
| KI-07 | Wrangler `pages deployment list` の Status 列は相対時刻表示。成否はプレビュー URL / 静的・API 応答で確認 |

---

## インシデント時の切り分け早見

```text
AI 起動失敗 → KI-02 overlay
予想が全て mock かつ provider が python でない → Tunnel / AI_BASE_URL
予想が mock_fallback 多いが provider=python → KI-01 データ不足（正常系の既知）
RePick っぽい挙動変化 → KI-04 Flag 誤 ON を疑う
Collector が外向き通信 → KI-03 HOLD 違反
```
