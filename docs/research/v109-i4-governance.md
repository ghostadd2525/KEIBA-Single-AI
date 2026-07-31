# Phase I4 — Governance

**Date:** 2026-07-29  
**Status:** Operational Readiness **IMPLEMENTED** · Cutover **BLOCKED pending re-eval**

---

```
【Production Diagnosis】
I4 = Single AI Detail Flag の監視・警報・運用文書を整備。Cutover は実行しない。

【Server Diagnosis】
Status: PASS
Evidence:
- singleDetailObservability + record on SingleDetailAdapter
- GET /api/ops/single-detail
- single_detail_ops in runAllProbes + ALT-SD01..05 in opsDashboard
- docs/ops/single-detail-*.md

【Client Diagnosis】
Status: PASS（非変更確認）
Network: race.html / races.html 非変更（I3 のまま）
Console: 新規 FE beacon なし（Flag ON率は endpoint 近似）
Timing: N/A（UI 非変更）
Response Body: N/A
Cache: list cache 非変更
PredictionBundle Parse: N/A
Render Flow: N/A
Unhandled Promise: N/A
JavaScript Error: N/A
Client Evidence: I4 は FE 非接触。監査で races.html / race.html 差分なしを確認

Diff Summary: BFF ops/metrics/adapter logging のみ。Core/Consumer/Prediction/UI/List Cache 非変更。
Root Cause: N/A（準備フェーズ）
Expected Action: Staging Flag ON + core path で Alert 緑確認 → I2 Cutover 再評価

【Decision】
Action Type: Operational Readiness（Monitoring/Alert/Docs）
Implementation Required: Yes（ops 完了）
Deployment Required: Yes（BFF Functions デプロイで metrics/alerts 有効）
Configuration Required: Optional（OPS_MONITOR_KEY / Slack 既存）
Production Required: No（Flag ON / Cutover は別 Gate）
Rollback Required: No（観測は additive；問題時は Flag OFF）
Risk: Low
Expected Next Action: Staging rehearse under Flag ON → I2 re-gate
```

---

## 硬制約

| ID | 制約 |
|---|---|
| G109-I4-1 | Core / Consumer / Prediction / UI layout 変更禁止 |
| G109-I4-2 | Race List Cache / 一覧 Single 禁止（永久） |
| G109-I4-3 | I4 で Production Cutover 実行禁止 |
| G109-I4-4 | Alert 未緑・staging 未 rehearse のまま Flag 本番 ON 禁止 |
| G109-I4-5 | expected_fallback（no core）を error として Cutover 判定に使わない |
| G109-I4-6 | Rollback = Flag OFF（I3） |

---

## Alert ownership

| ID | Owner | Runbook |
|---|---|---|
| ALT-SD01..05 | Ops on-call | `docs/ops/single-detail-runbook.md` |

## Cutover dependency

I4 **完了 ≠ Cutover 承認**。Cutover は I2 再評価ゲート。
