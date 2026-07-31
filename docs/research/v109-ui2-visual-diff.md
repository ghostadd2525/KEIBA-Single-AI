# Version109 Phase UI2 — Visual Diff

**Date:** 2026-07-29  
**Artifact:** `ui2-artifacts/visual-diff.json`

---

## Method

1. Baseline = Product-like PredictionBundle 2.0  
2. Candidate = UI1 `map_single_to_prediction_bundle` 出力（同一 base_bundle 合成）  
3. Structural fingerprint 比較（marks / confidence / ability keys / world null）  
4. Browser screenshot: baseline vs mapped（目視同一）

## Result

```json
{
  "identical_slots": true,
  "diff_keys": []
}
```

| Slot | Baseline | Mapped | Diff |
|---|---|---|---|
| marks | ◎○▲△ + horse_numbers | same | none |
| confidence_band | medium | medium | none |
| confidence_score | 0.72 | 0.72 | none |
| ability_score_keys | 5 keys | 5 keys | none |
| world | null | null | none |

**Visual Diff Verdict: PASS（差分ゼロ）**
