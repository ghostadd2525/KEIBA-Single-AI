# Phase R1 — Release Report

**Date:** 2026-07-29  
**Scope:** Single AI Detail (I3) + Ops (I4) Production Release Preparation  
**Freeze:** Core Platform V1 / Consumer / Prediction / UI layout / Race List Cache / Contract

---

## Executive verdict

| 項目 | 判定 |
|---|---|
| **I3+I4 Deploy（Flag OFF）** | **DONE / PASS** |
| **Post-deploy Health / Monitoring** | **PARTIAL**（Single Detail ops OK · 既存 degraded あり） |
| **Limited Live Rehearsal（Flag ON）** | **PASS**（ADMIN · race.html） |
| **Flag restored OFF** | **PASS** |
| **I2 Cutover（恒久 Flag ON）** | **NO-GO**（明示承認待ち） |
| **Safe Production Release（コード載せて Flag OFF）** | **GO — 完了** |

---

## What shipped

| Item | Production |
|---|---|
| `race.html` + `single-detail.js?v=2` | 配線済み |
| `ui-features.js?v=12` + `single_ai_detail` DEFAULT | 配信済み |
| `/api/single/detail/:id` + observability | 配信済み |
| `/api/ops/single-detail` · `single_detail_ops` probe | 配信済み |
| `beta.ui_features.single_ai_detail` | **false**（最終） |

## Deployments（Pages `keiba-single-ai`）

| Step | Preview | Flag |
|---|---|---|
| Initial I3+I4 OFF | `44885c02…` | OFF |
| Limited ON rehearse | `dab4d7c9…` / `1132055d…` / `54a4bd33…` | ON（一時） |
| Final OFF | `40287e64…` / `e3303744…` | **OFF** |

## Fixes applied during R1（release-only）

1. **CDN cache bust** — `ui-features.js?v=12`（旧 `?v=11` が DEFAULTS に Flag キー無しのままキャッシュ）
2. **Flag race** — `single-detail.js` が `ExpectUiFeatures.ready()` 後に Flag 判定（レイアウト非変更）

## Related

- [Deployment Report](./v109-r1-deployment-report.md)
- [Live Rehearsal Report](./v109-r1-live-rehearsal-report.md)
- [Production Readiness](./v109-r1-production-readiness-report.md)
- [Final Recommendation](./v109-r1-final-recommendation.md)
- [Governance](./v109-r1-governance.md)
- [I2 Final Gate](./v109-i2-final-cutover-gate-after-r1.md)
