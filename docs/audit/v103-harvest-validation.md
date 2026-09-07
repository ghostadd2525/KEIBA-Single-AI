# Version10.3 Audit — Horse Intelligence Harvest Validation

**Date:** 2026-07-27 (JST)  
**Type:** Production harvest proof（EC2 実測）  
**前置:** `docs/research/v103-horse-intelligence-harvest.md` · `docs/audit/v101-data-source-feasibility.md`

---

## 0. Verdict

| 条件 | 要求 | 実測 | 判定 |
|------|------|------|------|
| sire Coverage | ≥95% | **100% (619/619)** | **PASS** |
| damsire Coverage | ≥95% | **100% (619/619)** | **PASS** |
| breeder Coverage | ≥95% | **100% (619/619)** | **PASS** |
| owner Coverage | ≥95% | **100% (619/619)** | **PASS** |
| sale_price | 欠損許容 | **32.0%**（未掲載 `-`） | **PASS（許容）** |
| oikiri_time | ≥95% 目標 | **17.1% (106/619)** | **FAIL vs 95% / SOURCE_LIMITED** |
| oikiri_rating | ≥95% 目標 | **17.1% (106/619)** | **FAIL vs 95% / SOURCE_LIMITED** |
| Anti-Leak violations persisted | 0 意図 | 拒否フィールドは value 非保存 | **PASS** |
| Prediction Bundle / PE / CE / AI | 未変更 | 未変更 | **PASS** |
| Analyzer 再実行 | 必須 | `v103-feature-ranking.csv` 更新済 | **PASS** |

**総合:** 静的 Horse Intelligence の Coverage 拡張は **成立**。  
調教 Feature は Collector 実装済だが、netkeiba 公開済み出走馬比率が低く **95% 目標は未達**（技術ブロックではなくソース公開ギャップ）。

---

## 1. Evidence

### 1.1 DB counts（EC2 `expect_ai.db`）

| 指標 | 値 |
|------|-----|
| Snapshots complete | 50 |
| Snapshots failed | 7（レガシー ID） |
| Feature cells / feature | 619（complete のみ） |
| Reharvest targets | 50 |

### 1.2 Feature fill

| feature_id | filled | total | coverage |
|------------|-------:|------:|---------:|
| sire | 619 | 619 | 1.0000 |
| damsire | 619 | 619 | 1.0000 |
| breeder | 619 | 619 | 1.0000 |
| owner | 619 | 619 | 1.0000 |
| sale_price | 198 | 619 | 0.3199 |
| oikiri_time | 106 | 619 | 0.1712 |
| oikiri_rating | 106 | 619 | 0.1712 |
| popularity / win_odds / expected_popularity / trainer | 619 | 619 | 1.0000 |

### 1.3 Smoke（単レース）

`2026-07-26-01-01` / numeric `202604020201`:

- horse_id 通過: YES（PI board）
- sire/damsire/breeder/owner: 11/11
- oikiri: 3/11（ページ上に当該出走馬の調教行が存在する頭数に一致）

### 1.4 oikiri 未達の原因分類

| 仮説 | 判定 |
|------|------|
| numeric_race_id 誤り | 否定（タイトル・出走と一致） |
| パーサが全頭を落とす | 否定（公開頭は取得可、horse_id 限定抽出） |
| プレミアム壁で全マスク | 否定（無料 HTML にタイム/評価あり） |
| **出走馬のうち調教未掲載が多い** | **採用**（Head 行が一部頭のみ） |

---

## 2. Quality 観点

| 指標 | 実装 |
|------|------|
| Coverage / Missing | `research_snapshot_features` + `quality.compute_runner_feature_metrics`（全 PHASE1_FEATURES） |
| Latency | `research_source_events.latency_ms` / snapshot `source_latency_ms` |
| Freshness | source `observed_at` vs `prediction_created_at` |
| Consistency | 既存（人気 vs オッズ順位）維持 |
| Anti-Leak | `accept_observation` で違反 value を破棄 |

---

## 3. Analyzer Ranking（再計測）

CSV: `docs/research/v103-feature-ranking.csv`

要約:

1. popularity / win_odds / expected_popularity — PROMISING（Soft→Strict 20%）
2. oikiri_* — Coverage 低・Tie eligible ほぼ無し
3. trainer / sire / damsire / breeder / owner — Coverage 100%、カテゴリカル N/A

Prediction 順位は **Shadow 評価のみ**（変更なし）。

---

## 4. 【Decision】

```
【Production Diagnosis】
Server: Harvest PASS for static horse features; oikiri SOURCE_LIMITED
Client: N/A（本フェーズは Research sidecar / ドキュメント成果物）

【Server Diagnosis】
Status: PARTIAL
Evidence: sire/damsire/breeder/owner 100%; oikiri 17.1%

【Client Diagnosis】
Status: N/A
Client Evidence: no UI surface in V10.3 harvest scope

Diff Summary: Research Collector + Snapshot features expanded; Prediction Bundle untouched
Root Cause: # Both — static harvest success; oikiri gap is upstream publish coverage
Expected Action: Accept static PASS; track oikiri as known gap or timed pre-race harvest

【Decision】
Action Type: Harvest Validation
Implementation Required: No further for static targets
Deployment Required: Already on EC2
Configuration Required: No
Production Required: No (Prediction locked)
Rollback Required: No
Risk: Low
Expected Next Action: Tie Resolver design using high-coverage features; optional oikiri timing research
```
