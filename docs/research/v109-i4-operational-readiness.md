# Phase I4 — Operational Readiness Report

**Date:** 2026-07-29  
**Status:** Ops wiring **IMPLEMENTED** · Production Cutover **NOT in scope**（re-eval after alerts）

---

## Deliverables

| Artifact | Path |
|---|---|
| Operation Guide | `docs/ops/single-detail-operation-guide.md` |
| Alert Rules | `docs/ops/single-detail-alert-rules.md` |
| Metrics Definition | `docs/ops/single-detail-metrics.md` |
| Dashboard Design | `docs/ops/single-detail-dashboard.md` |
| Runbook | `docs/ops/single-detail-runbook.md` |
| Governance | `docs/research/v109-i4-governance.md` |

## Code（ops only）

| Component | Path |
|---|---|
| Metrics + alerts | `functions/_lib/singleDetailObservability.js` |
| Record on resolve | `functions/_lib/adapters/singleDetailAdapter.js` |
| Ops API | `functions/api/ops/single-detail.js` |
| Monitor probe | `functions/_lib/opsMonitor.js` → `probeSingleDetailOps` |
| Alert catalog | `functions/_lib/opsDashboard.js` ALT-SD* |

## Unchanged（hard freeze）

- Core / Consumer / Prediction engines
- UI layout / prediction-bind
- Race List Cache / `races.html`
- Flag default remains **OFF**

## Cutover

Production Cutover **re-evaluated after Alert completion**（this phase）.  
I2 verdict remains **NOT READY** until staging Flag ON + green SD alerts with attempted Single path.
