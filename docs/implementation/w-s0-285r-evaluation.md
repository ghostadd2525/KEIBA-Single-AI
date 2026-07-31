# W-S0 Baseline Freeze — 285R Evaluation

**Generated:** `2026-07-28T04:45:01+00:00`  
**Stage:** W-S0  
**Gate:** `PASS`  

## Flags (must be OFF / legacy)

```json
{
  "W_TRIGGER_SHADOW": false,
  "W_TRIGGER_PATH": "legacy",
  "W_DEFAULT_CORE": true,
  "stage": "W-S0",
  "decision_authority": "legacy",
  "shadow_dual_eval_enabled": false
}
```

## 285R Metrics (after == before)

| Metric | Value |
|---|---:|
| N | 285 |
| Hit | 218 |
| Purchase | 218 |
| rank710 | 14 |
| other_1_3 | 1 |
| other_10_13 | 13 |
| rank46 | 35 |
| Hit rate | 0.764912 |

## Deltas (must be 0)

```json
{
  "production_prediction_identical": true,
  "prediction_changes": 0,
  "hit_delta": 0,
  "purchase_delta": 0,
  "hit_delta_zero": true,
  "purchase_delta_zero": true,
  "shadow_log_ok": true,
  "flag_off_compatible": true,
  "s1_not_executed": true
}
```

## World (W-S0 freeze — Dual-Eval not run)

- Positive Match evaluated: `False` — V44 Positive Match Dual-Eval is S1+; W-S0 freezes Legacy only
- Unsatisfied evaluated: `False` — Unsatisfied semantics are V46 S5 / Shadow S1+; not computed in W-S0
- Winner Alignment evaluated: `False` — Requires restored-signal World labels on 285R; deferred to Shadow stages
- Legacy probe identical: `True`

## Shadow Log

- dir: `C:\win5-ai\KEIBA-Single-AI\var\world_trigger_shadow`
- rows: `285`
- readable: `True`

## Gate

- PASS: `True`
- Rollback required: `False`
- Next: `W-S1`
