# Version 3 — A-05 Shadow Evaluation Report（S0 Dry-run）

**Date:** 2026-07-24  
**Evaluation ID:** `v3-a05-shadow-evaluation/s0-1.0`  
**Phase:** **S0 Dry-run**  
**Runtime:** `research/v3_lab/shadow` + `shadow_evaluation.py`  
**Corpus:** real labeled_test **285R**（運用相当入力 · Offline と同系）  
**Decision:** **PASS**  
**PRR:** HOLD 継続  
**Artifacts:** `research/v3_lab/baselines/a05_shadow_evaluation/`

---

## 1. 目的

Shadow Runtime を用い、A-05 が実運用相当入力でも Offline Gate / Validation と同等性能を維持するか検証する。

本番 Decision / Purchase / Prediction API は変更しない。  
Shadow は fail-open · 非購入 · 並列評価のみ。

---

## 2. 実施条件

| 項目 | 内容 |
|------|------|
| Phase | S0 Dry-run |
| 件数ゲート | Acceptance H4: labeled **N=285 ≥ 285**（カレンダー 3–7 日不足時は最低件数で継続） |
| Control | Production Decision 相当 = Lab Flag OFF identity top-1 |
| Shadow | A-05（runtime 一時 ON → 終了時 Flag 既定復元） |
| 購入 | **実行なし**（仮想 Purchase/ROI のみ） |

---

## 3. Decision

| 項目 | 結果 |
|------|------|
| **Decision** | **PASS** |
| Hard Gate | PASS |
| Acceptance | PASS |
| Offline Validation パリティ | **一致**（59→66 · wr1=0 · churn=0 · +7） |
| Production wiring | **False** |
| Flag 既定 | **OFF 維持** |

---

## 4. Hard Gate

| 条件 | 結果 |
|------|------|
| worsened_winner_rank1 = 0 | **0** ✓ |
| ΔHit > 0 | **+7** ✓ |
| churn_hit = 0 | **0** ✓ |
| Acceptance Criteria | **PASS** ✓ |

---

## 5. Metric Summary

| 指標 | Control | Shadow | Δ |
|------|---------|--------|---|
| Hit | **59** | **66** | **+7** |
| Virtual Purchase | 59 | 66 | +7 |
| Virtual ROI | 0.0246 | **0.5235** | +0.4989 |
| improved | — | **7** | — |
| worsened | — | **0** | — |
| worsened_winner_rank1 | — | **0** | — |
| churn_hit | — | **0** | — |
| pick_churn | — | 46 | — |
| promote_rate | — | 0.161 | — |
| favsafe_block_rate | — | 0.702 | — |
| shadow_error_n | — | **0** | — |
| elapsed_ms p95 | — | 0.317 | — |

詳細: `baselines/a05_shadow_evaluation/shadow_metric_summary.json`

---

## 6. Acceptance Result

| Check | 結果 |
|-------|------|
| H1–H9 + purchase_not_executed | **すべて true** |
| Soft S1–S3 | **すべて true** |
| Decision | **PASS** |

詳細: [`v3-a05-shadow-acceptance-result.md`](./v3-a05-shadow-acceptance-result.md) · JSON artifact

---

## 7. 異常ログ / 例外

| 項目 | 結果 |
|------|------|
| 例外件数 | **0** |
| shadow_error_rate | **0.0** |
| 異常 race_id | なし |

JSONL: `baselines/a05_shadow_evaluation/logs/a05_shadow_*.jsonl`

---

## 8. Risk Summary

要約: [`v3-a05-shadow-risk-summary.md`](./v3-a05-shadow-risk-summary.md)

- 本番 Decision / 購入 / Flag 既定は未変更  
- Offline Validation と数値パリティ  
- 残リスク: ライブ複数日カレンダー未実施 · API 未配線 · 仮想 ROI のみ  

---

## 9. 変更範囲

| 追加 | Shadow Evaluation harness · artifacts · 文書 |
|------|------|
| **未変更** | アルゴリズム · Flag 既定 · Production · API · UI · Ops |

---

## 10. 停止

**Shadow Evaluation 完了。Decision = PASS。**  
Production Rollout · Feature Flag ON · PRR Close · Phase 3 には着手しない。
