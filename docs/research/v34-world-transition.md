# Version34 — World Transition (Shadow AB)

**Date:** 2026-07-27T14:34:12+00:00  
**Changed races:** `54` / `335` (16.1%)

## Transition matrix (counts)

Primary movement: Production/control midupper (or labeled midupper) → Shadow `core_world` when reconstructed difficulty falls below midupper thresholds (often &lt; 0.50).

See evidence JSON `world_transition.matrix_counts` for full From→To counts.

## Activation (world rates)

| World | Control rate | Shadow rate | Design ref |
|-------|-------------:|------------:|-----------:|
| `core_world` | 84.8% | 99.1% | 30.0% |
| `midupper_world` | 15.2% | 0.9% | 35.0% |
| `midhole_world` | 0.0% | 0.0% | 5.0% |
| `rank7_world` | 0.0% | 0.0% | 15.0% |
| `bug_world` | 0.0% | 0.0% | 5.0% |
| `mixed_world` | 0.0% | 0.0% | 10.0% |

## Interpretation

- Shadow WIC difficulty mean ≈0.40 with unique_n=51 → R7 `difficulty>=0.50` rarely fires → **core dominance**.
- Control often carries DEFAULT 0.5 when present, or assigned midupper labels from bundles → more midupper than Shadow sim.
- Neither arm recovers rank7 / bug / mixed / midhole (chaos still absent; other L2 inputs weak).

## Guardrails

- Shadow simulation only; Trigger thresholds unchanged
