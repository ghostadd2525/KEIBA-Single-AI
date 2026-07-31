# Version 3 — Accuracy Candidate Registry

**Date:** 2026-07-24  
**Registry ID:** `v3-accuracy-candidate-registry/3.0`（Phase 2 Close）  
**Prior:** `/2.0` Lab Configuration Freeze（Baseline v2）· `/1.0` Phase 1 Close  
**Artifact:** `research/v3_lab/baselines/accuracy_phase2_close/accuracy_candidate_registry_v3.json`

---

## Adopted Lab Stack

| 構成 | Hit | Status |
|------|-----|--------|
| **A-01 Evaluation + A-03 Admission + A-04 Selection** | **279** | `lab_adopted_configuration` |

---

## Roles

### Evaluation Primary — A-01

| 項目 | 値 |
|------|-----|
| Flag | `F_V3_RANK_D1_ENABLED` |
| Alone Hit | 246 |
| In stack | **Yes** |
| Validation | PASS |
| Logic | frozen |

### Admission Primary — A-03

| 項目 | 値 |
|------|-----|
| Flag | `F_V3_A03_POOL_ADMIT_ENABLED` |
| vs A-01 Stack Hit | 255 |
| In stack | **Yes** |
| Validation | PASS |
| Logic | frozen |

### Selection Primary — A-04

| 項目 | 値 |
|------|-----|
| Flag | `F_V3_A04_SEL_HISTORY_ENABLED` |
| vs Baseline v2 Hit | **279** |
| In stack | **Yes** |
| Lab | PASS |
| Validation | **PASS** |
| Logic | frozen |

### Evaluation Secondary — A-02（保持）

| 項目 | 値 |
|------|-----|
| Flag | `F_V3_RANK_D2_ENABLED` |
| Alone Hit | 242 |
| In stack | **No** |
| Status | `lab_secondary_candidate` |
| Note | D1+D2 同時 ON は禁止のまま |

---

## Decision

| 項目 | 値 |
|------|-----|
| Simultaneous D1+D2 | False |
| Delete in research scope | False |
| Production wiring | False |
| Phase 2 | **CLOSED** |
| Production Readiness | **HOLD** |
| Baseline v3 | `v3-lab-baseline-v3-a01-a03-a04` |
| Baseline v2 | 履歴として保持（公式 Accuracy スタックは v3） |
