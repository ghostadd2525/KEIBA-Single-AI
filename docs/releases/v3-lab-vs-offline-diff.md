# Lab vs Offline Diff

**Status:** Analysis Complete  
**Date:** 2026-07-24

---

## 1. Stack / Flags

| Item | Lab Baseline v3 | Offline Gate Treatment | Offline Gate Control |
|------|-----------------|------------------------|----------------------|
| Representation | Baseline | Baseline | Baseline |
| Admission | A-03 ON | A-03 ON | OFF |
| Selection | A-04 ON | A-04 ON | OFF |
| Evaluation | A-01 ON | A-01 ON | OFF |
| Purchase | Baseline | Baseline | Baseline |
| Flag defaults in code | OFF | harness ON | harness OFF |
| Production wiring | None | None | None |

**差分なし（設定意図）:** スタック定義・Flag 配線は一致。差は **入力コーパス** と **その上での発火頻度**。

---

## 2. Corpus / Input

| Axis | Lab Accuracy (285R) | Offline Real (285R) |
|------|---------------------|---------------------|
| Source | Synthetic Accuracy layers | phase154 labeled_test + demo_daily |
| Field size mean | 8.13 | 14.6 |
| Field min–max | 8–12 | 8–18 |
| Field ≥12 | 9 (Pool only) | 246 (86%) |
| history_score mean | 0.103 | 0.736 |
| history_score range | 0.03–0.48 | 0.00–1.00 |
| winner_rank=1 rate | 76.5% | 21.1% |
| Layer structure | Hit/Eval/Boundary/Reorder/Pool/Delete | Natural race mix |

Artifacts: `divergence_input_compare.json`

---

## 3. Evaluation Conditions

| Axis | Lab | Offline Gate |
|------|-----|--------------|
| Unit | Race | Race |
| Hit definition | top-1 pick == winner | same |
| Control | flags OFF → Hit 218 | flags OFF → Hit 59 |
| Treatment | A-01+A-03+A-04 → Hit 279 | same stack → Hit 42 |
| Churn tracking | Lab internal | Control vs Treatment race diffs |
| V2 PE / purchase survival | Not used | Not used |

**Metric 定義は一致。** 数字の絶対水準差はコーパスの favorite 率差に由来。

---

## 4. Metric Definition Compare

| Metric | Lab | Offline | Match? |
|--------|-----|---------|--------|
| Hit | pick == winner | pick == winner | Yes |
| ΔHit | Treatment − Control (or vs baseline) | Treatment − Control | Yes |
| Churn | pick changed races | same | Yes |
| Improved / Worsened | Hit flip directions | same | Yes |
| V2 PE Hit 218 | purchase/pool path | — | **Different system; not comparable** |

---

## 5. Policy Fire Rates

| Policy signal | Lab (stack ON) | Offline Treatment |
|---------------|----------------|-------------------|
| A-03 promote | ~3% (Pool×9 only) | **~53% (151/285)** |
| A-04 promote (worsened) | designed on Boundary/Reorder | 3/29 worsened |
| A-04 promote (improved) | — | 1/12 improved |
| A-01 eval rewrite | Eval×28 | present where Eval path applies |

---

## 6. Outcome Diff

| Outcome | Lab | Offline |
|---------|-----|---------|
| Stack Hit | 279 | 42 |
| vs flags-OFF | +61 (218→279) | −17 (59→42) |
| Improved | designed recoveries | 12 |
| Worsened | ~0 on Hit layer | **29** (all winner_rank=1) |
| Net | large gain | large loss |

---

## 7. One-line Diff Summary

Lab は「小頭数・層別シナリオ」で A-03 を封じ A-01/A-04 だけを効かせる。  
Offline は「大頭数実レース」で A-03 が本命を破壊し、同じスタックがマイナスになる。
