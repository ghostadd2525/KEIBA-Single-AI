# Version 2 — ChangeLog（Version 1.1 → Version 2）

**Date:** 2026-07-22  
**From:** Version 1.1（PI Prediction 本番移行 · `docs/releases/v1.1.md`）  
**To:** Version 2 Release Candidate  
**正本 RC:** [`v2-rc-report.md`](./v2-rc-report.md)

---

## 0. 要約

| 区分 | 内容 |
|------|------|
| **Breaking** | **なし**（クライアント契約） |
| **Additive** | explain · race-cards · ops dashboard/metrics · PE Flag |
| **既定** | 全 v2 Web/Explain Flag **OFF** ≡ v1.1 体験 |

---

## 1. Accuracy

| 変更 | v1.1 | v2 |
|------|------|-----|
| Baseline | Phase255 Final（Hit 216） | 同 Baseline 維持 |
| Pool/Entry | 既存 | **PE-V2-A 採用**（Hit **218**） |
| RePick V2 | — | RP-V2-A **不採用**（Flag OFF） |
| CE V2 | — | CE-V2-A **不採用**（Flag OFF） |
| Delete | 不変 | **不変** |

Flag: `WIN5_POOL_ENTRY_V2_ENABLED`（採用時 ON） / `WIN5_REPICK_V2_ENABLED` / `WIN5_CE_V2_ENABLED`

---

## 2. UI Enhancement

| 変更 | v1.1 | v2 |
|------|------|-----|
| レース一覧 | PredictionBundle + `raceCardHtml` | Flag ON 時 **RaceCardSummary** 一覧 |
| BFF | `/api/predictions` · `/api/races` | **+** `GET /api/race-cards` |
| URL | （既存） | `races.html?date=` 同期強化 |
| 検索 | 基本 | 本命 / 信頼度 / band（Flag ON） |
| お気に入り | 既存 localStorage | summary 行に ◎/% 投影（Flag ON） |

Flag: `v2_race_cards` · `v2_race_list_ui`（既定 false）

---

## 3. Explainability

| 変更 | v1.1 | v2 |
|------|------|-----|
| Bundle explain | 空 / 最小 | **explain 2.1**（additive） |
| decision_key / confidence_reason / trace | — | あり（Flag ON） |
| Product stages | — | Pool / Entry / RePick（journal） |
| Kaoba | 旧ルール | `explain_pick`（`v2_explain`） |

Flag: `WIN5_EXPLAIN_V2_ENABLED` · `EXPLAIN_V2_ENABLED` · `v2_explain`（既定 false）

---

## 4. Operations

| 変更 | v1.1 | v2 |
|------|------|-----|
| PI 監視 | 手動 / 間接 | **PI-H01/H02/H03** · BFF `pi_health` |
| Metrics | win5-ai ad-hoc 中心 | **expect-ops-metrics/1.0** · pi-metrics.jsonl |
| Dashboard | 簡易 ops.html | Overview / Inventory / Alerts / Runbook |
| Slack | なし〜限定 | **SLK-N01/N02/N03**（webhook 任意） |
| Health | BFF + RA | **+ additive `pi`** |
| Monitor | probes | **+ metrics/alerts/incidents** |

Flag: `v2_ops_dashboard`（既定 false）  
Docs: Runbook · 最終構成図 · Promtail example（prepared）

---

## 5. インフラ / 契約（変更なし）

| 項目 | 状態 |
|------|------|
| Tunnel ingress（races/predictions → :8081） | v1.1 継続 |
| PI API パス・レスポンス契約 | **非変更** |
| PredictionBundle 2.0 必須フィールド | **非変更** |
| RaceCardSummary JSON 契約 | **フィールド追加なし** |

---

## 6. ファイル・成果物インデックス（ドキュメント）

| 領域 | Final / 設計 |
|------|----------------|
| Accuracy | `v2-accuracy-final-report.md` · `v2-accuracy-v3-roadmap.md` |
| UI | `v2-ui-enhancement-final-report.md` · `v2-ui-enhancement-mock.md` |
| Explain | `v2-explainability-final-report.md` · `v2-explainability-design-review.md` |
| Ops | `v2-operations-final-report.md` · `v2-operations-monitoring-inventory.md` |

---

## 7. マイグレーション（運用）

1. コードデプロイ（本 ChangeLog 時点の V2 実装）  
2. **Flag はすべて OFF のまま** smoke（v1.1 恒等確認）  
3. Accuracy: EC2 で `WIN5_POOL_ENTRY_V2_ENABLED=ON`（採用構成）  
4. Web: 必要に応じ `v2_race_cards` → `v2_race_list_ui` → `v2_explain` → `v2_ops_dashboard` を段階 ON  
5. Ops: Slack webhook Secrets（任意）· PI env（Phase 1 example 参照）

詳細手順: [`v2-release-checklist.md`](./v2-release-checklist.md)
