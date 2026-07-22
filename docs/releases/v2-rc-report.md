# Version 2 — Release Candidate (RC) Report

**Date:** 2026-07-22  
**Status:** **Release Candidate**  
**Baseline:** Version 1.1 本番（PI Prediction + Race Catalog）  
**サブプロジェクト:** Accuracy · UI Enhancement · Explainability · Operations — **すべて正式クローズ**

| 提出物 | パス |
|--------|------|
| 本 RC Report | `docs/releases/v2-rc-report.md` |
| Architecture | `docs/releases/v2-architecture.md` |
| ChangeLog | `docs/releases/v2-changelog.md` |
| Known Limitations | `docs/releases/v2-known-limitations.md` |
| Release Checklist | `docs/releases/v2-release-checklist.md` |

**サブシステム Final Report:**

| 領域 | Final Report |
|------|--------------|
| Accuracy | `docs/releases/v2-accuracy-final-report.md` |
| UI Enhancement | `docs/releases/v2-ui-enhancement-final-report.md` |
| Explainability | `docs/releases/v2-explainability-final-report.md` |
| Operations | `docs/releases/v2-operations-final-report.md` |

---

## 1. 概要

Version 2 は、v1.1（PI 本番 Prediction）を壊さず、次の 4 軸を **Feature Flag 付き additive** で積み上げた Release Candidate である。

| 軸 | 目的 | RC 判定 |
|----|------|---------|
| **Accuracy** | Pool/Entry 改善（PE-V2-A）で Hit 216→**218** | 検証終了・採用確定 |
| **UI Enhancement** | RaceCardSummary 一覧・検索・お気に入り | Phase 1–5 クローズ |
| **Explainability** | explain 2.1 · Product stages · Kaoba | Phase 1–3 クローズ |
| **Operations** | PI Probe · Metrics · Dashboard · Slack | Phase 1–3 クローズ |

**互換性の原則:** 全 Web/Core Flag 既定 **OFF** ≡ **Version 1.1 恒等**。本番切替は Flag 段階 ON で行う。

**契約非破壊:** PredictionBundle 2.0 / RaceCardSummary / PI `/v1/races`·`/v1/predictions` の破壊的変更なし（explain 等は additive）。

---

## 2. 採用機能

### 2.1 Accuracy（AI Core）

| 項目 | 内容 |
|------|------|
| **採用** | **PE-V2-A**（`WIN5_POOL_ENTRY_V2_ENABLED=ON`） |
| Corpus | 285R labeled_test |
| 成果 | Hit **218**（Phase255 Control 216 から +2） |
| 副作用 | Purchase −2（記録済・Hard Gate 外）、churn_hit=0 |

最終スタック:

```text
Phase255 Final（V1.1 Baseline）
  + PE-V2-A ON
  + RP / CE OFF
```

### 2.2 UI Enhancement（BFF + Web）

| Phase | 機能 | Flag |
|------:|------|------|
| 1 | `GET /api/race-cards` | `v2_race_cards` |
| 2 | URL 同期 `races.html?date=` | `v2_race_list_ui` |
| 3 | `raceCardSummaryHtml` | `v2_race_list_ui` |
| 4 | 検索（本命 / 信頼度 / band） | `v2_race_list_ui` |
| 5 | お気に入り（◎ + 信頼度%） | `v2_race_list_ui` |

### 2.3 Explainability（Core → PI → BFF → Web → Kaoba）

| 機能 | 内容 |
|------|------|
| explain 2.1 | `decision_key` · `confidence_reason` · `decision_trace` |
| Product | Pool / Entry / RePick（journal 経由） |
| Kaoba | `explain_pick`（`v2_explain` context） |

### 2.4 Operations（EC2 + BFF + Ops UI）

| 機能 | 内容 |
|------|------|
| PI Probe | PI-H01/H02/H03 · BFF `pi_health` |
| Metrics | `expect-ops-metrics/1.0`（MET-J02/J04） |
| Dashboard | `GET /api/ops/dashboard` · `ops.html` 拡張 |
| Alert / Slack | ALT-E* · SLK-N01/N02/N03 · Runbook |

---

## 3. 採用されなかった実験

