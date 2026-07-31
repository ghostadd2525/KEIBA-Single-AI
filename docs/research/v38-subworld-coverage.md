# Version38 — SubWorld Coverage

**Generated:** `2026-07-27T23:35:41+00:00`

## ② Design vs Observed

| World | Design SubWorlds | Observed (design) | Missing | Missing rate | Util |
|-------|------------------|-------------------|---------|-------------:|-----:|
| core_world | core_top, core_under | — | core_top, core_under | 100.0% | 0.0% |
| midupper_world | midupper_route, midupper_spread, midupper_corelike | midupper_route, midupper_spread | midupper_corelike | 33.3% | 66.7% |
| midhole_world | fallback_standard | — | fallback_standard | 100.0% | 0.0% |
| rank7_world | rank7_transition, rank7_residual | — | rank7_transition, rank7_residual | 100.0% | 0.0% |
| bug_world | fallback_standard | — | fallback_standard | 100.0% | 0.0% |
| mixed_world | fallback_standard | — | fallback_standard | 100.0% | 0.0% |

### Catalog (`EXISTING_SUBWORLDS`)

`core_top`, `core_under`, `midupper_route`, `midupper_spread`, `midupper_corelike`, `rank7_transition`, `rank7_residual`, `fallback_standard`

### Notes

- Design inventory is taken from V24 `WORLD_ROLES` routes ∩ `EXISTING_SUBWORLDS` (no new labels).
- `bug_world` / `mixed_world` / `midhole_world` have **thin named** SubWorld inventory (`fallback_standard` only) relative to role text.
- Observed corpus activates almost only `midupper_world` with `midupper_route` / `midupper_spread`.

