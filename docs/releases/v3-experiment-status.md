# Version 3 — Experiment Status（Offline Gate FAIL）

**Date:** 2026-07-24  
**Status ID:** `v3-experiment-status/offline-gate`  
**Artifact:** `research/v3_lab/baselines/offline_gate/offline_gate_decision.json`

---

## Foundation

| Experiment | Status |
|------------|--------|
| P0–P5 | complete / frozen |

---

## Accuracy

| Experiment | Status | In Stack |
|------------|--------|----------|
| `v3-a01-d1-recal` | lab_primary_evaluation | Yes |
| `v3-a02-d2-rerank` | lab_secondary_candidate | No |
| `v3-a03-pool-coverage` | lab_primary_admission | Yes |
| `v3-a04-sel-history` | lab_primary_selection · Validation PASS | Yes |
| `v3-accuracy-phase2-close` | closed | Baseline v3 |
| `v3-a04-validation` | complete · PASS | — |
| `v3-production-readiness-review` | complete · **HOLD** | — |
| `v3-offline-gate` | **complete · FAIL** | — |

---

## Production Readiness

| 項目 | 状態 |
|------|------|
| Decision | **HOLD**（強化 · Offline Gate FAIL） |
| A-04 Validation | PASS |
| Offline Gate | **FAIL**（Hit 59→42 · churn 29） |
| Shadow / Mesh | **blocked** |
| Production wiring / Flag ON | **False** |
| Phase 3 | **not_started** |
