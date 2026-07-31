# Version 3 — A-05 Shadow Evaluation Report（Phase S1）

**Date:** 2026-07-24  
**Evaluation ID:** `v3-a05-shadow-evaluation/s1-1.0`  
**Phase:** **S1 Stability**  
**Harness:** `research/v3_lab/shadow_evaluation_s1.py`  
**Corpus:** real operational labeled **285R** · **57 race days**（≥14日）  
**S1 Decision:** **PASS**  
**Production Readiness Recommendation:** **HOLD**  
**PRR:** HOLD 継続  
**Artifacts:** `research/v3_lab/baselines/a05_shadow_evaluation_s1/`

---

## 1. 目的

実運用入力に対する A-05 Shadow の安定性を検証する。  
Production Decision は変更しない。Purchase は Control のみ（Shadow 非購入）。

---

## 2. 実施条件

| 項目 | 内容 |
|------|------|
| Phase | S1 |
| 期間ゲート | **57 race days ≥ 14** かつ labeled N=285 |
| Control | Production Decision 相当（Flag OFF identity）· 仮想 Purchase のみ集計 |
| Shadow | fail-open · 非購入 · 並列評価 |
| 安定性パネル | Full 285R + **直近 14 race days**（70R） |
| アルゴリズム / Flag 既定 / Production 配線 | **未変更** |

---

## 3. Decision

| 項目 | 結果 |
|------|------|
| **S1 Decision** | **PASS** |
| Hard Gate（Full） | PASS |
| 直近14日 wr1/churn | **0 / 0**（安全） |
| Acceptance（Full） | PASS |
| 例外件数 | **0** |
| **Production Readiness Recommendation** | **HOLD** |

HOLD 理由: S1 PASS でも PRR HOLD · API 未配線 · Flag ON / Rollout 未承認。

---

## 4. Hard Gate（Full 285R）

| 条件 | 結果 |
|------|------|
| worsened_winner_rank1 = 0 | **0** ✓ |
| ΔHit > 0 | **+7** ✓ |
| churn_hit = 0 | **0** ✓ |
| Acceptance Criteria | **PASS** ✓ |

### 直近 14 race days（安定性）

| 指標 | 値 |
|------|-----|
| n / days | 70 / 14 |
| ΔHit | **+2** |
| worsened_winner_rank1 | **0** |
| churn_hit | **0** |

---

## 5. Metric Summary

### Full operational window

| 指標 | Control | Shadow | Δ |
|------|---------|--------|---|
| Hit | **59** | **66** | **+7** |
| Virtual Purchase | 59 | 66 | +7 |
| Virtual ROI | 0.0246 | **0.5235** | +0.4989 |
| improved | — | **7** | — |
| worsened | — | **0** | — |
| worsened_winner_rank1 | — | **0** | — |
| churn_hit | — | **0** | — |
| 例外 | — | **0** | — |

### Last 14 race days

| 指標 | Control | Shadow | Δ |
|------|---------|--------|---|
| Hit | **9** | **11** | **+2** |
| Virtual Purchase | 9 | 11 | +2 |
| Virtual ROI | -0.6343 | -0.0129 | +0.6214 |
| improved / worsened | — | **2 / 0** | — |
| worsened_winner_rank1 | — | **0** | — |
| churn_hit | — | **0** | — |
| 例外 | — | **0** | — |

詳細: `baselines/a05_shadow_evaluation_s1/shadow_s1_metric_summary.json`

---

## 6. データ品質

| 項目 | 値 |
|------|-----|
| unique race days | **57**（2024-01-06 … 2026-06-28） |
| quality ok / degraded | 268 / 17 |
| degraded issue | odds_le_1_present ×17 |
| missing winner | 0 |
| H4 calendar ≥14 | PASS |
| H4 N≥285 | PASS |

---

## 7. 異常ログ

例外 **0** · error_rate **0.0** · 異常 race なし。

---

## 8. 提出物索引

| 提出物 | パス |
|--------|------|
| S1 Shadow Report | 本文書 |
| Metric Summary | JSON artifact |
| Acceptance Result | [`v3-a05-shadow-s1-acceptance-result.md`](./v3-a05-shadow-s1-acceptance-result.md) |
| Risk Summary | [`v3-a05-shadow-s1-risk-summary.md`](./v3-a05-shadow-s1-risk-summary.md) |
| Production Readiness Recommendation | [`v3-a05-shadow-s1-production-readiness-recommendation.md`](./v3-a05-shadow-s1-production-readiness-recommendation.md) |

---

## 9. 停止

**S1 Shadow Evaluation 完了。**  
Feature Flag ON · Production Rollout · Phase 3 には着手しない。
