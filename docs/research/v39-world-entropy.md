# Version39 — World Entropy

**N:** `56`  
**Verdict context:** `A`

## Current -> Restored

| Metric | Current | Restored | Delta |
|--------|--------:|---------:|------:|
| Entropy (bits) | 0.000 | 1.085 | +1.085 |
| Entropy ratio | 0.0% | 42.0% | — |
| Active Worlds | 1 | 4 | +3 |
| TV distance to design mix | 0.650 | 0.529 | -0.121 |

## Design mix proximity (secondary)

Design: core 30 / midupper 35 / rank7 15 / mixed 10 / bug 5 / midhole 5.

| World | Design | Current n | Current % | Restored n | Restored % | Delta n |
|-------|-------:|----------:|----------:|-----------:|-----------:|--------:|
| core_world | 30.0% | 0 | 0.0% | 42 | 75.0% | +42 |
| midupper_world | 35.0% | 56 | 100.0% | 3 | 5.4% | -53 |
| rank7_world | 15.0% | 0 | 0.0% | 0 | 0.0% | +0 |
| mixed_world | 10.0% | 0 | 0.0% | 10 | 17.9% | +10 |
| bug_world | 5.0% | 0 | 0.0% | 0 | 0.0% | +0 |
| midhole_world | 5.0% | 0 | 0.0% | 1 | 1.8% | +1 |

- TV improved vs design: `True`
- Note: Entropy gate is primary. Design-mix TV is secondary observation.

## Inactive -> Recovered

- Current inactive: `['core_world', 'midhole_world', 'rank7_world', 'bug_world', 'mixed_world']`
- Restored inactive: `['rank7_world', 'bug_world']`
- Recovered: `['core_world', 'midhole_world', 'mixed_world']`

## SubWorld distribution

### Current
`{"unset": 5, "midupper_route": 42, "midupper_spread": 9}`

### Restored
`{"unset": 56}`
