# Collector RC-1 — Release Review

**Date:** 2026-07-21  
**Subject:** Weekday Collector（C-0 … C-8）  
**Scope:** レビューのみ（コード変更なし）  
**Verdict:** **RC-1 PASS** / **Version 1.0 HOLD** / **Go-Live HOLD**

---

## 0. 総合判定

| 判定対象 | 結果 | 理由 |
|----------|------|------|
| **RC-1** | **PASS** | 責務分離・Contract・状態機械・Budget/Retry/分散・Manifest/Gate/OPS が揃い、Controlled 検証は C-7/C-8 で PASS。循環依存なし。Prediction 非破壊を維持。 |
| **Version 1.0（正式リリース）** | **HOLD** | Real KeibaNet 実接続検証が未完了（唯一の Must 級ブロッカー）。 |
| **Go-Live** | **HOLD** | 同上。接続条件を満たせば Go-Live 可（§4）。 |

RC-1 は「候補としてレビュー可能・品質ゲート通過」を意味する。本番宣言（1.0 / Go-Live）とは分離する。

---

## 1. アーキテクチャレビュー

### 1.1 責務分離

| レイヤ | 責務 | 評価 |
|--------|------|------|
| Contract | Availability / Dynamic / Retry / Weekday / Artifact 正本 | 良 |
| Repository | collect_* 永続化・idempotency・遷移 | 良 |
| Planner | カレンダー SoT → targets | 良 |
| Queue | Availability + 平日分散 enqueue | 良 |
| Scheduler | dequeue / finish / DYNAMIC refresh（Prediction 軸は触らない） | 良 |
| Collector | 取得 → Raw → Validator → 状態（retry_after 付与含む） | 良 |
| Retry | retry_after 到達後 PENDING | 良 |
| Budget | 日次 SoT（Client と共有） | 良 |
| Friday Gate | prediction_ready / complete_ready 正本 | 良 |
| OPS Monitor | Prediction 軸 + DYNAMIC 軸の分類 | 良 |
| Manifest | 週次スナップショット（書き手責任分離） | 良 |
| ETL Bridge | collect 外（`etl/from_raw.py`）。Collector は ETL を知らない | 良 |

**所見:** Prediction / FeatureLoader / LightGBM を collect が import しない境界は維持されている。

### 1.2 循環依存

**問題なし。** 依存は概ね DAG（Planner/Scheduler/Gate → Repository/Contracts/Budget）。サブモジュールは相対 import、`__init__` 経由の循環もない。

### 1.3 Contract

完成度は RC として十分。

- Availability（WEEKDAY / AFTER_DRAW / RACE_DAY）
- STATIC（race_meta / entries_core）+ DYNAMIC（odds / track）
- Retry Policy / Weekday Distribution / Dynamic refresh
- Manifest `expect-collect-week-manifest/1.1`

未実装（設計上の将来）: P2/P3 artifact Contract（意図的スコープ外）。

### 1.4 Repository

- Migration `007` / `008`（idempotency UNIQUE、dequeue index）
- kind-aware 遷移、`retry_after`、job↔artifact link

### 1.5 Scheduler

- Budget 下 dequeue、Manifest collect/budget/dynamic_* 更新
- Prediction Ready を確定しない（Gate 正本）— 設計どおり

### 1.6 Availability

- 未取得 = ジョブ未生成（SKIPPED 乱用なし）
- ENQUEUEABLE と契約レジストリが一致

### 1.7 Friday Gate

- Prediction Ready = prediction_required artifact 全 READY
- Complete Ready = Contract 全 artifact READY
- `dynamic_*` を破壊しない

### 1.8 OPS Monitor

- Prediction: NOT_READY / PREDICTION_READY / COMPLETE_READY
- Dynamic: STATIC_READY / DYNAMIC_REFRESHING / DYNAMIC_READY
- 二軸独立 — 良

---

## 2. Go-Live Checklist

