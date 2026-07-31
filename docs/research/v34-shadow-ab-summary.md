# Version34 — WIC Shadow AB Summary

**Date:** 2026-07-27T14:34:12+00:00  
**Schema:** `expect-wic-shadow-ab/1.0`  
**N races:** `335`  

## Verdict

- Non-inferiority governance: **PASS**
- ROI contribution proof: **INCONCLUSIVE_FROZEN_PE**
- Allow V35 Signal Service design: **False**
- Reason: Hit unchanged — PE pick frozen; World reclassification alone does not alter Prediction top pick in this AB

## Method

- Control: Production `research_world_signals` + assigned/sim world; **frozen PE pick**
- Shadow: WIC reconstruct difficulty from FeatureLoader; optional chaos diagnostic; first-match world; **same frozen PE pick**
- product_mutation: `False`
- signal_service_implemented: `False`
- CLI: `python -m app.research.collector_runner --wic-shadow-ab`

## KPI comparison

| Metric | Control | Shadow | Delta |
|--------|--------:|-------:|------:|
| Hit | 67 (20.0%) | 67 (20.0%) | 0 |
| Purchase | 67 (20.0%) | 67 (20.0%) | 0 |
| rank46 | 0 | 0 | 0 |
| rank710 | 0 | 0 | 0 |
| other_1_3 | 0 | 0 | 0 |
| other_10_13 | 0 | 0 | 0 |
| other_miss (sum) | 268 | 268 | 0 |

Note: Many bundles lack recoverable `winner_rank`, so miss layers often collapse into `other`. Deltas remain 0 under frozen pick.

## World distribution

| World | Control | Shadow | Design ref |
|-------|--------:|-------:|-----------:|
| `core_world` | 84.8% (n=284) | 99.1% (n=332) | 30.0% |
| `midupper_world` | 15.2% (n=51) | 0.9% (n=3) | 35.0% |
| `midhole_world` | 0.0% (n=0) | 0.0% (n=0) | 5.0% |
| `rank7_world` | 0.0% (n=0) | 0.0% (n=0) | 15.0% |
| `bug_world` | 0.0% (n=0) | 0.0% (n=0) | 5.0% |
| `mixed_world` | 0.0% (n=0) | 0.0% (n=0) | 10.0% |

World-changed races: **54 / 335** (see `v34-world-transition.md`).

## Signal coverage / reliability

| Item | Value |
|------|------:|
| Control difficulty present | 14.9% |
| Shadow difficulty present | 16.7% |
| Control chaos present | 0.0% |
| Shadow chaos present | 0.0% |
| WIC full rate | 1.5% |
| WIC partial rate | 98.5% |
| field_size alias rate | 15.2% |
| pace_collapse v2 bridge rate | 15.2% |
| Control difficulty unique_n | 1 (mean 0.5) |
| Shadow difficulty unique_n | 51 (mean ≈0.395, std ≈0.071) |

## World fitness (mean self-fit)

- Control: `≈0.997`
- Shadow: `≈0.878`

## ROI proof reading

V22–V33 の契約適用を Shadow で模倣すると、**difficulty の分散は回復し World ラベルは動く**が、現行 Prediction top pick は World 非依存のため **Hit/Purchase は不変**。  
したがって「ROI に寄与する」ことは **本 AB では証明されない**。

## Guardrails

- Production / Trigger / World / CSV / Signal Service unchanged
