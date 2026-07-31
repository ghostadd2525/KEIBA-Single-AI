# Phase UI3 — Mapper Fix

**Date:** 2026-07-29  
**Scope:** View Mapper + BFF contract ensure only  
**Non-goals:** Core / Consumer / Prediction engine / UI layout / Race List Cache

---

## Files

| Path | Change |
|---|---|
| `functions/_lib/singleToBundleMapper.js` | default `narrative: ""` · `ensurePredictionBundleContract` |
| `functions/_lib/domain.js` | `ensurePredictionBundleContract` · `normalizePredictionBundle` 末尾適用 |
| `services/win5-ai/app/ui_adaptation/single_to_bundle.py` | 同趣旨の coerce + `ensure_prediction_bundle_contract` |

## Behavior

1. Mapper 出力は常に ExpectContractGuard PASS 形
2. Prediction API（PI → `normalizePredictionBundle`）も同様に最終保証
3. 既存 UI / bind は非変更

## Tests

- `node scripts/ops/test-ui3-bundle-contract.mjs` → PASS
- `python -m unittest tests.ui_adaptation.test_ui1_mapper` → PASS（`test_ui3_contract_guard_fields` 追加）
