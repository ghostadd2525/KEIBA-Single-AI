# PE-V2-A — AB Report (Version 2 Accuracy)

**Generated:** 2026-07-21T23:41:21Z
**Experiment ID:** `v2-pe-v2-a-285r-ab`
**Git SHA:** `7732f06e8d606d31d1deb338aa306d670a5e2576`
**Flag:** `WIN5_POOL_ENTRY_V2_ENABLED` (Treatment only ON)
**Baseline:** Phase255 Final (285R Hit=216)
**STATUS:** **PASS**
**AB_PASS:** **True**
**Flag recommendation:** `CANDIDATE_ON`

## Hard Gate

`Treatment.Hit > 216` → **PASS** (Hit=218)

## Metrics

| arm | Hit | Purchase | rank710 | other | rank46 | Winner in Pool 率 |
|-----|----:|---------:|--------:|------:|-------:|------------------:|
| Control (Phase255) | 216 | 189 | 15 | 19 | 35 | 0.947368 |
| Treatment (PE-V2-A) | 218 | 187 | 14 | 18 | 35 | 0.961404 |
| Δ | 2 | -2 | -1 | -1 | 0 | 0.014036 |

- Winner Rescue: N/A（RP-V2 専用）
- pe_v2 fired_tx: **112**
- hit_loss (churn): **0**

## Gates

| gate | pass |
|------|------|
| G-Hard_Hit_gt_216 | True |
| G-Ident_ctrl_lock | True |
| G-Loss_churn_hit_0 | True |
| G-Single_flag | True |
| G-Pool_p95_le_110pct | True |
| G-Purchase_p95_le_110pct | True |

## Artifacts

- `C:\win5-ai\compare\v2_pe_v2_a_ab_summary.json`
- `C:\win5-ai\compare\v2_pe_v2_a_control_fire_path.csv`
- `C:\win5-ai\compare\v2_pe_v2_a_treatment_fire_path.csv`
- `C:\win5-ai\compare\v2_baseline_winner_in_pool.json`

## Notes

- Control must equal Phase255 Final 216/15/19 before Treatment is judged.
- Hard Gate is Hit > 216 only; Winner in Pool rate is attribution (not Hard Gate).
- RP-V2 / CE-V2 / Explainability / UI / Operations are blocked until PE-V2-A PASS.
