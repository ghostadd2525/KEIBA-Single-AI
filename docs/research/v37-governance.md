# Version37 — Governance

**Generated:** `2026-07-27T23:26:36+00:00`  
**N:** `51`

## PASS conditions (user)

| Check | Requirement |
|-------|-------------|
| Hit | not worse than Baseline |
| rank710 | not worse |
| other miss | not worse |
| Influence | World has meaningful effect on PE ranking |

## Per-weight checks

| Weight | Hit≥base | rank710≤base | other_miss≤base | meaningful | Hit↑ | NI+influence |
|-------:|:--------:|:------------:|:---------------:|:----------:|:----:|:------------:|
| 25% | `False` | `True` | `True` | `True` | `False` | `False` |
| 50% | `False` | `True` | `True` | `True` | `False` | `False` |
| 75% | `False` | `True` | `True` | `True` | `False` | `False` |
| 100% | `False` | `False` | `True` | `True` | `False` | `False` |

## Final verdict

# **FAIL**

**Reason:** No weight satisfies Hit non-worse + rank710/other_miss non-worse + meaningful influence with Hit lift

### Interpretation rule (aligned with V34 lesson)

Non-inferiority alone ≠ ROI proof.  
This phase requires **Hit improvement** under a weight that also satisfies NI + meaningful PE influence.

| Gate | Value |
|------|-------|
| final_pass | `False` |
| any_non_inferior_with_influence | `False` |
| any_hit_improvement | `False` |
| selected_weight | `None` |

## Guardrails

- No Prediction / PE / CE / AI / World / Signal Service / Production changes
- Simulation only (virtual policy layer)
