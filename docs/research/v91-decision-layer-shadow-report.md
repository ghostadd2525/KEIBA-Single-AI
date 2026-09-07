# Version91 — Decision Layer M1 Shadow Report

**Generated:** `2026-07-28T11:14:29+00:00`  
**ADR:** ADR-008 · Phase **M1-Shadow**  
**Verdict:** **PASS**  
n=285

## Architecture（固定）

- Core AI: Prediction / Ranking / Global Confidence / World Classification
- Single/Win5 AI: Decision Layer（Ticket / Pool / Explanation / Risk）
- Prediction は Dual Shadow で共通・非変更

## Feature Flags（既定）

- `W_DECISION_LAYER_ENABLED` = **False**
- `W_DECISION_TICKET` = **False**
- `W_DECISION_POOL` = **False**
- `W_DECISION_EXPLAIN` = **False**
- `W_DECISION_RISK` = **False**
- `W_DECISION_CONF_DISPLAY` = **False**

## OFF vs ON

| Metric | OFF | ON | Δ |
|---|---:|---:|---:|
| Coverage | 0.2070 | 0.3544 | 0.1474 |
| Purchase Hit | 0.2070 | 0.2679 | 0.0609 |
| Ticket ROI | 0.0246 | 0.0192 | -0.0054 |
| Explainability | 1.0000 | 1.0000 | 0.0000 |
| Buy / Skip | 285/0 | 265/20 | — |
| Mean pool size | 1.0000 | 2.1614 | — |

## PASS Gates

| Gate | Result |
|---|---|
| `prediction_fingerprint_identical` | PASS |
| `rank_identical` | PASS |
| `score_identical` | PASS |
| `coverage_improved` | PASS |
| `purchase_hit_improved` | PASS |
| `flag_off_compatibility` | PASS |
| `rollback_possible` | PASS |

## Decision Distribution (ON)

- `BUY:midhole`: 24
- `BUY:rank7_melee`: 65
- `BUY:unsatisfied_residual`: 176
- `SKIP:blocked_provisional`: 20

## Module

- `app/decision/`（flags / dto / policies / service / fingerprint）
- Shadow runner: `app/research/_v91_decision_layer_m1_shadow.py`

## 関連

- `v91-migration-report.md`
- `v91-governance.md`
