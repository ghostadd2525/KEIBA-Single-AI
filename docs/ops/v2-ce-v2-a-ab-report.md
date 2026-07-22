# CE-V2-A — AB Report (Version 2 Accuracy)

**Generated:** 2026-07-22T04:10:49Z
**Experiment ID:** `v2-ce-v2-a-285r-ab`
**Git SHA:** `7732f06e8d606d31d1deb338aa306d670a5e2576`
**Flag:** `WIN5_CE_V2_ENABLED` (Treatment only; PE-V2-A ON both arms; RP OFF)
**Facet:** CE-V2-A (temp=0.92)
**Control baseline:** PE-V2-A PASS (Hit=218)
**STATUS:** **FAIL**
**AB_PASS:** **False**
**Flag recommendation:** `OFF`

## Hard Gate

`Treatment.Hit > 218` → **FAIL** (Hit=216)
`churn_hit == 0` → **FAIL** (churn_hit=2)

## Metrics

| arm | Hit | Purchase | rank710 | other | rank46 | Winner in Pool率 | churn_hit |
|-----|----:|---------:|--------:|------:|-------:|-----------------:|----------:|
| Control (PE-V2-A) | 218 | 187 | 14 | 18 | 35 | 0.961404 | — |
| Treatment (PE+CE-V2-A) | 216 | 186 | 16 | 18 | 35 | 0.947368 | 2 |
| Δ | -2 | -1 | 2 | 0 | 0 | -0.014036 | — |

- ce_v2 fired_tx: **285**
- Flag OFF sample journal.reason: `disabled`

## Gates

| gate | pass |
|------|------|
| G-Hard_Hit_gt_218 | False |
| G-Loss_churn_hit_0 | False |
| G-Ident_ctrl_pe_lock | True |
| G-Single_flag_CE | True |

## 1. Hit が改善したレース

- （なし）

## 2. Hit を失ったレース（churn）

- `2024-01-28-小倉-11`
- `2025-12-28-中山-10`

## Feature Flag 確認

- Flag name: `WIN5_CE_V2_ENABLED`
- Default: **false** (`WIN5_CE_V2_ENABLED = False` in `v2_ce_v2.py`)
- Control arm: CE OFF → journal reason sample `disabled`
- Treatment arm: CE ON → fired_tx=285
- Facet C: **not implemented**

## Flag OFF 恒等性

- Unit: `research/ce-v2/test_ce_v2.py` (`test_flag_default_off_identity_*`)
- Control arm = PE-V2-A only; CE journal `disabled` when Flag OFF
- Control Hit locked to **218** (PE-V2-A PASS)

## Artifacts

- `C:\win5-ai\compare\v2_ce_v2_a_control_fire_path.csv`
- `C:\win5-ai\compare\v2_ce_v2_a_treatment_fire_path.csv`
- `C:\win5-ai\compare\v2_ce_v2_a_ab_summary.json`

## Notes

- Hard Gate requires **both** Hit>218 and churn_hit=0.
- Do not proceed to Facet C until this AB PASS/FAIL is accepted.
