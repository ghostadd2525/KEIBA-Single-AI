# Version39 — Signal Restoration Simulation

**Status:** Research / Simulation only — no Production / Trigger / CSV / Signal Service writes  
**Generated:** `2026-07-27T23:46:17+00:00`  
**N (FeatureLoader-loadable):** `56` / meta `337`  
**Verdict:** **A** — Signal Restoration により World Entropy が有意に改善

## Method

```text
Current signals (defaults / research_world_signals)
        -> first-match Trigger (unchanged)
Current World mix

Feature frame L0 + Scorer diagnostic (virtual)
        -> designed reconstruct_leg_upset + chaos/pace/late/sustained/short_field
Restored signals
        -> same Trigger rules
Restored World mix
```

Hit rate is **not** evaluated.

Coverage: Simulation limited to races FeatureLoader can resolve (daily/global pace feature CSV present). Not full 335 corpus.

## World Distribution

| World | Design | Current n | Current % | Restored n | Restored % | Delta n |
|-------|-------:|----------:|----------:|-----------:|-----------:|--------:|
| core_world | 30.0% | 0 | 0.0% | 42 | 75.0% | +42 |
| midupper_world | 35.0% | 56 | 100.0% | 3 | 5.4% | -53 |
| rank7_world | 15.0% | 0 | 0.0% | 0 | 0.0% | +0 |
| mixed_world | 10.0% | 0 | 0.0% | 10 | 17.9% | +10 |
| bug_world | 5.0% | 0 | 0.0% | 0 | 0.0% | +0 |
| midhole_world | 5.0% | 0 | 0.0% | 1 | 1.8% | +1 |

## Entropy

| Arm | H (bits) | H / Hmax | Active Worlds | TV to design |
|-----|---------:|---------:|--------------:|-------------:|
| Current | 0.000 | 0.0% | 1 | 0.650 |
| Restored | 1.085 | 42.0% | 4 | 0.529 |
| Delta | +1.085 | — | +3 | -0.121 |

Recovered Worlds (were inactive -> active): `['core_world', 'midhole_world', 'mixed_world']`

## Index

| Doc | Content |
|-----|---------|
| `v39-signal-restoration.md` | this file |
| `v39-world-entropy.md` | Entropy / design proximity |
| `v39-trigger-recovery.md` | Trigger activation / margins |
| `v39-signal-variance.md` | Signal coverage / variance |
| `v39-governance.md` | A/B/C |

## Guardrails

- Production / Prediction / PE / CE / AI / World / Trigger / CSV / FeatureLoader / Signal Service — unchanged