| # | 項目 | 状態 | 根拠 |
|---|------|------|------|
| 1 | Contract 完成 | ✅ | availability/dynamic/retry/weekday/artifact + manifest 1.1 |
| 2 | Migration 完成 | ✅ | 007_collect_c0 / 008_contract_1_1 |
| 3 | Repository 完成 | ✅ | runs/targets/jobs/artifacts + SM |
| 4 | Planner | ✅ | カレンダー SoT → targets |
| 5 | Queue | ✅ | Availability + 分散 enqueue |
| 6 | Scheduler | ✅ | dequeue / finish / dynamic refresh |
| 7 | Budget | ✅ | CollectBudget SoT（C-8） |
| 8 | Retry | ✅ | retry_after 自動 + CollectRetry（C-8） |
| 9 | Availability | ✅ | C-4 |
| 10 | Static | ✅ | race_meta / entries_core（C-1/C-4） |
| 11 | Dynamic | ✅ | odds / track + STALE（C-6） |
| 12 | Manifest | ✅ | 1.1 + 責務分離（C-5/C-6） |
| 13 | Friday Gate | ✅ | C-5 |
| 14 | OPS Monitor | ✅ | C-5/C-6 |
| 15 | ETL Bridge | ✅ | EtlFromRaw（C-3） |
| 16 | Prediction 非破壊 | ✅ | C-3/C-7 mock 検証 |

**Checklist 内訳:** 16/16 実装・Controlled 検証済み。  
**Go-Live 追加ゲート（Checklist 外）:** Real KeibaNet — ❌ 未実施。

---

## 3. Known Limitation

### Must（1.0 / Go-Live 前）

1. **Real KeibaNet 実接続検証**（成功/失敗/429/Timeout/Rate Limit、4 artifact）
2. 週末規模での **実測レート制限**（daily_limit 150 前提の実トラフィック）

### Should

1. 本番 OPS ダッシュボードへの Manifest / 二軸状態の常時表示
2. real AI engine での Prediction 不変の再確認（mock 以外）
3. `Retry-After` ヘッダ尊重（429）
4. systemd / 本番 Timer 配線（設計にあるが意図的未実装）

### Nice to Have

1. P2 / P3 artifact 取得
2. Raw Store 世代・容量管理ポリシー自動化
3. 取得レイテンシ週次ベースライン
4. C-7 結果の自動 JSON → OPS 連携

---

## 4. Real KeibaNet → Go-Live 条件

以下を **すべて満たしたとき** Go-Live（および Version 1.0 宣言）可。

| # | 条件 |
|---|------|
| G1 | `EXPECT_KEIBANET_BASE_URL` を本番相当に設定 |
| G2 | `race_meta` / `entries_core` / `odds` / `track` の実取得成功を各 1 件以上確認 |
| G3 | HTTP 429 / 5xx / Timeout が FAILED + retry_after → CollectRetry で PENDING まで確認 |
| G4 | 日次 Budget（Manifest = Scheduler = Client）が実運用値で一致 |
| G5 | 1 週分（または同等規模）の平日分散 enqueue が実カレンダーで破綻しない |
| G6 | Collector 経由 ETL 後も Prediction シグネチャが不変（推奨: real engine） |
| G7 | OPS が Prediction Ready と DYNAMIC 軸を誤表示しない（手動確認で可） |

**満たさない場合:** Go-Live / 1.0 は継続 HOLD。RC-1 ステータスは維持してよい。

---

## 5. Version 判定

| 質問 | 回答 |
|------|------|
| Collector **Version 1.0** として正式リリース可能か？ | **不可（HOLD）** |
| 理由 | Real KeibaNet Must 未クリア。Controlled 品質は 1.0 候補レベル。 |
| 推奨タグ | `collector-rc-1`（候補）。`collector-1.0.0` は G1–G7 完了後。 |

---

## 6. RC-1 判定（最終）

### **RC-1 PASS**

**理由**

1. C-0〜C-8 の契約・実装・Controlled 検証が揃っている  
2. アーキテクチャ上の循環依存・責務混線・Prediction 汚染がない  
3. Go-Live Checklist（実装項目）はすべて ✅  
4. 残制限は外部依存（実 KeibaNet）に限定され、Known Limitation として明示可能  

**同時宣言**

- **Version 1.0 HOLD**
- **Go-Live HOLD**（§4 条件待ち）

---

## 関連

- [`collector-c7-production-validation.md`](./collector-c7-production-validation.md)
- [`collector-c8-production-readiness.md`](./collector-c8-production-readiness.md)
- [`collector-weekday-dispersion.md`](./collector-weekday-dispersion.md)
