# Phase I2 — Production Cutover Report

**Date:** 2026-07-29  
**Mode:** Gate Design + Audit only · **実装変更なし** · **Cutover 未実行**  
**Parents:** PLATFORM-V1 · A1 · I1 · UI1 · UI2 · Race List Cache Audit · C6/C7  
**Product Requirement:** Race List Cache **必須維持**

---

## Verdict

| 判定 | 内容 |
|---|---|
| **Gate Status** | **NOT READY — CUTOVER BLOCKED** |
| Race List Cache 条件 | **PASS**（維持・変更なし） |
| 一覧 Single 禁止 | **PASS** |
| 詳細 Single 切替設計 | **PARTIAL**（Flag/Timeout 設計あり · ページ配線なし） |
| Production Ops | **PARTIAL**（Flag/Rollback 文書あり · Alert/本番監視 GAP） |
| Cutover 実行 | **DO_NOT_EXECUTE** |

---

## 必須条件サマリ

| # | 条件 | Status |
|---|---|---|
| ① | Race List Cache 変更禁止 | **PASS** |
| ② | 一覧: Single/追加HTTP/追加JS/Perf劣化禁止 | **PASS**（現状維持） |
| ③ | 詳細切替設計監査 | **PARTIAL** |
| ④ | Production Readiness | **PARTIAL** |
| ⑤ | 非機能 | **PARTIAL**（測定ベースライン未本番） |

①②が Product Requirement として満たされていても、③–⑤の GAP により **本番切替は不可**。

---

## ① Race List Cache（Product Requirement）— PASS

| 項目 | 現状 | 変更 |
|---|---|---|
| `expect_race_list_cache_v4` | 使用中 | **なし** |
| `expect_pb_prefetch_v1` | 使用中 | **なし** |
| TTL | 5 分 | **なし** |
| 更新方法 | ready のみ write / localStorage | **なし** |
| HTTP経路 | Prediction / RaceCards / prefetch | **Single 非接続** |

Evidence: `v109-race-list-cache-audit.md`

**I2 硬制約:** Cutover 後も上記を変更してはならない。一覧に Single を繋いではならない。

---

## ② 一覧画面 — PASS

| 禁止 | 現状 |
|---|---|
| Single API 接続 | 未接続 |
| 追加 HTTP（A1–UI2 起因） | なし |
| 追加 JS（single.js 等） | `races.html` 未ロード |
| Performance 劣化（A1–UI2 起因） | なし |

---

## ③ 詳細画面（切替設計のみ）— PARTIAL

| 項目 | 設計上の状態 | Cutover Ready? |
|---|---|---|
| Feature Flag | `W_CONSUMER_SINGLE_ENABLED` · `SITE_SINGLE_HTTP_ENABLED` · `SINGLE_AI_HTTP_ENABLED` | Flag は存在。**FE 切替 Flag 未配線** |
| Rollback | Flag OFF → Prediction 経路（現状のまま） | 文書上 OK · **切替未実施のため実地未検証** |
| Timeout | `SITE_SINGLE_TIMEOUT_MS` default 12000 · BFF aiFetch 12s | 設計 OK |
| Error | CONSUMER_DISABLED / TIMEOUT / UNAUTHORIZED | API 層 OK |
| Version | `site-integration/single/v1` · Bundle 2.0 · `i1/1.0` | OK |
| ページ配線 | `race.html` = Prediction only | **GAP — 切替コードなし** |

**Cutover 設計原則（承認後の実装 Gate 用・本フェーズでは実装しない）:**

```text
一覧: 必ず Race List Cache / Prediction・RaceCards（Single 禁止）
詳細: Flag ON 時のみ Single → UI1 Mapper → 既存 bind
      Flag OFF / error / timeout → 既存 Prediction.getWithMeta にフォールバック
```

---

## ④ Production Readiness — PARTIAL

| 項目 | Status | メモ |
|---|---|---|
| Feature Flag 運用 | PASS（定義・既定 OFF） | 本番 ON 手順は Checklist 参照 |
| Rollback 手順 | PASS（文書） | Flag OFF 即時 |
| Monitoring | PARTIAL | `/v1/single/metrics` · `/v1/site/health` あり。本番 dashboard GAP |
| Logging | PASS | `[single-ai-http]` structured logs |
| Alert | **GAP** | 本番 alert rules 未整備（C7 継続） |
| Version 管理 | PASS | schema / api_version / PLATFORM-V1 |

---

## ⑤ 非機能 — PARTIAL

| 項目 | Status | メモ |
|---|---|---|
| 初回表示時間 | 未計測（本番） | 一覧は cache 維持で悪化しない設計 |
| HTTP回数 | 一覧: Single 追加 0 | 詳細切替後は +0〜1（設計上 Flag 時のみ） |
| Cache Hit率 | 既存仕組み維持 | 計測ダッシュボード GAP |
| Race Switching | UI2 PASS（契約） | |
| SPA遷移 | UI2 PASS（list URL state） | |
| メモリリーク | 未計測 | 切替未配線のため現状 N/A |
| 例外 | API envelope あり | FE フォールバック未配線 |

---

## Blockers（Cutover 実行前に必須）

| ID | Blocker |
|---|---|
| B-I2-1 | 詳細ページの Flag 付き配線 + Prediction フォールバック（**実装は別 Gate**） |
| B-I2-2 | 本番 Alert（Single error rate / timeout / flag snapshot） |
| B-I2-3 | 一覧に Single を絶対接続しないことの Release サインオフ（本票で要件化済） |
| B-I2-4 | Staging での詳細 Flag ON→OFF Rollback 実地 |

Non-blockers: UI1 Mapper / UI2 100% / Cache Audit PASS / Library C5–C6 PASS

---

## Recommendation

| 対象 | 推奨 |
|---|---|
| Library / HTTP / Mapper / UI Shadow | **APPROVE（維持）** |
| Race List Cache | **LOCK — 変更禁止** |
| **Production Cutover** | **BLOCK** |
| 次 Gate | Detail Flag Wiring（一覧非接触）+ Alerts → Staging cutover rehearse → 再監査 |

---

```
【Decision】
Action Type: Production Cutover Gate (Audit)
Implementation Required: No
Deployment Required: No
Production Required: No
Rollback Required: No
Risk: High if cutover forced now
Expected Next Action: BLOCK 維持。B-I2-1..4 解消後に再 Gate
```
