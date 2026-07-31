# Version 3 — A-05 Shadow Acceptance Result（S0）

**Date:** 2026-07-24  
**Parent:** [`v3-a05-shadow-evaluation-report.md`](./v3-a05-shadow-evaluation-report.md)  
**Decision:** **PASS**

---

## Hard Checks

| ID | Criteria | Result |
|----|----------|--------|
| H1 | worsened_winner_rank1 = 0 | **PASS** |
| H2 | ΔHit > 0 | **PASS**（+7） |
| H3 | churn_hit = 0 | **PASS** |
| H4 | 窓 ≥14日 **or** N≥285 | **PASS**（N=285） |
| H5 | 入力一致 / リークなし | **PASS** |
| H6 | A-03 同時 ON なし | **PASS** |
| H7 | 本番 A-05 既定 OFF | **PASS** |
| H8 | Control 経路健全 | **PASS** |
| H9 | Shadow error_rate ≤ 上限 | **PASS**（0.0） |
| — | purchase_not_executed | **PASS** |

## Soft Checks

| ID | Result |
|----|--------|
| S1 improved ≥ 1 | **PASS**（7） |
| S2 promote_rate band | **PASS**（0.161 ≤ 0.25） |
| S3 ROI Shadow ≥ Control | **PASS** |

## Verdict

**hard_pass = true → Acceptance Decision = PASS**
