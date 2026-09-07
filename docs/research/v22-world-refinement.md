# Version22 — Existing World Refinement (Subtypes only)

**Date:** 2026-07-27T11:30:59+00:00  

- New Worlds created: `0`
- New Worlds forbidden: `True`

## Internal細分類候補

Format: `ParentWorld / Type` — World count unchanged.

### `midupper_world` × `surface`

- Internal細分類候補 only — World count unchanged

- `midupper_world / Surface=turf` n=`29` (new_world_forbidden=`True`)
- `midupper_world / Surface=dirt` n=`21` (new_world_forbidden=`True`)

### `midupper_world` × `distance_bucket`

- Internal細分類候補 only — World count unchanged

- `midupper_world / Distance=mile` n=`23` (new_world_forbidden=`True`)
- `midupper_world / Distance=sprint` n=`21` (new_world_forbidden=`True`)
- `midupper_world / Distance=middle` n=`5` (new_world_forbidden=`True`)

### `midupper_world` × `going`

- Internal細分類候補 only — World count unchanged

- `midupper_world / Going=良` n=`44` (new_world_forbidden=`True`)
- `midupper_world / Going=稍` n=`5` (new_world_forbidden=`True`)

### `midupper_world / midupper_route`

- Parent: `midupper_world`
- N: `42`
- Maps to existing sub_world: `True` (`midupper_route`)
- Confidence: `High`
- Proposal: Keep as internal subtype of existing World (NOT a new World). Prefer existing sub_world `midupper_route`.
- Modes: `{"surface": "turf", "distance_bucket": "mile", "going": "良", "weather": "曇", "field_bucket": "field_15-16"}`

### `midupper_world / midupper_spread`

- Parent: `midupper_world`
- N: `9`
- Maps to existing sub_world: `True` (`midupper_spread`)
- Confidence: `Low`
- Proposal: Keep as internal subtype of existing World (NOT a new World). Prefer existing sub_world `midupper_spread`.
- Modes: `{"surface": "turf", "distance_bucket": "sprint", "going": "良", "weather": "曇", "field_bucket": "field_<=10"}`

## Rule

- Only subtypes inside an existing World are allowed.
- Example: `midupper_world` → Type `midupper_route` / `midupper_spread`.
- Never introduce `world_7` or rename Worlds.
