# Version22 — Existing World Characterization

**Date:** 2026-07-27T11:30:59+00:00  
**Scope:** Existing Worlds only / New Worlds FORBIDDEN / Research only  

## Sample

- Corpus races: `337`
- Labeled (canonical): `51`
- Labeled with feature bins: `51`
- Labeled with Evidence: `50`
- By world: `{"midupper_world": 51}`
- Exploratory: `True`

## Existing Worlds

- `core_world`
- `midupper_world`
- `midhole_world`
- `rank7_world`
- `bug_world`
- `mixed_world`

## Feature profiles (field-best pick bins)

### `core_world`

- N: `0` (Evidence `0`)  
- Confidence: `Exploratory`  
- Dist mean top1/entropy/gap12: `None` / `None` / `None`

| Feature | Mode |
|---------|------|
| (insufficient labels) | — |

### `midupper_world`

- N: `51` (Evidence `50`)  
- Confidence: `High`  
- Dist mean top1/entropy/gap12: `0.09700588235294118` / `2.4750960784313727` / `0.0032333333333333333`

| Feature | Mode |
|---------|------|
| Surface | `turf` |
| Distance | `mile` |
| Going | `良` |
| Weather | `曇` |
| Field Size | `field_<=10` |

### `midhole_world`

- N: `0` (Evidence `0`)  
- Confidence: `Exploratory`  
- Dist mean top1/entropy/gap12: `None` / `None` / `None`

| Feature | Mode |
|---------|------|
| (insufficient labels) | — |

### `rank7_world`

- N: `0` (Evidence `0`)  
- Confidence: `Exploratory`  
- Dist mean top1/entropy/gap12: `None` / `None` / `None`

| Feature | Mode |
|---------|------|
| (insufficient labels) | — |

### `bug_world`

- N: `0` (Evidence `0`)  
- Confidence: `Exploratory`  
- Dist mean top1/entropy/gap12: `None` / `None` / `None`

| Feature | Mode |
|---------|------|
| (insufficient labels) | — |

### `mixed_world`

- N: `0` (Evidence `0`)  
- Confidence: `Exploratory`  
- Dist mean top1/entropy/gap12: `None` / `None` / `None`

| Feature | Mode |
|---------|------|
| (insufficient labels) | — |

## Note

- Profiles describe **assigned** existing Worlds; they do not create Worlds.
- Hit rate is intentionally omitted from characterization KPI.
