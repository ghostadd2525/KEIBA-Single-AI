# Contract Issue: `evaluation.runners[].win_prob` under RESTORED_V2

**Status:** Open (documented; schema unchanged)  
**Date:** 2026-08-23  
**Phase:** Production Probability Fix Phase1 — label correction only  
**Related audit:** Displayed Win Probability Audit (2026-08-23)

---

## Summary

`evaluation.runners[].win_prob` is part of the frozen `single-prediction-bundle/2.0` schema.
Under `decision_authority = RESTORED_V2`, the field name implies a win probability, but the
published value is **not** `P(1着 | input)`.

## Observed mapping (production)

```
RESTORED_V2 final_order (rank)
    ↓
ranking[].score = max(0, 1.0 - (rank - 1) × 0.01)   [AI Server: bundle_map.build_v2_ranking_rows]
    ↓
evaluation.runners[].win_prob := ranking[].score      [single_prediction_mapper._runners_from_ranking]
    ↓
Client (Phase1 fix): win_prob no longer rendered as 「1着確率」 on 対抗・穴 cards
```

## Semantic mismatch

| Field name | Implied meaning | Actual value (RESTORED_V2) |
|------------|-----------------|----------------------------|
| `win_prob` | Calibrated or model win probability | Rank-derived display score |

Example (7-horse field): ranks 1–7 → `1.00, 0.99, 0.98, 0.97, 0.96, 0.95, 0.94` (sum **6.79**, not 1.0).

## Internal vs public

- **Internal (not exposed in Phase1):** `race_softmax(adjusted_score)` inside RESTORED_V2 spine may produce
  race-normalized scores used for ordering. Calibration as true win probability is **not verified**.
- **Public bundle:** ranking scores are replaced before mapping to `win_prob`; softmax values must not
  be published as 「1着確率」 until a dedicated calibration audit passes.

## Phase1 scope (this issue record)

- **Done:** UI no longer labels RESTORED_V2 `win_prob` as 「1着確率」 on production 対抗・穴 cards.
- **Not in scope:** Renaming schema field, changing server mapping, exposing softmax, calibration.

## Expected follow-up

Separate phase: **Actual Win Probability Calibration Audit** on V2 internal softmax before any
user-facing probability label is restored.
