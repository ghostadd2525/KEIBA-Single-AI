# Version37 — World Policy Weight Sensitivity

## Curve

| Weight | Hit Δ | rank710 Δ | other_miss Δ | Top1 change rate |
|-------:|------:|----------:|-------------:|-----------------:|
| 0% | +0 | +0 | +0 | 0.0% |
| 25% | -1 | +0 | -2 | 92.2% |
| 50% | -2 | +0 | -3 | 96.1% |
| 75% | -2 | +0 | -2 | 98.0% |
| 100% | -1 | +2 | -4 | 98.0% |

## Safety flags

- midupper_share: `1.0`
- world_saturation_flag: `True`
- policy_domination_flag (Top1 change ≥50% at w=100%): `True`
- Top1 change rate @100%: `98.0%`
- mean |Δrank| @100%: `1.335`

## Saturation vs design mix

| World | observed | design | Δ |
|-------|---------:|-------:|--:|
| core_world | 0.0% | 30.0% | -30.0% |
| midupper_world | 100.0% | 35.0% | +65.0% |
| midhole_world | 0.0% | 5.0% | -5.0% |
| rank7_world | 0.0% | 15.0% | -15.0% |
| bug_world | 0.0% | 5.0% | -5.0% |
| mixed_world | 0.0% | 10.0% | -10.0% |

## Bias / Overfit notes

- Kernel is design-prior (not fit on Hit labels) to reduce label overfit in this simulation.
- Corpus World labels are midupper-saturated; policy effect may concentrate on midupper_world.

Overfit control: kernels are **not** optimized against Hit on this corpus.
