# Version38 — Refinement Potential & Existing SubWorld Review

**Generated:** `2026-07-27T23:35:41+00:00`

## ④ Existing SubWorld review

Does SubWorld adequately refine each World?

### core_world

- Design route: `core_top / core_under; may promote to midupper_route under compression`
- Observed counts: `{}`
- Adequate? **No** (refinement level: `blocked_inactive`)
- Rationale: World never activated in labeled corpus; SubWorld refinement not observable

### midupper_world

- Design route: `midupper_route | midupper_spread | midupper_corelike`
- Observed counts: `{"midupper_route": 42, "midupper_spread": 9}`
- Adequate? **No** (refinement level: `high`)
- Rationale: Design SubWorlds unused or entropy far below design capacity

### midhole_world

- Design route: `sustained / outside (via mixed/midhole sub rules)`
- Observed counts: `{}`
- Adequate? **No** (refinement level: `blocked_inactive`)
- Rationale: World never activated in labeled corpus; SubWorld refinement not observable

### rank7_world

- Design route: `rank7_transition | rank7_residual`
- Observed counts: `{}`
- Adequate? **No** (refinement level: `blocked_inactive`)
- Rationale: World never activated in labeled corpus; SubWorld refinement not observable

### bug_world

- Design route: `bug observation / deep residual`
- Observed counts: `{}`
- Adequate? **No** (refinement level: `blocked_inactive`)
- Rationale: World never activated in labeled corpus; SubWorld refinement not observable

### mixed_world

- Design route: `route-forward + multi-survivor families`
- Observed counts: `{}`
- Adequate? **No** (refinement level: `blocked_inactive`)
- Rationale: World never activated in labeled corpus; SubWorld refinement not observable

## ⑤ Missing classification (absorption / under-split)

### Within-SubWorld heterogeneity

| World | SubWorld | n | joint H (bits) | bins | under_split? |
|-------|----------|--:|---------------:|-----:|:------------:|
| midupper_world | midupper_route | 42 | 2.042 | 5 | `yes` |
| midupper_world | midupper_spread | 9 | 0.986 | 3 | no |

### Midupper absorption of other World triggers (signal probe)

- Checked midupper races with signals: `51`
- Would also match (count): `{}`
- Note: Read-only V24 threshold probe on stored signals; missing signals reduce detection (esp. chaos).

Examples:

- (none detected or signals mostly null)

## ⑥ Refinement potential summary

| World | Level | obs/design SubWorlds | missing_rate | unused bits |
|-------|-------|---------------------:|-------------:|------------:|
| core_world | `blocked_inactive` | 0/2 | 100.0% | 1.000 |
| midupper_world | `high` | 2/3 | 33.3% | 0.913 |
| midhole_world | `blocked_inactive` | 0/1 | 100.0% | 0.000 |
| rank7_world | `blocked_inactive` | 0/2 | 100.0% | 1.000 |
| bug_world | `blocked_inactive` | 0/1 | 100.0% | 0.000 |
| mixed_world | `blocked_inactive` | 0/1 | 100.0% | 0.000 |

No new World proposals. Levels describe **existing** World/SubWorld inventory only.
