# Phase UI3 — Compatibility Report

**Date:** 2026-07-29  
**Status:** **PASS**（unit）· Deploy recommended for production BFF

---

```
【Production Diagnosis】
PredictionBundle 契約不一致を Mapper/BFF ensure で解消。UI 非変更。

【Server Diagnosis】
Status: PASS（修正後 unit）
Evidence:
- contract-guard 必須項目を Mapper/normalize で保証
- test-ui3-bundle-contract.mjs PASS
- test_ui1_mapper（UI3 case）PASS
- 2026-07-26 live predictions 36/36 既に PASS（回帰なし）

【Client Diagnosis】
Status: PARTIAL → デプロイ後に再確認
Network: race.html の validatePredictionBundle は非変更
Console: 「契約と一致しません」は narrative/race_no 欠落時に発生
Timing: N/A
Response Body: ensure 後 Guard PASS 形
Cache: Race List Cache 非変更
PredictionBundle Parse: 対象
Render Flow: ExpectPredictionBind 非変更
Unhandled Promise: N/A
JavaScript Error: N/A
Client Evidence: Guard ルールと Mapper 出力の突合（unit）

Diff Summary: domain.ensurePredictionBundleContract + Mapper narrative/race_info coerce
Root Cause: Client（契約違反応答）← Server Mapper/normalize 不足
Expected Action: BFF Pages デプロイ · Flag OFF 維持

【Decision】
Action Type: Contract Fix（Mapper/BFF）
Implementation Required: Yes（完了）
Deployment Required: Yes
Configuration Required: No（Flag OFF 維持）
Production Required: Deploy only
Rollback Required: Previous Pages deployment
Risk: Low
Expected Next Action: deploy:pages
```

## Compatibility matrix

| Check | Result |
|---|---|
| schema_version 2.0 | PASS |
| race_id / race_info | PASS |
| evaluation.runners | PASS |
| ai_confidence.score | PASS |
| explain.narrative | PASS |
| betting_recommendations.items | PASS |
| UI layout | unchanged |
| Race List Cache | unchanged |
| Core / Consumer / Prediction engine | unchanged |