| ID | 領域 | 理由 | Flag |
|----|------|------|------|
| **RP-V2-A** | Accuracy | Hit Δ0 · Winner Rescue 0/11 · Trigger 不足 | `WIN5_REPICK_V2_ENABLED` **OFF** |
| **CE-V2-A** | Accuracy | Hit −2 · churn=2 · Softmax 温度が既得 Hit を崩す | `WIN5_CE_V2_ENABLED` **OFF** |
| **CE-V2-C** | Accuracy | V2 検証終了のため **未実施**（V3 候補） | — |
| **PE-V2-B/C** | Accuracy | V2 終了のため **未実施**（任意持ち越し） | — |
| **RO-V2** | Accuracy | 設計のみ · **未実装**（V3 新 Trigger 候補） | — |
| **本番 Loki 接続** | Operations | Promtail レシピのみ（prepared） | — |
| **CF Analytics API 自動化** | Operations | 設計・後続（非ブロッカー） | — |
| **SLO Burn Dashboard** | Operations | 設計 Phase 4 · 未実装 | — |

---

## 4. Feature Flag 一覧

### 4.1 Accuracy / Core（環境変数）

| Flag | 既定（RC） | 本番推奨（Accuracy 採用時） | 役割 |
|------|------------|-----------------------------|------|
| `WIN5_POOL_ENTRY_V2_ENABLED` | 実験時 ON 検証済 | **ON**（採用） | PE-V2-A |
| `WIN5_REPICK_V2_ENABLED` | **false** | **OFF** | RP（不採用） |
| `WIN5_CE_V2_ENABLED` | **false** | **OFF** | CE（不採用） |
| `WIN5_EXPLAIN_V2_ENABLED` | **false** | 段階 ON | Core explain_payload |

### 4.2 PI / BFF

| Flag | 既定 | 役割 |
|------|------|------|
| `EXPLAIN_V2_ENABLED` | **false** | PI/BFF explain pass-through / mapper |

### 4.3 Web（`config/beta.json` · `ui_features`）

| Flag | 既定 | 役割 |
|------|------|------|
| `v2_race_cards` | **false** | RaceCardSummary BFF |
| `v2_race_list_ui` | **false** | 一覧 HTML / 検索 / fav |
| `v2_explain` | **false** | explain UI + Kaoba context |
| `v2_ops_dashboard` | **false** | Ops Dashboard v2 セクション + `/api/ops/dashboard` |

### 4.4 既存 v1.1（参考・入場ゲート）

| Flag | 備考 |
|------|------|
| `v11_ops_dashboard` | Ops 画面入場（v2 パネルとは独立） |
| `v11_auto_maintenance` | 現行 beta で true（v1.1 運用） |
| その他 `v11_*` | v1.1 系 UI（本 RC の切替対象外） |

**RC 原則:** 上記 v2_* / Explain / PE 以外を OFF のままデプロイしても **v1.1 と同一ユーザー体験**。

---

## 5. 互換性

| 契約 / 経路 | v1.1 | v2 RC |
|-------------|------|-------|
| PredictionBundle `single-prediction-bundle/2.0` | 維持 | 維持（`explain` additive） |
| RaceCardSummary | — | 契約フィールド追加なし（表示のみ Flag） |
| PI `/v1/races` · `/v1/predictions` · `/health` | 維持 | **非変更** |
| BFF `/api/predictions` | 維持 | 維持 |
| BFF `/api/race-cards` | なし | **新規**（`v2_race_cards`） |
| BFF `/api/ops/dashboard` | なし | **新規**（`v2_ops_dashboard`） |
| `/api/health` | 維持 | additive `pi` |
| `/api/ops/monitor` | 維持 | additive metrics/alerts |
| Flag 全 OFF | — | **≡ v1.1** |

**Breaking Changes:** クライアント契約上 **なし**。

---

## 6. テストサマリー

| 領域 | 代表コマンド / 検証 | 結果 |
|------|---------------------|------|
| Accuracy | 285R AB（PE / RP / CE） | PE **PASS** · RP/CE **FAIL**（意図的不採用） |
| UI Enhancement | `favorites-v2` · `race-search` · `race-card-list-ui` | **24 PASS** |
| Explainability | Core explain · explain-v2 · e2e · kaoba | Core 6 · contract/e2e 系（横断 OK） |
| Operations | `ops-v2-phase1/2/3` · `ops-monitor` | **28 PASS** |

詳細は各 Final Report を正とする。

---

## 7. RC 判定

| 項目 | 判定 |
|------|------|
| 4 サブプロジェクト正式クローズ | **OK** |
| Flag 既定 OFF / v1.1 恒等 | **OK** |
| Prediction / RaceCardSummary / PI 契約非破壊 | **OK** |
| 提出物（Architecture / ChangeLog / Limitations / Checklist） | **本文書セット** |
| Production 切替 | **Checklist 完了後**（本 RC は切替実行を含まない） |

**Version 2 Release Candidate — ドキュメント提出完了。**
